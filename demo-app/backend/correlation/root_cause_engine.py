import asyncio
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from kubernetes import client, config

# Resolve backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import traceback
import database.db as db_module
from models.alert import DBAlert, DBNetworkAlert
from models.rca import DBRootCauseReport
import agents.dependency_mapper as dependency_mapper

async def run_rca_engine():
    print("Root Cause Analysis (RCA) Engine started successfully.")
    
    # Wait for the DB to be ready and initialized
    await asyncio.sleep(10)
    
    # Load Kubernetes Client for live events
    k8s_api = None
    try:
        config.load_incluster_config()
        k8s_api = client.CoreV1Api()
        print("[RCA Engine] Kubernetes in-cluster config loaded.")
    except Exception:
        try:
            config.load_kube_config()
            k8s_api = client.CoreV1Api()
            print("[RCA Engine] Fallback: Local kubeconfig loaded.")
        except Exception as e:
            print(f"[RCA Engine] Warning: Kubernetes API unreachable: {e}. Running in standalone mode.")

    while True:
        try:
            db: Session = db_module.SessionLocal()
            try:
                # 1. Fetch recent alerts (last 5 minutes)
                time_threshold = datetime.utcnow() - timedelta(minutes=5)
                
                cpu_storage_alerts = db.query(DBAlert).filter(DBAlert.timestamp >= time_threshold).all()
                network_alerts = db.query(DBNetworkAlert).filter(DBNetworkAlert.timestamp >= time_threshold).all()
                
                # If no alerts, nothing is wrong
                if not cpu_storage_alerts and not network_alerts:
                    db.close()
                    await asyncio.sleep(20)
                    continue

                # 2. Get active service dependency graph
                # latest_topology schema: {"nodes": [...], "edges": [...], "adjacency": {...}}
                topo = dependency_mapper.latest_topology
                nodes = {node["id"]: node for node in topo.get("nodes", [])}
                adjacency = topo.get("adjacency", {})

                # 3. Retrieve Kubernetes events
                k8s_events = []
                if k8s_api:
                    try:
                        events_list = k8s_api.list_namespaced_event(namespace="tasksphere-app")
                        # Filter events from the last 5 minutes
                        for event in events_list.items:
                            # Parse timestamp
                            last_ts = event.last_timestamp or event.event_time
                            if last_ts:
                                # Convert to timezone-naive UTC datetime for comparison
                                if hasattr(last_ts, "tzinfo") and last_ts.tzinfo:
                                    last_ts = last_ts.astimezone(None).replace(tzinfo=None)
                                # Check if it's within the threshold
                                if (datetime.utcnow() - last_ts).total_seconds() < 300:
                                    k8s_events.append(event)
                    except Exception as e:
                        print(f"[RCA Engine] Error fetching Kubernetes events: {e}")

                # 4. Core correlation logic
                # We analyze the three primary services: frontend, backend, database
                services_to_analyze = ["frontend", "backend", "database"]
                candidates = []

                for svc in services_to_analyze:
                    cpu_score = 0.0
                    storage_score = 0.0
                    network_score = 0.0
                    dep_score = 0.0
                    
                    evidence_messages = []

                    # A. CPU Score (40% weight)
                    # Check for CPU alerts on pods of this service
                    svc_cpu_alerts = [
                        a for a in cpu_storage_alerts 
                        if svc in a.pod_name.lower() and not a.pod_name.startswith("pvc:")
                    ]
                    if svc_cpu_alerts:
                        cpu_score = 0.40
                        median_val = max([a.cpu_value for a in svc_cpu_alerts])
                        evidence_messages.append(f"High CPU Anomaly detected (Max value: {median_val:.3f} cores)")

                    # B. Storage Score (30% weight)
                    # For database, check PVC alerts or postgres-pvc alert
                    svc_storage_alerts = []
                    if svc == "database":
                        svc_storage_alerts = [
                            a for a in cpu_storage_alerts 
                            if a.pod_name.startswith("pvc:") or "postgres" in a.pod_name.lower() or "storage" in a.message.lower()
                        ]
                    if svc_storage_alerts:
                        storage_score = 0.30
                        max_pct = max([a.cpu_value for a in svc_storage_alerts])
                        evidence_messages.append(f"Storage Saturation / PVC growth anomaly detected ({max_pct:.1f}% capacity/MB)")

                    # C. Network Score (20% weight)
                    # Check if the service is a source or target of a network latency/drop alert
                    svc_network_alerts = [
                        a for a in network_alerts 
                        if a.source_service == svc or a.target_service == svc
                    ]
                    if svc_network_alerts:
                        network_score = 0.20
                        max_lat = max([a.metric_value for a in svc_network_alerts])
                        metric_types = ", ".join(list(set([a.metric_name for a in svc_network_alerts])))
                        evidence_messages.append(f"Network anomaly on link ({metric_types}: {max_lat:.1f})")

                    # D. Dependency Match (10% weight)
                    # If this service is a dependency of another service that has alerts, and this service itself has alerts
                    dependencies_of_svc = [
                        src for src, dsts in adjacency.items() 
                        if svc in dsts
                    ]
                    has_dependent_alerts = False
                    for dep in dependencies_of_svc:
                        # If a dependent service has active alerts
                        dep_alerts = [a for a in cpu_storage_alerts if dep in a.pod_name.lower()] or \
                                     [a for a in network_alerts if a.source_service == dep or a.target_service == dep]
                        if dep_alerts:
                            has_dependent_alerts = True
                            evidence_messages.append(f"Dependent downstream service '{dep}' is also experiencing alerts")
                            break
                    if has_dependent_alerts and (cpu_score > 0 or storage_score > 0 or network_score > 0):
                        dep_score = 0.10

                    # E. Kubernetes Events adjustment (extra weight / evidence)
                    event_evidence = []
                    for ev in k8s_events:
                        obj_name = ev.involved_object.name.lower()
                        if svc in obj_name or (svc == "database" and "postgres" in obj_name):
                            if ev.type == "Warning":
                                event_evidence.append(f"Kubernetes Event Warning: {ev.reason} - {ev.message}")
                    
                    if event_evidence:
                        evidence_messages.extend(event_evidence)
                        # Slightly bump confidence if K8s events confirm failures
                        dep_score = min(0.10, dep_score + 0.05)

                    total_confidence = cpu_score + storage_score + network_score + dep_score

                    if total_confidence > 0.25:
                        candidates.append({
                            "service": svc,
                            "confidence": total_confidence,
                            "cpu": cpu_score,
                            "storage": storage_score,
                            "network": network_score,
                            "dependency": dep_score,
                            "evidence": evidence_messages
                        })

                # If we have candidates, determine primary root cause (highest confidence)
                if candidates:
                    candidates.sort(key=lambda x: x["confidence"], reverse=True)
                    primary = candidates[0]
                    
                    svc_name = primary["service"]
                    conf = primary["confidence"]
                    
                    # Deduce cause string
                    cause_str = ""
                    severity = "Warning"
                    
                    if primary["storage"] > 0:
                        cause_str = f"{svc_name.capitalize()} Storage Saturation"
                        severity = "Critical"
                    elif primary["cpu"] > 0 and primary["network"] > 0:
                        cause_str = f"{svc_name.capitalize()} CPU Saturation / Network Latency Chain"
                        severity = "Critical"
                    elif primary["cpu"] > 0:
                        cause_str = f"{svc_name.capitalize()} CPU Saturation"
                    elif primary["network"] > 0:
                        cause_str = f"{svc_name.capitalize()} Connection Latency / Packet Loss"
                    else:
                        cause_str = f"{svc_name.capitalize()} Telemetry Outlier Anomaly"
                        
                    affected = [c["service"] for c in candidates if c["service"] != svc_name]
                    if not affected:
                        # Fallback list based on adjacency
                        affected = list(adjacency.get(svc_name, []))
                        
                    affected_str = ", ".join(affected) if affected else "None"
                    
                    # Create description message
                    evidence_bullet = "\n- ".join(primary["evidence"])
                    msg = (
                        f"Primary Root Cause identified at the '{svc_name}' service. "
                        f"Confidence score calculated as {int(conf * 100)}%. "
                        f"Active evidence points to:\n- {evidence_bullet}"
                    )
                    
                    # Check database to see if we already logged this root cause in the last 2 minutes
                    recent_limit = datetime.utcnow() - timedelta(minutes=2)
                    existing_report = db.query(DBRootCauseReport).filter(
                        DBRootCauseReport.root_cause == cause_str,
                        DBRootCauseReport.timestamp >= recent_limit
                    ).first()
                    
                    if existing_report:
                        # Update existing report's timestamp and confidence/message
                        existing_report.timestamp = datetime.utcnow()
                        existing_report.confidence_score = conf
                        existing_report.message = msg
                        existing_report.affected_services = affected_str
                        print(f"[RCA Engine] Updated existing Root Cause: {cause_str} (Confidence: {int(conf * 100)}%)")
                    else:
                        # Create a new report
                        new_report = DBRootCauseReport(
                            root_cause=cause_str,
                            affected_services=affected_str,
                            severity=severity,
                            confidence_score=conf,
                            message=msg
                        )
                        db.add(new_report)
                        print(f"[RCA Engine] LOGGED NEW ROOT CAUSE: {cause_str} (Confidence: {int(conf * 100)}%)")
                        
                    db.commit()

            except Exception as e:
                print(f"[RCA Engine] Database error in detection logic: {e}")
                db.rollback()
            finally:
                db.close()
                
        except Exception as e:
            print(f"[RCA Engine] Unhandled exception: {e}")
            traceback.print_exc()
            
        await asyncio.sleep(20)
