import asyncio
import os
import sys
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db as db_mod
from models.alert import DBNetworkAlert
from models.chaos_event import DBChaosEvent
from services.prometheus_service import PrometheusService

# History storage per service link
# Key format: "source_service->target_service"
link_metrics_history = {}
HISTORY_WINDOW_LIMIT = 50

LATENCY_THRESHOLD_MS = 500.0
PACKET_LOSS_THRESHOLD_PCT = 2.0
REQUEST_RATE_SPIKE_LIMIT = 100.0
ERROR_THRESHOLD_RATE = 1.0
_cycle_count = 0

async def run_network_agent():
    print("Network Monitoring Agent started successfully.")
    prometheus_service = PrometheusService()
    global _cycle_count
    
    # Let database initialize
    await asyncio.sleep(15)
    
    while True:
        try:
            _cycle_count += 1
            metrics = await prometheus_service.get_network_metrics()
            db = db_mod.SessionLocal()

            # Only alert if chaos simulation is active
            chaos_active = db.query(DBChaosEvent).filter(
                DBChaosEvent.status == "active"
            ).first() is not None

            # Prune network alerts periodically
            if _cycle_count % 10 == 0:
                cutoff = datetime.utcnow() - timedelta(hours=2)
                deleted = db.query(DBNetworkAlert).filter(
                    DBNetworkAlert.timestamp < cutoff
                ).delete(synchronize_session=False)
                db.commit()
                if deleted:
                    print(f"[NetworkAgent] Pruned {deleted} old network alerts (>2h)")

            if not chaos_active:
                db.close()
                await asyncio.sleep(30)
                continue
            for item in metrics:
                source = item["source_service"]
                target = item["target_service"]
                link_key = f"{source}->{target}"
                
                latency = item["latency_ms"]
                rx_bytes = item["receive_bytes_sec"]
                tx_bytes = item["transmit_bytes_sec"]
                rx_errors = item["receive_errors"]
                tx_errors = item["transmit_errors"]
                pkt_drop = item["packet_loss_rate"]
                tcp_conn = item["tcp_connections"]
                req_rate = item["http_request_rate"]
                
                if link_key not in link_metrics_history:
                    link_metrics_history[link_key] = []
                    
                current_vector = [latency, rx_bytes, tx_bytes, rx_errors, pkt_drop, tcp_conn, req_rate]
                link_metrics_history[link_key].append(current_vector)
                
                if len(link_metrics_history[link_key]) > HISTORY_WINDOW_LIMIT:
                    link_metrics_history[link_key].pop(0)
                    
                history = np.array(link_metrics_history[link_key])
                history_len = len(history)
                
                def calc_z_score(val, hist_col):
                    if len(hist_col) < 5:
                        return 0.0
                    mean = np.mean(hist_col)
                    std = np.std(hist_col)
                    if std == 0.0:
                        return 0.0
                    return (val - mean) / std

                hist_latency = history[:, 0]
                hist_pkt_drop = history[:, 4]
                hist_req_rate = history[:, 6]
                hist_errors = history[:, 3]
                
                lat_z = calc_z_score(latency, hist_latency)
                drop_z = calc_z_score(pkt_drop, hist_pkt_drop)
                req_z = calc_z_score(req_rate, hist_req_rate)
                err_z = calc_z_score(rx_errors, hist_errors)
                
                triggered_alert = False
                alert_msg = ""
                alert_metric = ""
                alert_val = 0.0
                max_z = 0.0
                if latency > LATENCY_THRESHOLD_MS or lat_z > 2.5:
                    alert_msg = f"High Network Latency Alert: {source} -> {target} latency is {latency:.1f}ms (Z-Score: {lat_z:.2f})"
                    alert_metric = "latency"
                    alert_val = latency
                    max_z = lat_z
                    triggered_alert = True
                    
                elif pkt_drop > PACKET_LOSS_THRESHOLD_PCT or drop_z > 2.5:
                    alert_msg = f"Packet Loss / Network Congestion Alert: {source} -> {target} packet drop rate is {pkt_drop:.2f}% (Z-Score: {drop_z:.2f})"
                    alert_metric = "packet_loss"
                    alert_val = pkt_drop
                    max_z = drop_z
                    triggered_alert = True
                    
                elif req_rate > REQUEST_RATE_SPIKE_LIMIT or req_z > 2.5:
                    alert_msg = f"Traffic Spike Alert: {source} -> {target} HTTP request rate is {req_rate:.1f} req/s (Z-Score: {req_z:.2f})"
                    alert_metric = "traffic_spike"
                    alert_val = req_rate
                    max_z = req_z
                    triggered_alert = True
                    
                elif rx_errors > ERROR_THRESHOLD_RATE or err_z > 2.5:
                    alert_msg = f"Connection Failure Alert: {source} -> {target} connection error rate is {rx_errors:.1f} errors/s (Z-Score: {err_z:.2f})"
                    alert_metric = "connection_failure"
                    alert_val = rx_errors
                    max_z = err_z
                    triggered_alert = True

                # ML anomaly detection
                if history_len >= 10 and not triggered_alert:
                    try:
                        clf = IsolationForest(contamination=0.05, random_state=42)
                        preds = clf.fit_predict(history)
                        
                        if preds[-1] == -1:
                            z_scores = [abs(lat_z), abs(drop_z), abs(req_z), abs(err_z)]
                            max_z_idx = np.argmax(z_scores)
                            
                            metrics_names = ["latency", "packet_loss", "traffic_spike", "connection_failure"]
                            metrics_vals = [latency, pkt_drop, req_rate, rx_errors]
                            metrics_zs = [lat_z, drop_z, req_z, err_z]
                            
                            driver_metric = metrics_names[max_z_idx]
                            driver_val = metrics_vals[max_z_idx]
                            driver_z = metrics_zs[max_z_idx]
                            
                            if abs(driver_z) > 1.5:
                                alert_msg = f"Abnormal Network Usage: Isolation Forest detected network anomaly on {source} -> {target} driven by {driver_metric} = {driver_val:.2f} (Z-Score: {driver_z:.2f})"
                                alert_metric = driver_metric
                                alert_val = driver_val
                                max_z = driver_z
                                triggered_alert = True
                    except Exception as clf_err:
                        print(f"Error fitting IsolationForest for {link_key}: {clf_err}")

                # Save alert to database
                if triggered_alert:
                    print(f"[NetworkAgent] ALERT - Link '{link_key}': {alert_msg}")
                    alert_db = DBNetworkAlert(
                        source_service=source,
                        target_service=target,
                        metric_name=alert_metric,
                        metric_value=alert_val,
                        z_score=float(max_z),
                        message=alert_msg
                    )
                    db.add(alert_db)
                    db.commit()
                    
            db.close()
        except Exception as e:
            print(f"Error in Network monitoring agent iteration: {e}")
            
        # Run loop every 30 seconds
        await asyncio.sleep(30)
