import asyncio
import os
import sys
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.db as db_mod
from models.alert import DBAlert
from models.chaos_event import DBChaosEvent
from services.prometheus_service import PrometheusService

# Historical CPU values per pod
pod_cpu_history = {}
HISTORY_WINDOW_LIMIT = 50
MIN_HISTORY_REQUIRED = 5
_cycle_count = 0

async def run_cpu_agent():
    print("CPU Anomaly Detection Agent started successfully.")
    prometheus_service = PrometheusService()
    global _cycle_count
    
    # Let FastAPI and DB start up
    await asyncio.sleep(10)
    
    while True:
        try:
            _cycle_count += 1
            metrics = await prometheus_service.get_cpu_metrics()
            db = db_mod.SessionLocal()

            # Only alert if chaos simulation is active
            chaos_active = db.query(DBChaosEvent).filter(
                DBChaosEvent.status == "active"
            ).first() is not None
            
            # Prune CPU alerts (>2h) periodically
            if _cycle_count % 10 == 0:
                cutoff = datetime.utcnow() - timedelta(hours=2)
                deleted = db.query(DBAlert).filter(
                    DBAlert.timestamp < cutoff,
                    ~DBAlert.pod_name.like('pvc:%')
                ).delete(synchronize_session=False)
                db.commit()
                if deleted:
                    print(f"[CPUAgent] Pruned {deleted} old CPU alerts (>2h)")

            if not chaos_active:
                db.close()
                await asyncio.sleep(30)
                continue
            for item in metrics:
                pod = item["pod"]
                cores = item["cpu_cores"]
                
                # Ignore inactive pods
                if cores < 0.0001:
                    continue
                
                if pod not in pod_cpu_history:
                    pod_cpu_history[pod] = []
                
                pod_cpu_history[pod].append(cores)
                if len(pod_cpu_history[pod]) > HISTORY_WINDOW_LIMIT:
                    pod_cpu_history[pod].pop(0)
                    
                history = pod_cpu_history[pod]
                
                # Run anomaly detection if we have enough data
                if len(history) >= MIN_HISTORY_REQUIRED:
                    X = np.array(history).reshape(-1, 1)
                    
                    clf = IsolationForest(contamination=0.1, random_state=42)
                    clf.fit(X)
                    
                    latest_point = np.array([[cores]])
                    prediction = clf.predict(latest_point)[0]
                    
                    historical_median = np.median(history[:-1]) if len(history) > 1 else 0
                    
                    if prediction == -1 and cores > (historical_median * 1.5):
                        msg = f"CPU Anomaly Spike: {cores:.5f} cores (Median: {historical_median:.5f} cores)"
                        print(f"[CPUAgent] ALERT - Pod '{pod}': {msg}")
                        
                        alert = DBAlert(
                            pod_name=pod,
                            cpu_value=cores,
                            message=msg
                        )
                        db.add(alert)
                        db.commit()
            
            db.close()
        except Exception as e:
            print(f"Error in CPU anomaly agent iteration: {e}")
            
        # Run loop every 30 seconds
        await asyncio.sleep(30)
