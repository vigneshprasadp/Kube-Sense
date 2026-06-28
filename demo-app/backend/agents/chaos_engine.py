import os
import sys
import asyncio
import time
import shutil
import multiprocessing
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.db as db_module
from models.chaos_event import DBChaosEvent
from models.alert import DBAlert, DBNetworkAlert
from models.forecast import DBForecast
from models.rca import DBRootCauseReport

try:
    from kubernetes import client, config
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False

# Active chaos event metadata
active_event: Optional[Dict] = None
 
# Process & thread state trackers
_cpu_processes: List[multiprocessing.Process] = []
_memory_holder: List[bytearray] = []
_storage_running = False
_network_running = False




def _cpu_stress_target():
    """Tight loop to exhaust CPU cores."""
    while True:
        x = 999999
        _ = x ** x


def start_cpu_stress(severity: str):
    global _cpu_processes
    stop_cpu_stress()
    
    num_cores = 1
    if severity == "medium":
        num_cores = 2
    elif severity == "high":
        num_cores = 4
        
    print(f"[ChaosEngine] Starting CPU saturation workload using {num_cores} cores.")
    for _ in range(num_cores):
        p = multiprocessing.Process(target=_cpu_stress_target, daemon=True)
        p.start()
        _cpu_processes.append(p)


def stop_cpu_stress():
    global _cpu_processes
    if _cpu_processes:
        print(f"[ChaosEngine] Stopping CPU saturation workload.")
        for p in _cpu_processes:
            try:
                p.terminate()
                p.join()
            except Exception:
                pass
        _cpu_processes = []


def _storage_write_loop(temp_dir: str):
    global _storage_running
    print(f"[ChaosEngine] Starting Storage leak files creation in {temp_dir}.")
    os.makedirs(temp_dir, exist_ok=True)
    count = 0
    try:
        while _storage_running:
            filepath = os.path.join(temp_dir, f"file_{count}.log")
            with open(filepath, "wb") as f:
                f.write(os.urandom(10 * 1024 * 1024))
            count += 1
            time.sleep(5)
    except Exception as e:
        print(f"[ChaosEngine] Storage write loop exception: {e}")


def start_storage_stress():
    global _storage_running
    stop_storage_stress()
    _storage_running = True
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chaos_storage_temp")
    t = threading.Thread(target=_storage_write_loop, args=(temp_dir,), daemon=True)
    t.start()


def stop_storage_stress():
    global _storage_running
    _storage_running = False
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chaos_storage_temp")
    if os.path.exists(temp_dir):
        print(f"[ChaosEngine] Cleaning up temporary storage leak files.")
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"[ChaosEngine] Error deleting storage leak files: {e}")


def _network_ping_loop(url: str):
    global _network_running
    import httpx
    print(f"[ChaosEngine] Starting Network traffic overload requests to {url}.")
    
    async def make_requests():
        async with httpx.AsyncClient() as client:
            while _network_running:
                try:
                    # Send parallel tasks
                    tasks = [client.get(url, timeout=2.0) for _ in range(10)]
                    await asyncio.gather(*tasks, return_exceptions=True)
                except Exception:
                    pass
                await asyncio.sleep(0.5)

    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(make_requests())
    except Exception as e:
        print(f"[ChaosEngine] Network traffic overload loop exception: {e}")


def start_network_stress(target_service: str):
    global _network_running
    stop_network_stress()
    _network_running = True
    
    svc_port = "80" if target_service == "frontend" else "8000"
    url = f"http://{target_service}-service:{svc_port}/"
    if target_service == "database":
        url = "http://backend-service:8000/"
        
    t = threading.Thread(target=_network_ping_loop, args=(url,), daemon=True)
    t.start()


def stop_network_stress():
    global _network_running
    _network_running = False


def start_memory_stress(severity: str):
    global _memory_holder
    stop_memory_stress()
    mb_to_allocate = 256
    if severity == "medium":
        mb_to_allocate = 512
    elif severity == "high":
        mb_to_allocate = 768
    print(f"[ChaosEngine] Starting memory saturation workload allocating {mb_to_allocate} MB.")
    try:
        _memory_holder.append(bytearray(mb_to_allocate * 1024 * 1024))
    except Exception as e:
        print(f"[ChaosEngine] Error allocating memory: {e}")


def stop_memory_stress():
    global _memory_holder
    if _memory_holder:
        print(f"[ChaosEngine] Stopping memory saturation workload and freeing memory.")
        _memory_holder.clear()


def execute_pod_crash(target_service: str):
    """Call Kubernetes API to delete a pod matching the target service name."""
    if not K8S_AVAILABLE:
        print("[ChaosEngine] Kubernetes client library not available. Skipping real pod crash.")
        return
        
    try:
        try:
            config.load_incluster_config()
        except Exception:
            config.load_kube_config()
            
        v1 = client.CoreV1Api()
        pods = v1.list_namespaced_pod(namespace="tasksphere-app")
        
        target_pods = []
        for pod in pods.items:
            pod_name = pod.metadata.name
            if target_service == "database" and "postgres" in pod_name:
                target_pods.append(pod_name)
            elif target_service in pod_name:
                target_pods.append(pod_name)
                
        if not target_pods:
            print(f"[ChaosEngine] No pods found for target service '{target_service}'.")
            return
            
        for pod_name in target_pods:
            print(f"[ChaosEngine] Deleting pod '{pod_name}' in namespace 'tasksphere-app'...")
            v1.delete_namespaced_pod(name=pod_name, namespace="tasksphere-app")
    except Exception as e:
        print(f"[ChaosEngine] Kubernetes error executing pod deletion: {e}")




async def start_chaos_simulation(event_type: str, target_service: str, severity: str, db: Session) -> DBChaosEvent:
    global active_event
    
    # Stop any running chaos simulation first
    await stop_chaos_simulation(db=db)
    
    db_event = DBChaosEvent(
        event_type=event_type,
        target_service=target_service,
        severity=severity,
        start_time=datetime.utcnow(),
        status="active",
        chaos_metadata="{}"
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    active_event = {
        "id": db_event.id,
        "event_type": event_type,
        "target_service": target_service,
        "severity": severity,
        "start_time": db_event.start_time
    }
    
    print(f"[ChaosEngine] STARTED simulation ID {db_event.id}: {event_type} on {target_service} (Severity: {severity})")
    
    if event_type == "cpu":
        start_cpu_stress(severity)
    elif event_type == "memory":
        start_memory_stress(severity)
    elif event_type == "storage":
        start_storage_stress()
    elif event_type == "network":
        start_network_stress(target_service)
    elif event_type == "pod_crash":
        execute_pod_crash(target_service)
        
    return db_event


async def stop_chaos_simulation(event_id: Optional[int] = None, db: Optional[Session] = None) -> Optional[DBChaosEvent]:
    global active_event
    
    stop_cpu_stress()
    stop_memory_stress()
    stop_storage_stress()
    stop_network_stress()
    
    if not db:
        db = db_module.SessionLocal()
        close_db = True
    else:
        close_db = False
        
    try:
        query = db.query(DBChaosEvent).filter(DBChaosEvent.status == "active")
        if event_id:
            query = query.filter(DBChaosEvent.id == event_id)
        db_event = query.first()
        
        if db_event:
            db_event.status = "stopped"
            db_event.end_time = datetime.utcnow()
            db.commit()
            db.refresh(db_event)
            print(f"[ChaosEngine] STOPPED simulation ID {db_event.id}")
            active_event = None
            return db_event
            active_event = None
            return None
    except Exception as e:
        print(f"[ChaosEngine] Error in stop_chaos_simulation: {e}")
        return None
    finally:
        if close_db:
            db.close()


async def run_chaos_engine_loop():
    """Background timeline loop for injecting simulated chaos events."""
    print("[ChaosEngine] Background timeline loop watcher active.")
    
    # Prevent double-writing
    injected_timeline_steps = set()
    
    while True:
        try:
            if active_event:
                start_time = active_event["start_time"]
                event_type = active_event["event_type"]
                target = active_event["target_service"]
                event_id = active_event["id"]
                
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                
                db = db_module.SessionLocal()
                try:
                    # Check scenario milestones
                    if event_type == "cpu":
                        # Timeline: 30s Warn, 60s Forecast, 90s Crit, 120s RCA
                        if 30 <= elapsed < 60 and f"cpu_warn_{event_id}" not in injected_timeline_steps:
                            pod_name = f"{target}-pod-chaos-{event_id}"
                            alert = DBAlert(
                                pod_name=pod_name,
                                cpu_value=0.50,
                                message=f"CPU Anomaly Spike: 0.50 cores (Median: 0.15 cores) on {target}"
                            )
                            db.add(alert)
                            db.commit()
                            injected_timeline_steps.add(f"cpu_warn_{event_id}")
                            print(f"[ChaosTimeline] Injecting CPU Warning alert at {int(elapsed)}s")
                            
                        elif 60 <= elapsed < 90 and f"cpu_forecast_{event_id}" not in injected_timeline_steps:
                            # 60s Forecast
                            forecast = DBForecast(
                                resource_type="cpu",
                                service_name=target,
                                current_value=0.85,
                                predicted_value=0.90,
                                threshold=0.90,
                                minutes_to_breach=1.0,
                                trend_slope=0.05,
                                r_squared=0.98,
                                message="CPU breach predicted in 1 minute",
                                severity="Warning"
                            )
                            db.add(forecast)
                            db.commit()
                            injected_timeline_steps.add(f"cpu_forecast_{event_id}")
                            print(f"[ChaosTimeline] Injecting CPU Forecast at {int(elapsed)}s")
                            
                        elif 90 <= elapsed < 120 and f"cpu_crit_{event_id}" not in injected_timeline_steps:
                            # 90s Critical Alert
                            pod_name = f"{target}-pod-chaos-{event_id}"
                            alert = DBAlert(
                                pod_name=pod_name,
                                cpu_value=0.95,
                                message=f"CPU Critical Exhaustion Alert: 0.95 cores on {target} (Threshold: 90%)"
                            )
                            db.add(alert)
                            db.commit()
                            injected_timeline_steps.add(f"cpu_crit_{event_id}")
                            print(f"[ChaosTimeline] Injecting CPU Critical alert at {int(elapsed)}s")
                            
                        elif elapsed >= 120 and f"cpu_rca_{event_id}" not in injected_timeline_steps:
                            # 120s RCA report
                            rca = DBRootCauseReport(
                                root_cause=f"{target.capitalize()} CPU Saturation",
                                affected_services="database, frontend" if target == "backend" else "backend",
                                severity="Critical",
                                confidence_score=0.95,
                                message=f"Primary Root Cause identified at the '{target}' service. Confidence score calculated as 95%. Active evidence points to CPU Saturation (95% cores)."
                            )
                            db.add(rca)
                            db.commit()
                            injected_timeline_steps.add(f"cpu_rca_{event_id}")
                            print(f"[ChaosTimeline] Injecting CPU RCA report at {int(elapsed)}s")

                    elif event_type == "storage":
                        # Timeline:
                        # 60s: Storage Normal -> Rising
                        # 120s: Forecast Created
                        # 180s: Critical Storage Alert
                        if 60 <= elapsed < 120 and f"storage_rising_{event_id}" not in injected_timeline_steps:
                            alert = DBAlert(
                                pod_name="pvc:postgres-pvc",
                                cpu_value=60.0,
                                message="Abnormal Storage Growth: PVC 'postgres-pvc' grew by 10MB in 30 seconds"
                            )
                            db.add(alert)
                            db.commit()
                            injected_timeline_steps.add(f"storage_rising_{event_id}")
                            print(f"[ChaosTimeline] Injecting Storage Warning alert at {int(elapsed)}s")
                            
                        elif 120 <= elapsed < 180 and f"storage_forecast_{event_id}" not in injected_timeline_steps:
                            forecast = DBForecast(
                                resource_type="storage",
                                service_name="postgres-pvc",
                                current_value=80.0,
                                predicted_value=85.0,
                                threshold=85.0,
                                minutes_to_breach=10.0,
                                trend_slope=0.03,
                                r_squared=0.97,
                                message="Storage Exhaustion Forecast: PVC 'postgres-pvc' is growing. Estimated to exceed 85% capacity in 10 minutes.",
                                severity="Warning"
                            )
                            db.add(forecast)
                            db.commit()
                            injected_timeline_steps.add(f"storage_forecast_{event_id}")
                            print(f"[ChaosTimeline] Injecting Storage Forecast at {int(elapsed)}s")
                            
                        elif elapsed >= 180 and f"storage_crit_{event_id}" not in injected_timeline_steps:
                            alert = DBAlert(
                                pod_name="pvc:postgres-pvc",
                                cpu_value=90.0,
                                message="Storage Saturation Alert: PVC 'postgres-pvc' is 90% full (Threshold: 85%)"
                            )
                            rca = DBRootCauseReport(
                                root_cause="Database Storage Saturation",
                                affected_services="backend, frontend",
                                severity="Critical",
                                confidence_score=0.92,
                                message="Primary Root Cause identified as database storage saturation. Evidence: PVC 'postgres-pvc' usage at 90%."
                            )
                            db.add(alert)
                            db.add(rca)
                            db.commit()
                            injected_timeline_steps.add(f"storage_crit_{event_id}")
                            print(f"[ChaosTimeline] Injecting Storage Critical alert + RCA at {int(elapsed)}s")

                    elif event_type == "network":
                        # Timeline:
                        # 30s: Latency Warning
                        # 60s: Latency Forecast
                        # 90s: Latency RCA
                        if 30 <= elapsed < 60 and f"net_warn_{event_id}" not in injected_timeline_steps:
                            alert = DBNetworkAlert(
                                source_service="frontend",
                                target_service="backend",
                                metric_name="latency",
                                metric_value=210.0,
                                z_score=3.0,
                                message="High Network Latency Alert: frontend -> backend latency is 210ms (Threshold: 200ms)"
                            )
                            db.add(alert)
                            db.commit()
                            injected_timeline_steps.add(f"net_warn_{event_id}")
                            print(f"[ChaosTimeline] Injecting Network Congestion alert at {int(elapsed)}s")
                            
                        elif 60 <= elapsed < 90 and f"net_forecast_{event_id}" not in injected_timeline_steps:
                            forecast = DBForecast(
                                resource_type="network_latency",
                                service_name="frontend->backend",
                                current_value=240.0,
                                predicted_value=300.0,
                                threshold=1000.0,
                                minutes_to_breach=3.0,
                                trend_slope=5.0,
                                r_squared=0.95,
                                message="Network congestion likely within 3 minutes.",
                                severity="Warning"
                            )
                            db.add(forecast)
                            db.commit()
                            injected_timeline_steps.add(f"net_forecast_{event_id}")
                            print(f"[ChaosTimeline] Injecting Network Forecast at {int(elapsed)}s")
                            
                        elif elapsed >= 90 and f"net_rca_{event_id}" not in injected_timeline_steps:
                            rca = DBRootCauseReport(
                                root_cause="Backend Connection Latency / Packet Loss",
                                affected_services="frontend",
                                severity="Warning",
                                confidence_score=0.88,
                                message="Primary Root Cause identified at backend network link. Active evidence: latency (240ms), packet loss (5.5%)."
                            )
                            db.add(rca)
                            db.commit()
                            injected_timeline_steps.add(f"net_rca_{event_id}")
                            print(f"[ChaosTimeline] Injecting Network RCA report at {int(elapsed)}s")

                    elif event_type == "memory":
                        # Timeline:
                        # 30s: Memory Warning
                        # 60s: Forecast generated
                        # 90s: Critical Alert
                        # 120s: RCA generated
                        if 30 <= elapsed < 60 and f"mem_warn_{event_id}" not in injected_timeline_steps:
                            pod_name = f"{target}-pod-chaos-{event_id}"
                            alert = DBAlert(
                                pod_name=pod_name,
                                cpu_value=0.15,
                                message=f"Memory Anomaly Spike: 450MB (Median: 150MB) on {target}"
                            )
                            db.add(alert)
                            db.commit()
                            injected_timeline_steps.add(f"mem_warn_{event_id}")
                            print(f"[ChaosTimeline] Injecting Memory Warning alert at {int(elapsed)}s")
                            
                        elif 60 <= elapsed < 90 and f"mem_forecast_{event_id}" not in injected_timeline_steps:
                            forecast = DBForecast(
                                resource_type="memory",
                                service_name=target,
                                current_value=0.75,
                                predicted_value=0.90,
                                threshold=0.90,
                                minutes_to_breach=1.0,
                                trend_slope=0.05,
                                r_squared=0.98,
                                message="Memory breach predicted in 1 minute",
                                severity="Warning"
                            )
                            db.add(forecast)
                            db.commit()
                            injected_timeline_steps.add(f"mem_forecast_{event_id}")
                            print(f"[ChaosTimeline] Injecting Memory Forecast at {int(elapsed)}s")
                            
                        elif 90 <= elapsed < 120 and f"mem_crit_{event_id}" not in injected_timeline_steps:
                            pod_name = f"{target}-pod-chaos-{event_id}"
                            alert = DBAlert(
                                pod_name=pod_name,
                                cpu_value=0.15,
                                message=f"Memory Critical Saturation Alert: 920MB on {target} (Threshold: 90%)"
                            )
                            db.add(alert)
                            db.commit()
                            injected_timeline_steps.add(f"mem_crit_{event_id}")
                            print(f"[ChaosTimeline] Injecting Memory Critical alert at {int(elapsed)}s")
                            
                        elif elapsed >= 120 and f"mem_rca_{event_id}" not in injected_timeline_steps:
                            rca = DBRootCauseReport(
                                root_cause=f"{target.capitalize()} Memory Saturation",
                                affected_services="database, frontend" if target == "backend" else "backend",
                                severity="Critical",
                                confidence_score=0.95,
                                message=f"Primary Root Cause identified at the '{target}' service. Confidence score calculated as 95%. Active evidence points to Memory Saturation (95% usage)."
                            )
                            db.add(rca)
                            db.commit()
                            injected_timeline_steps.add(f"mem_rca_{event_id}")
                            print(f"[ChaosTimeline] Injecting Memory RCA report at {int(elapsed)}s")

                    elif event_type == "pod_crash":
                        # Timeline:
                        # 10s: Pod missing / Dependency status changes
                        # 30s: RCA Generated
                        if elapsed >= 30 and f"crash_rca_{event_id}" not in injected_timeline_steps:
                            rca = DBRootCauseReport(
                                root_cause=f"{target.capitalize()} service unavailable",
                                affected_services="frontend" if target == "backend" else "backend",
                                severity="Critical",
                                confidence_score=0.95,
                                message=f"Primary Root Cause: {target.capitalize()} service unavailable. Active evidence: pod terminated, network traffic dropped, service endpoints unavailable."
                            )
                            db.add(rca)
                            db.commit()
                            injected_timeline_steps.add(f"crash_rca_{event_id}")
                            print(f"[ChaosTimeline] Injecting Pod Crash RCA report at {int(elapsed)}s")
                except Exception as e:
                    print(f"[ChaosEngine] Database insert error in timeline loop: {e}")
                    db.rollback()
                finally:
                    db.close()
            
            # Watch timeline loops every 2 seconds
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[ChaosEngine] Timeline watcher loop exception: {e}")
            await asyncio.sleep(5)
