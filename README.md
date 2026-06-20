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

### Prerequisites
*   Node.js (v18+)
*   Python (v3.10+)
*   PostgreSQL
*   Kubernetes Cluster with Prometheus deployed (optional, for live telemetry integration)

### Installation & Local Setup

#### 1. Backend Setup
1. Navigate to the backend folder:
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
4. Run the FastAPI dev server:
   ```bash
   uvicorn main:app --reload
   ```

#### 2. Frontend Setup
1. Navigate to the frontend folder:
   ```bash
   cd demo-app/frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Run the Vite development server:
   ```bash
   npm run dev
   ```
