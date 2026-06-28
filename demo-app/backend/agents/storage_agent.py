import asyncio
import os
import sys
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db as db_mod
from models.alert import DBAlert
from models.chaos_event import DBChaosEvent
from services.prometheus_service import PrometheusService

# Track PVC growth history
pvc_growth_history = {}
HISTORY_WINDOW_LIMIT = 50
_cycle_count = 0

SATURATION_THRESHOLD_PERCENT = 90.0
ABNORMAL_GROWTH_BYTES_PER_INTERVAL = 2 * 1024 * 1024

async def run_storage_agent():
    print("Storage Monitoring Agent started successfully.")
    prometheus_service = PrometheusService()
    global _cycle_count
    
    # Let FastAPI and DB start up
    await asyncio.sleep(15)
    
    while True:
        try:
            _cycle_count += 1
            pvc_metrics = await prometheus_service.get_pvc_metrics()
            db = db_mod.SessionLocal()

            # Only alert if chaos simulation is active
            chaos_active = db.query(DBChaosEvent).filter(
                DBChaosEvent.status == "active"
            ).first() is not None

            # Prune old alerts periodically
            if _cycle_count % 10 == 0:
                cutoff = datetime.utcnow() - timedelta(hours=2)
                deleted = db.query(DBAlert).filter(
                    DBAlert.timestamp < cutoff,
                    DBAlert.pod_name.like('pvc:%')
                ).delete(synchronize_session=False)
                db.commit()
                if deleted:
                    print(f"[StorageAgent] Pruned {deleted} old storage alerts (>2h)")

            if not chaos_active:
                db.close()
                await asyncio.sleep(30)
                continue
            for pvc in pvc_metrics:
                pvc_name = pvc["pvc_name"]
                used_bytes = pvc["used_bytes"]
                capacity_bytes = pvc["capacity_bytes"]
                percentage_used = pvc["percentage_used"]
                
                # Saturation check
                if percentage_used > SATURATION_THRESHOLD_PERCENT:
                    msg = f"Storage Saturation Alert: PVC '{pvc_name}' is {percentage_used}% full ({pvc['used_mb']:.1f}MB of {pvc['capacity_mb']:.1f}MB used)"
                    print(f"[StorageAgent] ALERT - PVC '{pvc_name}': {msg}")
                    
                    alert = DBAlert(
                        pod_name=f"pvc:{pvc_name}",
                        cpu_value=percentage_used,
                        message=msg
                    )
                    db.add(alert)
                    db.commit()
                
                # Track growth history
                if pvc_name not in pvc_growth_history:
                    pvc_growth_history[pvc_name] = []
                
                pvc_growth_history[pvc_name].append(used_bytes)
                if len(pvc_growth_history[pvc_name]) > HISTORY_WINDOW_LIMIT:
                    pvc_growth_history[pvc_name].pop(0)
                    
                history = pvc_growth_history[pvc_name]
                
                # Abnormal growth check
                if len(history) >= 2:
                    growth = history[-1] - history[-2]
                    
                    if growth > ABNORMAL_GROWTH_BYTES_PER_INTERVAL:
                        growth_mb = growth / (1024 * 1024)
                        msg = f"Abnormal Storage Growth: PVC '{pvc_name}' grew by {growth_mb:.2f}MB in 30 seconds"
                        print(f"[StorageAgent] ALERT - PVC '{pvc_name}': {msg}")
                        
                        alert = DBAlert(
                            pod_name=f"pvc:{pvc_name}",
                            cpu_value=percentage_used,
                            message=msg
                        )
                        db.add(alert)
                        db.commit()
            
            db.close()
        except Exception as e:
            print(f"Error in Storage monitoring agent iteration: {e}")
            
        # Run loop every 30 seconds
        await asyncio.sleep(30)
