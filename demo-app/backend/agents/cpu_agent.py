import asyncio
import os
import sys
import numpy as np
from datetime import datetime
from sklearn.ensemble import IsolationForest

# Ensure paths resolve properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.db as db_mod
from models.alert import DBAlert
from services.prometheus_service import PrometheusService

# In-memory dictionary storing historical CPU values per pod
pod_cpu_history = {}
HISTORY_WINDOW_LIMIT = 50
MIN_HISTORY_REQUIRED = 5  # Start fitting once we have 5 data points

async def run_cpu_agent():
    print("CPU Anomaly Detection Agent started successfully.")
    prometheus_service = PrometheusService()
    
    # Wait initially to give FastAPI startup & DB init time to complete
    await asyncio.sleep(10)
    
    while True:
        try:
            # Retrieve metrics
            metrics = await prometheus_service.get_cpu_metrics()
            
            # Open database session using dynamically resolved SessionLocal
            db = db_mod.SessionLocal()
            
            for item in metrics:
                pod = item["pod"]
                cores = item["cpu_cores"]
                
                # Skip zero or low-load targets to ignore inactive pods
                if cores < 0.0001:
                    continue
                
                if pod not in pod_cpu_history:
                    pod_cpu_history[pod] = []
                
                # Append current core value to the list
                pod_cpu_history[pod].append(cores)
                
                # Truncate history window if it gets too large
                if len(pod_cpu_history[pod]) > HISTORY_WINDOW_LIMIT:
                    pod_cpu_history[pod].pop(0)
                    
                history = pod_cpu_history[pod]
                
                # Run Isolation Forest anomaly detection if we have enough sample points
                if len(history) >= MIN_HISTORY_REQUIRED:
                    X = np.array(history).reshape(-1, 1)
                    
                    # Fit Isolation Forest
                    clf = IsolationForest(contamination=0.1, random_state=42)
                    clf.fit(X)
                    
                    # Predict anomaly for the current latest metric point
                    latest_point = np.array([[cores]])
                    prediction = clf.predict(latest_point)[0]
                    
                    # Calculate historical median of past metrics (excluding the latest data point)
                    historical_median = np.median(history[:-1]) if len(history) > 1 else 0
                    
                    # Check if predicted as anomaly AND it is a high-value spike
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
            
        # Scrape and run model every 30 seconds
        await asyncio.sleep(30)
