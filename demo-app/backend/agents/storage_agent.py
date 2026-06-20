import asyncio
import os
import sys
import numpy as np
from datetime import datetime

# Ensure paths resolve properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db as db_mod
from models.alert import DBAlert
from services.prometheus_service import PrometheusService

# In-memory dictionary to track historical used bytes per PVC
pvc_growth_history = {}
HISTORY_WINDOW_LIMIT = 50

# Thresholds
SATURATION_THRESHOLD_PERCENT = 85.0
ABNORMAL_GROWTH_BYTES_PER_INTERVAL = 1024 * 1024  # 1 MB growth in 30 seconds

async def run_storage_agent():
    print("Storage Monitoring Agent started successfully.")
    prometheus_service = PrometheusService()
    
    # Wait initially to give FastAPI startup & DB init time to complete
    await asyncio.sleep(15)
    
    while True:
        try:
            # Fetch PVC metrics from Prometheus
            pvc_metrics = await prometheus_service.get_pvc_metrics()
            
            # Open database session
            db = db_mod.SessionLocal()
            
            for pvc in pvc_metrics:
                pvc_name = pvc["pvc_name"]
                used_bytes = pvc["used_bytes"]
                capacity_bytes = pvc["capacity_bytes"]
                percentage_used = pvc["percentage_used"]
                
                # Check for Saturation (exceeding 85% capacity)
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
                
                # Track Growth History for anomaly detection
                if pvc_name not in pvc_growth_history:
                    pvc_growth_history[pvc_name] = []
                
                pvc_growth_history[pvc_name].append(used_bytes)
                if len(pvc_growth_history[pvc_name]) > HISTORY_WINDOW_LIMIT:
                    pvc_growth_history[pvc_name].pop(0)
                    
                history = pvc_growth_history[pvc_name]
                
                # Check for Abnormal Storage Growth (if we have at least 2 points)
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
            
        # Run check every 30 seconds
        await asyncio.sleep(30)
