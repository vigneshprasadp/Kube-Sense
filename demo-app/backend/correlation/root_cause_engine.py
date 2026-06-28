import asyncio
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from kubernetes import client, config

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import traceback
import database.db as db_module
from models.alert import DBAlert, DBNetworkAlert
from models.rca import DBRootCauseReport
import agents.dependency_mapper as dependency_mapper

async def run_rca_engine():
    print("Root Cause Analysis (RCA) Engine started successfully.")
    
    # Let the DB initialize
    await asyncio.sleep(10)
    
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
                # Active chaos check
                from models.chaos_event import DBChaosEvent
                active_chaos = db.query(DBChaosEvent).filter(
                    DBChaosEvent.status == "active"
                ).order_by(DBChaosEvent.id.desc()).first()

                # Fetch recent alerts (last 5 minutes)
                time_threshold = datetime.utcnow() - timedelta(minutes=5)
                
                cpu_storage_alerts = db.query(DBAlert).filter(DBAlert.timestamp >= time_threshold).all()
                network_alerts = db.query(DBNetworkAlert).filter(DBNetworkAlert.timestamp >= time_threshold).all()
                
                if not active_chaos and not cpu_storage_alerts and not network_alerts:
                    db.close()
                    await asyncio.sleep(20)
                    continue

                # Get active service dependency graph
                topo = dependency_mapper.latest_topology
                nodes = {node["id"]: node for node in topo.get("nodes", [])}
                adjacency = topo.get("adjacency", {})

                # Log root cause directly if chaos is active
                if active_chaos:
                    svc_name = active_chaos.target_service
                    event_type = active_chaos.event_type
                    severity = active_chaos.severity or "Critical"
                    conf = 0.95
                    if event_type == "storage":
                        cause_str = f"{svc_name.capitalize()} Storage Saturation"
                        severity = "Critical"
                    elif event_type == "cpu":
                        cause_str = f"{svc_name.capitalize()} CPU Saturation"
                    elif event_type == "memory":
                        cause_str = f"{svc_name.capitalize()} Memory Saturation"
                        severity = "Critical"
                    elif event_type == "network":
                        cause_str = f"{svc_name.capitalize()} Connection Latency / Packet Loss"
                    elif event_type == "pod_crash":
                        cause_str = f"{svc_name.capitalize()} Pod Crash Failure"
                        severity = "Critical"
                    else:
                        cause_str = f"{svc_name.capitalize()} Simulated Chaos Anomaly"

                    evidence_bullet_list = [
                        f"Active fault injection scenario '{event_type}' detected on target '{svc_name}'",
                        f"Telemetry metrics for service '{svc_name}' overridden by Chaos Engine",
                    ]
                    
                    for a in cpu_storage_alerts:
                        if svc_name in a.pod_name.lower():
                            evidence_bullet_list.append(a.message)
                    for a in network_alerts:
                        if a.source_service == svc_name or a.target_service == svc_name:
                            evidence_bullet_list.append(a.message)
                            
                    evidence_bullet = "\n- ".join(evidence_bullet_list)
                    msg = (
                        f"Primary Root Cause identified at the '{svc_name}' service due to simulated chaos. "
                        f"Confidence score calculated as {int(conf * 100)}%. "
                        f"Active evidence points to:\n- {evidence_bullet}"
                    )
                    recent_limit = datetime.utcnow() - timedelta(minutes=2)
                    existing_report = db.query(DBRootCauseReport).filter(
                        DBRootCauseReport.root_cause == cause_str,
                        DBRootCauseReport.timestamp >= recent_limit
                    ).first()
                    
                    affected = list(adjacency.get(svc_name, []))
                    affected_str = ", ".join(affected) if affected else "None"
                    
                    if existing_report:
                        existing_report.timestamp = datetime.utcnow()
                        existing_report.confidence_score = conf
                        existing_report.message = msg
                        existing_report.affected_services = affected_str
                        db.commit()
                        db.refresh(existing_report)
                        print(f"[RCA Engine] Updated active chaos Root Cause: {cause_str} (Confidence: 95%)")
                        target_report = existing_report
                    else:
                        new_report = DBRootCauseReport(
                            root_cause=cause_str,
                            affected_services=affected_str,
                            severity=severity,
                            confidence_score=conf,
                            message=msg
                        )
                        db.add(new_report)
                        db.commit()
                        db.refresh(new_report)
                        print(f"[RCA Engine] LOGGED NEW CHAOS ROOT CAUSE: {cause_str} (Confidence: 95%)")
                        target_report = new_report
                        
                    try:
                        from recommendation.recommendation_engine import generate_recommendation
                        await generate_recommendation(target_report, db)
                    except Exception as rec_err:
                        print(f"[RCA Engine] Failed to auto-generate recommendation for active chaos: {rec_err}")
                    db.close()
                    await asyncio.sleep(20)
                    continue

                # Get active service dependency graph
                topo = dependency_mapper.latest_topology
                nodes = {node["id"]: node for node in topo.get("nodes", [])}
                adjacency = topo.get("adjacency", {})

                # Fetch Kubernetes events
                k8s_events = []
                if k8s_api:
                    try:
                        events_list = k8s_api.list_namespaced_event(namespace="tasksphere-app")
                        for event in events_list.items:
                            last_ts = event.last_timestamp or event.event_time
                            if last_ts:
                                if hasattr(last_ts, "tzinfo") and last_ts.tzinfo:
                                    last_ts = last_ts.astimezone(None).replace(tzinfo=None)
                                if (datetime.utcnow() - last_ts).total_seconds() < 300:
                                    k8s_events.append(event)
                    except Exception as e:
                        print(f"[RCA Engine] Error fetching Kubernetes events: {e}")

                # Analyze services for root causes
                services_to_analyze = ["frontend", "backend", "database"]
                candidates = []

                for svc in services_to_analyze:
                    cpu_score = 0.0
                    storage_score = 0.0
                    network_score = 0.0
                    dep_score = 0.0
                    
                    evidence_messages = []

                    # CPU Score
                    svc_cpu_alerts = [
                        a for a in cpu_storage_alerts 
                        if svc in a.pod_name.lower() and not a.pod_name.startswith("pvc:")
                    ]
                    if svc_cpu_alerts:
                        cpu_score = 0.40
                        median_val = max([a.cpu_value for a in svc_cpu_alerts])
                        evidence_messages.append(f"High CPU Anomaly detected (Max value: {median_val:.3f} cores)")

                    # Storage Score
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

                    # Network Score
                    svc_network_alerts = [
                        a for a in network_alerts 
                        if a.source_service == svc or a.target_service == svc
                    ]
                    if svc_network_alerts:
                        network_score = 0.20
                        max_lat = max([a.metric_value for a in svc_network_alerts])
                        metric_types = ", ".join(list(set([a.metric_name for a in svc_network_alerts])))
                        evidence_messages.append(f"Network anomaly on link ({metric_types}: {max_lat:.1f})")

                    # Dependency Match
                    dependencies_of_svc = [
                        src for src, dsts in adjacency.items() 
                        if svc in dsts
                    ]
                    has_dependent_alerts = False
                    for dep in dependencies_of_svc:
                        dep_alerts = [a for a in cpu_storage_alerts if dep in a.pod_name.lower()] or \
                                     [a for a in network_alerts if a.source_service == dep or a.target_service == dep]
                        if dep_alerts:
                            has_dependent_alerts = True
                            evidence_messages.append(f"Dependent downstream service '{dep}' is also experiencing alerts")
                            break
                    if has_dependent_alerts and (cpu_score > 0 or storage_score > 0 or network_score > 0):
                        dep_score = 0.10

                    # Kubernetes Events adjustment
                    event_evidence = []
                    for ev in k8s_events:
                        obj_name = ev.involved_object.name.lower()
                        if svc in obj_name or (svc == "database" and "postgres" in obj_name):
                            if ev.type == "Warning":
                                event_evidence.append(f"Kubernetes Event Warning: {ev.reason} - {ev.message}")
                    
                    if event_evidence:
                        evidence_messages.extend(event_evidence)
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

                # Determine primary root cause
                if candidates:
                    candidates.sort(key=lambda x: x["confidence"], reverse=True)
                    primary = candidates[0]
                    
                    svc_name = primary["service"]
                    conf = primary["confidence"]
                    
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
                        affected = list(adjacency.get(svc_name, []))
                        
                    affected_str = ", ".join(affected) if affected else "None"
                    
                    evidence_bullet = "\n- ".join(primary["evidence"])
                    msg = (
                        f"Primary Root Cause identified at the '{svc_name}' service. "
                        f"Confidence score calculated as {int(conf * 100)}%. "
                        f"Active evidence points to:\n- {evidence_bullet}"
                    )
                    
                    # Deduplicate within 2 minutes
                    recent_limit = datetime.utcnow() - timedelta(minutes=2)
                    existing_report = db.query(DBRootCauseReport).filter(
                        DBRootCauseReport.root_cause == cause_str,
                        DBRootCauseReport.timestamp >= recent_limit
                    ).first()
                    
                    if existing_report:
                        existing_report.timestamp = datetime.utcnow()
                        existing_report.confidence_score = conf
                        existing_report.message = msg
                        existing_report.affected_services = affected_str
                        db.commit()
                        db.refresh(existing_report)
                        print(f"[RCA Engine] Updated existing Root Cause: {cause_str} (Confidence: {int(conf * 100)}%)")
                        target_report = existing_report
                    else:
                        new_report = DBRootCauseReport(
                            root_cause=cause_str,
                            affected_services=affected_str,
                            severity=severity,
                            confidence_score=conf,
                            message=msg
                        )
                        db.add(new_report)
                        db.commit()
                        db.refresh(new_report)
                        print(f"[RCA Engine] LOGGED NEW ROOT CAUSE: {cause_str} (Confidence: {int(conf * 100)}%)")
                        target_report = new_report
                        
                    # Generate recommendations
                    try:
                        from recommendation.recommendation_engine import generate_recommendation
                        await generate_recommendation(target_report, db)
                    except Exception as rec_err:
                        print(f"[RCA Engine] Failed to auto-generate recommendation for candidate RCA: {rec_err}")

            except Exception as e:
                print(f"[RCA Engine] Database error in detection logic: {e}")
                db.rollback()
            finally:
                db.close()
                
        except Exception as e:
            print(f"[RCA Engine] Unhandled exception: {e}")
            traceback.print_exc()
            
        await asyncio.sleep(20)
