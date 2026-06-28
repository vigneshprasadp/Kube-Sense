import os
import json
import httpx
import traceback
from sqlalchemy.orm import Session
from models.rca import DBRootCauseReport
from models.recommendation import DBRecommendation

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.minikube.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")

def get_rule_based_fallback(root_cause: str, affected_services: str):
    """
    SRE-curated fallback rules in case Ollama is offline or fails to generate a response.
    """
    root_cause_lower = root_cause.lower()
    affected_services = affected_services or "None"
    
    if "storage" in root_cause_lower or "pvc" in root_cause_lower:
        explanation = (
            f"The incident is caused by storage saturation or volume exhaustion in the database namespace. "
            f"This prevents write-ahead logging (WAL) and state persistence, causing database transaction failures "
            f"to cascade and degrade downstream services like {affected_services}."
        )
        recommended_fixes = [
            "Increase the Persistent Volume Claim (PVC) size by editing the volume definition.",
            "Restart the database deployment to release locked system descriptors.",
            "Scale backend deployment down temporarily to control traffic incoming queues."
        ]
        preventive_measures = [
            "Enable Storage Forecast Alerts utilizing the scikit-learn forecasting model.",
            "Configure automatic storage expansion (autogrow) in the storage class."
        ]
    elif "cpu" in root_cause_lower:
        explanation = (
            f"High CPU utilization on the core services causes thread starvation and request processing delays. "
            f"Since downstream callers wait for HTTP responses, cascading latency propagates through the network, "
            f"degrading performance across {affected_services}."
        )
        recommended_fixes = [
            "Check pod CPU resource limits and current throttling logs.",
            "Scale deployment replicas to distribute transaction load.",
            "Profile the application runtime thread dump to identify resource locks."
        ]
        preventive_measures = [
            "Establish Horizontal Pod Autoscaler (HPA) using CPU target metrics.",
            "Define explicit container resource requests and limits in deployment manifests."
        ]
    elif "crash" in root_cause_lower or "unavailable" in root_cause_lower or "terminated" in root_cause_lower:
        explanation = (
            f"The incident is caused by pod termination or crash failure of the target microservice. "
            f"Since the containers are down or unreachable, the system is unable to process incoming requests, "
            f"leading to cascading connection failures and service downtime across {affected_services}."
        )
        recommended_fixes = [
            "Inspect container restart events and check logs for exit code errors (e.g. OOMKilled/Exit Code 137).",
            "Verify pod state and replication status using 'kubectl describe pod'.",
            "Check node resource pressure to ensure the host machine has enough capacity."
        ]
        preventive_measures = [
            "Configure liveness and readiness probe delays to prevent premature container restarts.",
            "Implement high-availability redundancy by increasing deployment replica counts."
        ]
    elif "network" in root_cause_lower or "latency" in root_cause_lower or "connection" in root_cause_lower:
        explanation = (
            f"Network congestion, packet drop anomalies, or connectivity failures disrupt RPC communication between pods. "
            f"This causes request timeouts and socket exhaustion, leading to failures in {affected_services}."
        )
        recommended_fixes = [
            "Inspect the Kubernetes CNI plugin logs for connection failure anomalies.",
            "Check cluster network policies for accidental blockages.",
            "Restart affected service pods to refresh connection pools and resolve socket hangs."
        ]
        preventive_measures = [
            "Configure SRE circuit breakers and retry limits on intermediate clients.",
            "Implement TCP socket keep-alive optimizations in pod configs."
        ]
    else:
        explanation = (
            f"An anomaly root-caused as '{root_cause}' has degraded cluster performance. "
            f"Telemetry analysis flags performance outliers impacting {affected_services}."
        )
        recommended_fixes = [
            "Inspect container log streams for error exception patterns.",
            "List namespace events to check for node eviction or crash loops.",
            "Verify metric levels in Prometheus dashboard."
        ]
        preventive_measures = [
            "Define alerts for telemetry outliers.",
            "Review configuration settings and limits."
        ]
        
    return explanation, recommended_fixes, preventive_measures

async def generate_recommendation(rca_report: DBRootCauseReport, db: Session) -> DBRecommendation:
    """
    Generate an SRE recommendation using Ollama (Llama 3) and save it in the database.
    If Ollama is unreachable, automatically fall back to rule-based recommendations.
    """
    print(f"[Recommendation Engine] Generating recommendation for RCA ID {rca_report.id}: '{rca_report.root_cause}'")
    
    explanation = None
    recommended_fixes = []
    preventive_measures = []
    used_llm = False
    
    prompt = f"""You are a Kubernetes Site Reliability Engineer.

Analyze the following incident.

Root Cause:
{rca_report.root_cause}

Affected Services:
{rca_report.affected_services}

Generate:
1. Explanation: A detailed natural-language explanation of this root cause and why it affects these services.
2. Recommended Fixes: A list of actionable steps to resolve the immediate incident.
3. Preventive Measures: A list of long-term recommendations to prevent recurring failures.

You must respond with a JSON object containing exactly these keys: "explanation" (string), "recommended_fixes" (list of strings), and "preventive_measures" (list of strings). Do not include any text before or after the JSON.
"""

    try:
        async with httpx.AsyncClient() as client:
            print(f"[Recommendation Engine] Requesting Ollama ({OLLAMA_URL}) using model '{OLLAMA_MODEL}'...")
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=15.0
            )
            
            if response.status_code == 200:
                result_json = response.json()
                response_text = result_json.get("response", "").strip()
                print(f"[Recommendation Engine] Ollama response: {response_text}")
                
                parsed = json.loads(response_text)
                explanation = parsed.get("explanation")
                recommended_fixes = parsed.get("recommended_fixes", [])
                preventive_measures = parsed.get("preventive_measures", [])
                
                if explanation and (recommended_fixes or preventive_measures):
                    used_llm = True
                    print("[Recommendation Engine] LLM recommendation generated successfully.")
                else:
                    print("[Recommendation Engine] Warning: Ollama response structure invalid.")
            else:
                print(f"[Recommendation Engine] Ollama API returned status code {response.status_code}.")
                
    except Exception as e:
        print(f"[Recommendation Engine] Failed to query Ollama LLM: {e}. Cascading to SRE rule-based fallback.")
        traceback.print_exc()


    if not used_llm:
        print("[Recommendation Engine] Applying rule-based fallback recommendations.")
        explanation, recommended_fixes, preventive_measures = get_rule_based_fallback(
            rca_report.root_cause, rca_report.affected_services
        )
    
    # Check if recommendation already exists
    existing_rec = db.query(DBRecommendation).filter(DBRecommendation.rca_id == rca_report.id).first()
    
    if existing_rec:
        existing_rec.root_cause = rca_report.root_cause
        existing_rec.severity = rca_report.severity
        existing_rec.affected_services = rca_report.affected_services
        existing_rec.explanation = explanation
        existing_rec.recommended_fixes = json.dumps(recommended_fixes)
        existing_rec.preventive_measures = json.dumps(preventive_measures)
        existing_rec.timestamp = rca_report.timestamp
        db.commit()
        db.refresh(existing_rec)
        print(f"[Recommendation Engine] Updated existing recommendation ID {existing_rec.id} for RCA ID {rca_report.id}.")
        return existing_rec
    else:
        new_rec = DBRecommendation(
            rca_id=rca_report.id,
            root_cause=rca_report.root_cause,
            severity=rca_report.severity,
            affected_services=rca_report.affected_services,
            explanation=explanation,
            recommended_fixes=json.dumps(recommended_fixes),
            preventive_measures=json.dumps(preventive_measures),
            timestamp=rca_report.timestamp
        )
        db.add(new_rec)
        db.commit()
        db.refresh(new_rec)
        print(f"[Recommendation Engine] Saved new recommendation ID {new_rec.id} for RCA ID {rca_report.id}.")
        return new_rec
