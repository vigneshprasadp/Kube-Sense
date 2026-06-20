import asyncio
import os
import sys
import networkx as nx
from kubernetes import client, config

# Ensure paths resolve properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.prometheus_service import PrometheusService

# Global cache for the discovered dependency topology
latest_topology = {
    "nodes": [],
    "edges": [],
    "adjacency": {}
}

async def run_dependency_mapper():
    print("Dependency Mapper Agent started successfully.")
    
    # Load Kubernetes Configuration
    try:
        config.load_incluster_config()
        print("[DependencyMapper] Loaded in-cluster Kubernetes config.")
    except Exception:
        try:
            config.load_kube_config()
            print("[DependencyMapper] Fallback: Loaded local kubeconfig.")
        except Exception as e:
            print(f"[DependencyMapper] CRITICAL - Failed to load Kubernetes configuration: {e}")
            # Keep running in dummy mode if k8s is unreachable to avoid crashing backend
            await run_dummy_mapper_loop()
            return

    v1 = client.CoreV1Api()
    prometheus_service = PrometheusService()
    
    while True:
        try:
            # 1. Fetch Services & Pods
            services = v1.list_namespaced_service(namespace="tasksphere-app")
            pods = v1.list_namespaced_pod(namespace="tasksphere-app")
            
            # Build nodes list
            nodes_map = {}
            for svc in services.items:
                svc_name = svc.metadata.name
                # Normalize name for output (e.g. database, backend, frontend)
                short_name = svc_name.replace("-service", "")
                if short_name == "postgres":
                    short_name = "database"
                    
                nodes_map[short_name] = {
                    "id": short_name,
                    "type": "service",
                    "full_name": svc_name,
                    "status": "active",
                    "pods": 0
                }
                
            # Count running pods per service mapping
            for pod in pods.items:
                pod_name = pod.metadata.name
                pod_phase = pod.status.phase
                labels = pod.metadata.labels or {}
                
                # Check selector matches
                for short_name, info in nodes_map.items():
                    svc_full = info["full_name"]
                    # Usually, minikube standard selectors matches app=postgres or app=backend
                    app_label = labels.get("app", "")
                    if app_label and app_label in svc_full:
                        if pod_phase == "Running":
                            nodes_map[short_name]["pods"] += 1
            
            # Ensure standard nodes exist
            for key in ["frontend", "backend", "database"]:
                if key not in nodes_map:
                    nodes_map[key] = {
                        "id": key,
                        "type": "service",
                        "full_name": f"{key}-service" if key != "database" else "postgres-service",
                        "status": "simulated",
                        "pods": 1
                    }

            # 2. Build edges using NetworkX
            G = nx.DiGraph()
            for n in nodes_map:
                G.add_node(n)
                
            # Inspect environment variables for static configuration references
            for pod in pods.items:
                pod_name = pod.metadata.name
                # Deduce source pod type
                source_service = None
                if "frontend" in pod_name:
                    source_service = "frontend"
                elif "backend" in pod_name:
                    source_service = "backend"
                elif "postgres" in pod_name:
                    source_service = "database"
                    
                if not source_service:
                    continue
                    
                # Look at container environment variables
                for container in pod.spec.containers:
                    env_list = container.env or []
                    for env in env_list:
                        val = str(env.value or "")
                        # Check if it references postgres/database or backend
                        if "postgres-service" in val or "postgres" in val:
                            G.add_edge(source_service, "database")
                        if "backend-service" in val or "backend" in val:
                            G.add_edge(source_service, "backend")

            # Fallback/Merge with Prometheus traffic links
            try:
                traffic = await prometheus_service.get_network_metrics()
                for link in traffic:
                    src = link["source_service"]
                    tgt = link["target_service"]
                    if tgt == "postgres":
                        tgt = "database"
                    if src in nodes_map and tgt in nodes_map:
                        G.add_edge(src, tgt)
            except Exception as e:
                print(f"[DependencyMapper] Error reading prometheus network traffic metrics: {e}")

            # Heuristic standard fallback to keep visual consistency
            if not G.has_edge("frontend", "backend"):
                G.add_edge("frontend", "backend")
            if not G.has_edge("backend", "database"):
                G.add_edge("backend", "database")

            # 3. Serialize Topology
            nodes_list = list(nodes_map.values())
            edges_list = []
            for u, v in G.edges():
                edges_list.append({
                    "source": u,
                    "target": v
                })
                
            adjacency = {}
            for n in G.nodes():
                adjacency[n] = list(G.successors(n))

            global latest_topology
            latest_topology = {
                "nodes": nodes_list,
                "edges": edges_list,
                "adjacency": adjacency
            }
            
        except Exception as e:
            print(f"[DependencyMapper] Error in discovery loop: {e}")
            
        # Refresh every 30 seconds
        await asyncio.sleep(30)


async def run_dummy_mapper_loop():
    print("[DependencyMapper] Starting in dummy/fallback topology mode.")
    global latest_topology
    while True:
        # Standard fallback layout frontend -> backend -> database
        latest_topology = {
            "nodes": [
                {"id": "frontend", "type": "service", "full_name": "frontend-service", "status": "active", "pods": 1},
                {"id": "backend", "type": "service", "full_name": "backend-service", "status": "active", "pods": 1},
                {"id": "database", "type": "service", "full_name": "postgres-service", "status": "active", "pods": 1}
            ],
            "edges": [
                {"source": "frontend", "target": "backend"},
                {"source": "backend", "target": "database"}
            ],
            "adjacency": {
                "frontend": ["backend"],
                "backend": ["database"],
                "database": []
            }
        }
        await asyncio.sleep(30)
