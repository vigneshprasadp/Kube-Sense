import os
import httpx
from fastapi import HTTPException

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
PROMETHEUS_QUERY_API = f"{PROMETHEUS_URL}/api/v1/query"

class PrometheusService:
    def __init__(self, prometheus_url: str = PROMETHEUS_URL):
        self.prometheus_url = prometheus_url
        self.query_api = f"{prometheus_url}/api/v1/query"

    async def execute_query(self, query: str):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.query_api, params={"query": query}, timeout=5.0)
                if response.status_code != 200:
                    raise HTTPException(status_code=500, detail=f"Prometheus returned status {response.status_code}")
                return response.json()
            except httpx.RequestError as e:
                raise HTTPException(status_code=503, detail=f"Failed to connect to Prometheus: {e}")

    async def get_cpu_metrics(self):
        from agents.chaos_engine import active_event
        from datetime import datetime

        query = 'sum(rate(container_cpu_usage_seconds_total{pod!=""}[5m])) by (pod)'
        result = await self.execute_query(query)
        formatted = []
        for item in result.get("data", {}).get("result", []):
            metric = item.get("metric", {})
            value = item.get("value", [0, "0"])
            formatted.append({
                "pod": metric.get("pod", "unknown"),
                "cpu_cores": float(value[1])
            })

        # Chaos override
        if active_event and active_event["event_type"] == "cpu":
            target = active_event["target_service"]
            elapsed = (datetime.utcnow() - active_event["start_time"]).total_seconds()
            if elapsed < 20:
                cores_val = 0.20
            elif elapsed < 45:
                cores_val = 0.35
            elif elapsed < 75:
                cores_val = 0.50
            elif elapsed < 100:
                cores_val = 0.70
            elif elapsed < 120:
                cores_val = 0.85
            else:
                cores_val = 0.95
                
            found = False
            for item in formatted:
                if target in item["pod"]:
                    item["cpu_cores"] = cores_val
                    found = True
            if not found:
                formatted.append({
                    "pod": f"{target}-chaos-pod",
                    "cpu_cores": cores_val
                })
        elif active_event and active_event["event_type"] == "pod_crash":
            target = active_event["target_service"]
            formatted = [item for item in formatted if target not in item["pod"]]

        return formatted

    async def get_memory_metrics(self):
        from agents.chaos_engine import active_event
        from datetime import datetime

        query = 'sum(container_memory_working_set_bytes{pod!=""}) by (pod)'
        result = await self.execute_query(query)
        formatted = []
        for item in result.get("data", {}).get("result", []):
            metric = item.get("metric", {})
            value = item.get("value", [0, "0"])
            formatted.append({
                "pod": metric.get("pod", "unknown"),
                "memory_bytes": int(value[1]),
                "memory_mb": round(int(value[1]) / (1024 * 1024), 2)
            })

        # Chaos override
        if active_event and active_event["event_type"] == "memory":
            target = active_event["target_service"]
            elapsed = (datetime.utcnow() - active_event["start_time"]).total_seconds()
            if elapsed < 30:
                mem_pct = 30.0
            elif elapsed < 60:
                mem_pct = 45.0
            elif elapsed < 90:
                mem_pct = 60.0
            elif elapsed < 120:
                mem_pct = 75.0
            else:
                mem_pct = 90.0
                
            max_mb = 1024.0
            memory_mb = max_mb * (mem_pct / 100.0)
            memory_bytes = int(memory_mb * 1024 * 1024)
            
            found = False
            for item in formatted:
                if target in item["pod"]:
                    item["memory_bytes"] = memory_bytes
                    item["memory_mb"] = memory_mb
                    found = True
            if not found:
                formatted.append({
                    "pod": f"{target}-chaos-pod",
                    "memory_bytes": memory_bytes,
                    "memory_mb": memory_mb
                })
        elif active_event and active_event["event_type"] == "pod_crash":
            target = active_event["target_service"]
            formatted = [item for item in formatted if target not in item["pod"]]

        return formatted

    async def get_storage_metrics(self):
        from agents.chaos_engine import active_event

        # Fallback to filesystem writes metrics since direct container capacity metrics are omitted in cAdvisor node limits on Minikube
        query = 'sum(container_fs_writes_bytes_total{pod!=""}) by (pod)'
        result = await self.execute_query(query)
        formatted = []
        for item in result.get("data", {}).get("result", []):
            metric = item.get("metric", {})
            value = item.get("value", [0, "0"])
            formatted.append({
                "pod": metric.get("pod", "unknown"),
                "storage_bytes": int(value[1]),
                "storage_mb": round(int(value[1]) / (1024 * 1024), 2)
            })

        if active_event and active_event["event_type"] == "pod_crash":
            target = active_event["target_service"]
            formatted = [item for item in formatted if target not in item["pod"]]

        return formatted

    async def get_summary_metrics(self):
        cpu_query = 'sum(rate(container_cpu_usage_seconds_total{pod!=""}[5m])) by (pod)'
        mem_query = 'sum(container_memory_working_set_bytes{pod!=""}) by (pod)'
        storage_query = 'sum(container_fs_writes_bytes_total{pod!=""}) by (pod)'
        
        async with httpx.AsyncClient() as client:
            try:
                import asyncio
                cpu_task = client.get(self.query_api, params={"query": cpu_query}, timeout=5.0)
                mem_task = client.get(self.query_api, params={"query": mem_query}, timeout=5.0)
                storage_task = client.get(self.query_api, params={"query": storage_query}, timeout=5.0)
                
                cpu_res, mem_res, storage_res = await asyncio.gather(cpu_task, mem_task, storage_task)
                
                if any(r.status_code != 200 for r in [cpu_res, mem_res, storage_res]):
                    raise HTTPException(status_code=500, detail="Prometheus query failed")
                    
                cpu_data = cpu_res.json().get("data", {}).get("result", [])
                mem_data = mem_res.json().get("data", {}).get("result", [])
                storage_data = storage_res.json().get("data", {}).get("result", [])
                
                summary = {}
                for item in cpu_data:
                    pod = item.get("metric", {}).get("pod", "unknown")
                    summary[pod] = {"cpu_cores": float(item.get("value", [0, "0"])[1])}
                    
                for item in mem_data:
                    pod = item.get("metric", {}).get("pod", "unknown")
                    if pod not in summary:
                        summary[pod] = {}
                    mem_bytes = int(item.get("value", [0, "0"])[1])
                    summary[pod]["memory_bytes"] = mem_bytes
                    summary[pod]["memory_mb"] = round(mem_bytes / (1024 * 1024), 2)
                    
                for item in storage_data:
                    pod = item.get("metric", {}).get("pod", "unknown")
                    if pod not in summary:
                        summary[pod] = {}
                    storage_bytes = int(item.get("value", [0, "0"])[1])
                    summary[pod]["storage_bytes"] = storage_bytes
                    summary[pod]["storage_mb"] = round(storage_bytes / (1024 * 1024), 2)
                    
                # Apply Summary chaos overrides
                from agents.chaos_engine import active_event
                from datetime import datetime
                
                if active_event:
                    event_type = active_event["event_type"]
                    target = active_event["target_service"]
                    elapsed = (datetime.utcnow() - active_event["start_time"]).total_seconds()
                    
                    target_pod = None
                    for pod in list(summary.keys()):
                        if target in pod:
                            target_pod = pod
                            break
                    if not target_pod:
                        target_pod = f"{target}-chaos-pod"
                        summary[target_pod] = {
                            "cpu_cores": 0.05,
                            "memory_bytes": 100 * 1024 * 1024,
                            "memory_mb": 100.0,
                            "storage_bytes": 10 * 1024 * 1024,
                            "storage_mb": 10.0
                        }
                    
                    if event_type == "cpu":
                        if elapsed < 20:
                            cores_val = 0.20
                        elif elapsed < 45:
                            cores_val = 0.35
                        elif elapsed < 75:
                            cores_val = 0.50
                        elif elapsed < 100:
                            cores_val = 0.70
                        elif elapsed < 120:
                            cores_val = 0.85
                        else:
                            cores_val = 0.95
                        summary[target_pod]["cpu_cores"] = cores_val
                        
                    elif event_type == "memory":
                        if elapsed < 30:
                            mem_pct = 30.0
                        elif elapsed < 60:
                            mem_pct = 45.0
                        elif elapsed < 90:
                            mem_pct = 60.0
                        elif elapsed < 120:
                            mem_pct = 75.0
                        else:
                            mem_pct = 90.0
                        max_mb = 1024.0
                        summary[target_pod]["memory_mb"] = max_mb * (mem_pct / 100.0)
                        summary[target_pod]["memory_bytes"] = int(summary[target_pod]["memory_mb"] * 1024 * 1024)
                        
                    elif event_type == "pod_crash":
                        summary = {k: v for k, v in summary.items() if target not in k}
                        
                return summary
            except httpx.RequestError as e:
                raise HTTPException(status_code=503, detail=f"Failed to connect to Prometheus: {e}")

    async def get_pvc_metrics(self):
        used_query = 'kubelet_volume_stats_used_bytes{namespace="tasksphere-app"}'
        capacity_query = 'kubelet_volume_stats_capacity_bytes{namespace="tasksphere-app"}'
        
        async with httpx.AsyncClient() as client:
            try:
                import asyncio
                used_task = client.get(self.query_api, params={"query": used_query}, timeout=5.0)
                capacity_task = client.get(self.query_api, params={"query": capacity_query}, timeout=5.0)
                
                used_res, capacity_res = await asyncio.gather(used_task, capacity_task)
                
                if used_res.status_code != 200 or capacity_res.status_code != 200:
                    raise HTTPException(status_code=500, detail="Prometheus query failed for volume stats")
                
                used_data = used_res.json().get("data", {}).get("result", [])
                capacity_data = capacity_res.json().get("data", {}).get("result", [])
                
                pvc_metrics = {}
                
                for item in used_data:
                    metric = item.get("metric", {})
                    pvc_name = metric.get("persistentvolumeclaim", "unknown")
                    val = item.get("value", [0, "0"])[1]
                    pvc_metrics[pvc_name] = {
                        "pvc_name": pvc_name,
                        "used_bytes": int(val),
                        "used_mb": round(int(val) / (1024 * 1024), 2),
                        "capacity_bytes": 0,
                        "capacity_mb": 0.0,
                        "percentage_used": 0.0
                    }
                    
                for item in capacity_data:
                    metric = item.get("metric", {})
                    pvc_name = metric.get("persistentvolumeclaim", "unknown")
                    val = item.get("value", [0, "0"])[1]
                    if pvc_name not in pvc_metrics:
                        pvc_metrics[pvc_name] = {
                            "pvc_name": pvc_name,
                            "used_bytes": 0,
                            "used_mb": 0.0,
                            "capacity_bytes": int(val),
                            "capacity_mb": round(int(val) / (1024 * 1024), 2),
                            "percentage_used": 0.0
                        }
                    else:
                        cap_val = int(val)
                        pvc_metrics[pvc_name]["capacity_bytes"] = cap_val
                        pvc_metrics[pvc_name]["capacity_mb"] = round(cap_val / (1024 * 1024), 2)
                        if cap_val > 0:
                            pvc_metrics[pvc_name]["percentage_used"] = round(
                                (pvc_metrics[pvc_name]["used_bytes"] / cap_val) * 100, 2
                            )
                
                # Fallback: if no pvc metrics are found, generate simulated/mocked PVC metrics for testing
                if not pvc_metrics:
                    from agents.chaos_engine import active_event
                    import random
                    
                    cap_bytes = 1024 * 1024 * 1024  # 1Gi
                    is_storage_chaos = active_event and active_event["event_type"] == "storage"
                    
                    global _mock_pvc_used_bytes
                    if '_mock_pvc_used_bytes' not in globals():
                        globals()['_mock_pvc_used_bytes'] = 350 * 1024 * 1024  # Start at 350MB (35%)
                    
                    if is_storage_chaos:
                        # Grow by 2.1MB to 3.5MB to trigger abnormal growth anomaly (>2.0MB)
                        growth = random.uniform(2.1 * 1024 * 1024, 3.5 * 1024 * 1024)
                        globals()['_mock_pvc_used_bytes'] += int(growth)
                        if globals()['_mock_pvc_used_bytes'] > 0.92 * cap_bytes:
                            globals()['_mock_pvc_used_bytes'] = int(0.92 * cap_bytes)
                    else:
                        # Reset and keep stable at 350MB (35%) when healthy
                        globals()['_mock_pvc_used_bytes'] = 350 * 1024 * 1024
                        
                    used_bytes = globals()['_mock_pvc_used_bytes']
                    pct = round((used_bytes / cap_bytes) * 100, 2)
                    
                    pvc_metrics['postgres-pvc'] = {
                        "pvc_name": "postgres-pvc",
                        "used_bytes": used_bytes,
                        "used_mb": round(used_bytes / (1024 * 1024), 2),
                        "capacity_bytes": cap_bytes,
                        "capacity_mb": round(cap_bytes / (1024 * 1024), 2),
                        "percentage_used": pct
                    }
                
                # Apply Storage Chaos override
                from agents.chaos_engine import active_event
                from datetime import datetime
                if active_event and active_event["event_type"] == "storage":
                    elapsed = (datetime.utcnow() - active_event["start_time"]).total_seconds()
                    if elapsed < 30:
                        pct = 40.0
                    elif elapsed < 60:
                        pct = 50.0
                    elif elapsed < 90:
                        pct = 60.0
                    elif elapsed < 120:
                        pct = 70.0
                    elif elapsed < 150:
                        pct = 80.0
                    else:
                        pct = 90.0
                        
                    cap_bytes = 1024 * 1024 * 1024
                    used_bytes = int(cap_bytes * (pct / 100.0))
                    used_mb = round(used_bytes / (1024 * 1024), 2)
                    
                    for name in pvc_metrics:
                        if "postgres" in name:
                            pvc_metrics[name]["percentage_used"] = pct
                            pvc_metrics[name]["used_bytes"] = used_bytes
                            pvc_metrics[name]["used_mb"] = used_mb
                            pvc_metrics[name]["capacity_bytes"] = cap_bytes
                            pvc_metrics[name]["capacity_mb"] = round(cap_bytes / (1024 * 1024), 2)
                
                return list(pvc_metrics.values())
            except httpx.RequestError as e:
                raise HTTPException(status_code=503, detail=f"Failed to connect to Prometheus: {e}")

    async def get_network_metrics(self):
        rx_bytes_query = 'sum(rate(container_network_receive_bytes_total{namespace="tasksphere-app"}[5m])) by (pod)'
        tx_bytes_query = 'sum(rate(container_network_transmit_bytes_total{namespace="tasksphere-app"}[5m])) by (pod)'
        rx_dropped_query = 'sum(rate(container_network_receive_packets_dropped_total{namespace="tasksphere-app"}[5m])) by (pod)'
        rx_errors_query = 'sum(rate(container_network_receive_errors_total{namespace="tasksphere-app"}[5m])) by (pod)'
        
        async with httpx.AsyncClient() as client:
            try:
                import asyncio
                rx_bytes_task = client.get(self.query_api, params={"query": rx_bytes_query}, timeout=5.0)
                tx_bytes_task = client.get(self.query_api, params={"query": tx_bytes_query}, timeout=5.0)
                rx_dropped_task = client.get(self.query_api, params={"query": rx_dropped_query}, timeout=5.0)
                rx_errors_task = client.get(self.query_api, params={"query": rx_errors_query}, timeout=5.0)
                
                rx_res, tx_res, rx_drop_res, rx_err_res = await asyncio.gather(
                    rx_bytes_task, tx_bytes_task, rx_dropped_task, rx_errors_task
                )
                
                pod_rx_bytes = {}
                pod_tx_bytes = {}
                pod_rx_dropped = {}
                pod_rx_errors = {}
                
                if rx_res.status_code == 200:
                    for item in rx_res.json().get("data", {}).get("result", []):
                        pod = item.get("metric", {}).get("pod", "")
                        if pod:
                            pod_rx_bytes[pod] = float(item.get("value", [0, "0"])[1])
                if tx_res.status_code == 200:
                    for item in tx_res.json().get("data", {}).get("result", []):
                        pod = item.get("metric", {}).get("pod", "")
                        if pod:
                            pod_tx_bytes[pod] = float(item.get("value", [0, "0"])[1])
                if rx_drop_res.status_code == 200:
                    for item in rx_drop_res.json().get("data", {}).get("result", []):
                        pod = item.get("metric", {}).get("pod", "")
                        if pod:
                            pod_rx_dropped[pod] = float(item.get("value", [0, "0"])[1])
                if rx_err_res.status_code == 200:
                    for item in rx_err_res.json().get("data", {}).get("result", []):
                        pod = item.get("metric", {}).get("pod", "")
                        if pod:
                            pod_rx_errors[pod] = float(item.get("value", [0, "0"])[1])
            except Exception:
                pod_rx_bytes, pod_tx_bytes, pod_rx_dropped, pod_rx_errors = {}, {}, {}, {}

        import random
        
        # Stateful counters/mocks for network simulation
        global _network_sim_counter
        if '_network_sim_counter' not in globals():
            globals()['_network_sim_counter'] = 0
        globals()['_network_sim_counter'] += 1
        counter = globals()['_network_sim_counter']
        
        fb_latency = random.uniform(8.0, 15.0)
        fb_req_rate = random.uniform(10.0, 20.0)
        fb_tcp = int(random.uniform(30, 50))
        fb_drop = 0.0
        fb_errors = 0.0
        
        bp_latency = random.uniform(15.0, 25.0)
        bp_req_rate = random.uniform(5.0, 15.0)
        bp_tcp = int(random.uniform(10, 20))
        bp_drop = 0.0
        bp_errors = 0.0
        
        if counter % 3 == 0:
            # Latency spike alert: Backend -> Postgres latency goes to 1200ms
            bp_latency = random.uniform(1150.0, 1250.0)
        elif counter % 4 == 0:
            # Packet Loss / Congestion alert: Frontend -> Backend packet drop rate goes to 7.5%
            fb_drop = random.uniform(6.0, 9.0)
        elif counter % 5 == 0:
            # Traffic spike alert: Frontend -> Backend request rate goes to 250
            fb_req_rate = random.uniform(220.0, 270.0)
        elif counter % 6 == 0:
            # Connection Failure alert: Backend -> Postgres errors go to 10
            bp_errors = random.uniform(8.0, 12.0)
            
        fb_rx_real = 0.0
        fb_tx_real = 0.0
        for pod, val in pod_rx_bytes.items():
            if 'frontend' in pod:
                fb_rx_real = val
        for pod, val in pod_tx_bytes.items():
            if 'frontend' in pod:
                fb_tx_real = val
                
        bp_rx_real = 0.0
        bp_tx_real = 0.0
        for pod, val in pod_rx_bytes.items():
            if 'backend' in pod:
                bp_rx_real = val
        for pod, val in pod_tx_bytes.items():
            if 'backend' in pod:
                bp_tx_real = val

        fb_rx = fb_rx_real if fb_rx_real > 0 else random.uniform(8000.0, 12000.0)
        fb_tx = fb_tx_real if fb_tx_real > 0 else random.uniform(4000.0, 6000.0)
        
        bp_rx = bp_rx_real if bp_rx_real > 0 else random.uniform(2000.0, 4000.0)
        bp_tx = bp_tx_real if bp_tx_real > 0 else random.uniform(1000.0, 3000.0)
        
        if counter % 5 == 0:
            fb_rx *= 15.0
            fb_tx *= 15.0
            
        res_list = [
            {
                "source_service": "frontend",
                "target_service": "backend",
                "latency_ms": fb_latency,
                "receive_bytes_sec": fb_rx,
                "transmit_bytes_sec": fb_tx,
                "receive_errors": fb_errors,
                "transmit_errors": 0.0,
                "packet_loss_rate": fb_drop,
                "tcp_connections": fb_tcp,
                "http_request_rate": fb_req_rate
            },
            {
                "source_service": "backend",
                "target_service": "postgres",
                "latency_ms": bp_latency,
                "receive_bytes_sec": bp_rx,
                "transmit_bytes_sec": bp_tx,
                "receive_errors": bp_errors,
                "transmit_errors": 0.0,
                "packet_loss_rate": bp_drop,
                "tcp_connections": bp_tcp,
                "http_request_rate": bp_req_rate
            }
        ]

        # Apply Network / Pod Crash Chaos overrides
        from agents.chaos_engine import active_event
        from datetime import datetime

        if active_event and active_event["event_type"] == "network":
            target = active_event["target_service"]
            elapsed = (datetime.utcnow() - active_event["start_time"]).total_seconds()
            if elapsed < 30:
                latency = 20.0
                pkt_drop = 0.5
            elif elapsed < 60:
                latency = 40.0
                pkt_drop = 1.0
            elif elapsed < 90:
                latency = 80.0
                pkt_drop = 2.0
            elif elapsed < 120:
                latency = 150.0
                pkt_drop = 3.5
            else:
                latency = 300.0
                pkt_drop = 5.5
                
            for link in res_list:
                src = link["source_service"]
                tgt = link["target_service"]
                if target == src or target == tgt or (target == "database" and tgt == "postgres"):
                    link["latency_ms"] = latency
                    link["packet_loss_rate"] = pkt_drop
                    link["http_request_rate"] = 150.0 + (elapsed * 0.5)
                    
        elif active_event and active_event["event_type"] == "pod_crash":
            target = active_event["target_service"]
            for link in res_list:
                src = link["source_service"]
                tgt = link["target_service"]
                if target == src or target == tgt or (target == "database" and tgt == "postgres"):
                    link["latency_ms"] = 0.0
                    link["receive_bytes_sec"] = 0.0
                    link["transmit_bytes_sec"] = 0.0
                    link["receive_errors"] = 1.0
                    link["packet_loss_rate"] = 100.0
                    link["tcp_connections"] = 0
                    link["http_request_rate"] = 0.0
                    
        return res_list
