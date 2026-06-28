# KubeSense (TaskSphere)

KubeSense is a modern, AI-powered Kubernetes observability and monitoring platform. It combines real-time cluster metrics, automated anomaly detection, predictive resource forecasting, and interactive topology maps into a single, intuitive interface. 

By analyzing live data stream telemetry directly from your Kubernetes cluster (via Prometheus), the platform helps developers and DevOps teams proactively detect issues, trace dependency chains, and determine the root cause of infrastructure anomalies before they affect users.

---

## 🚀 Key Features

*   **Real-time Cluster Telemetry**: Streams CPU, PVC storage, and network metrics from Prometheus directly to the UI using high-performance WebSockets.
*   **Predictive AI/ML Forecasting**: Background agents analyze resource consumption patterns, compute trend lines, and predict future threshold breaches (estimating down to the minute when a service might run out of CPU or storage).
*   **Automated Root Cause Analysis (RCA)**: A background RCA engine correlates CPU, storage, and network anomalies, matches them against the cluster topology, and generates detailed incident reports with confidence scores.
*   **Interactive Dependency Graphs**: Visually map and explore relationships between Kubernetes services, pods, and persistent volumes using interactive flow topology maps.
*   **Intelligent Recommendations**: Get automated, actionable suggestions for system optimizations, such as scaling recommendations or configuration adjustments to prevent issues.

---

## 🛠️ Tech Stack

### Frontend
*   **Core**: React + TypeScript + Vite
*   **Styling**: Tailwind CSS & Framer Motion (for smooth micro-animations)
*   **Data Visualization**: Recharts (metric charts) & ReactFlow (interactive service mesh graphs)
*   **State Management**: TanStack React Query & Axios

### Backend
*   **Framework**: FastAPI (Python) with WebSockets for real-time streaming
*   **Database**: PostgreSQL with SQLAlchemy ORM
*   **AI/ML & Graph Processing**: Scikit-Learn (for forecasting models) & NetworkX (for service-dependency graph calculations)
*   **Cluster Integration**: Kubernetes Client library & Prometheus Service Integrations

### Infrastructure
*   **Deployment**: Kubernetes manifests (Deployments, Services, RBAC rules, Namespaces)
*   **Monitoring**: Integrated Prometheus deployment configurations
*   **Containerization**: Dockerfiles for modular container creation

---

## 📂 Directory Structure

```text
demo-app/
├── backend/            # FastAPI backend, background AI/ML agents, and database models
├── frontend/           # React, TypeScript, Tailwind CSS UI application
└── k8s/                # Kubernetes deployment configurations, RBAC, and Prometheus manifests
```

---

## ⚙️ Getting Started

You can run KubeSense in two modes depending on your needs:
1. **Local Standalone Mode (Zero-Config)**: Runs the frontend and backend directly on your computer. Telemetry and anomalies are fully simulated, and the backend automatically falls back to a local SQLite database (`tasksphere.db`). No PostgreSQL or Kubernetes/Minikube setup is required.
2. **Kubernetes Cluster Mode (Minikube)**: Runs the application inside a Minikube cluster, querying live Kubernetes telemetry from a Prometheus deployment, and storing data in a PostgreSQL container.

---

### Option 1: Local Standalone Mode (Recommended for Quick Run)

#### Prerequisites
*   Node.js (v18+)
*   Python (v3.10+)

#### 1. Backend Setup
1. Open a terminal and navigate to the backend folder:
   ```bash
   cd demo-app/backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the FastAPI development server:
   ```bash
   uvicorn main:app --reload
   ```
   *Note: The backend will automatically create a local SQLite database file `tasksphere.db` in the backend directory. You do not need to configure any database settings.*

#### 2. Frontend Setup
1. Open a new terminal window and navigate to the frontend folder:
   ```bash
   cd demo-app/frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
4. Open your browser and navigate to the URL printed in the console (usually `http://localhost:5173`).

---

### Option 2: Kubernetes Cluster Mode

#### Prerequisites
*   Minikube
*   Kubectl
*   Docker Desktop / Hypervisor

#### Quick Start with PowerShell (Windows)
We provide a startup script to start Minikube, apply manifests, and establish tunnels automatically:
1. Run the startup script from the project root:
   ```powershell
   .\start.ps1
   ```
2. Keep the newly opened tunnel terminal windows running to maintain connection to the cluster services.

#### Manual Startup Steps (Cross-Platform)
1. Start Minikube:
   ```bash
   minikube start
   ```
2. Build and load the Docker images into Minikube's Docker daemon registry:
   ```bash
   # Point shell to minikube docker daemon
   eval $(minikube docker-env) # On macOS/Linux
   # or: minikube docker-env | Invoke-Expression # On Windows

   # Build Backend
   docker build -t tasksphere-backend:latest demo-app/backend/

   # Build Frontend
   docker build -t tasksphere-frontend:latest demo-app/frontend/
   ```
3. Apply the Kubernetes manifests:
   ```bash
   kubectl apply -f demo-app/k8s/namespace.yaml
   kubectl apply -f demo-app/k8s/rbac.yaml
   kubectl apply -f demo-app/k8s/prometheus.yaml
   kubectl apply -f demo-app/k8s/deployment.yaml
   kubectl apply -f demo-app/k8s/service.yaml
   ```
4. Expose the services using Minikube tunnel:
   ```bash
   minikube service frontend-service -n tasksphere-app
   ```
