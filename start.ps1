# ============================================================
# KubeSense Startup Script
# Run this from c:\Users\vigne\mini_proj
# Usage: .\start.ps1
# ============================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  KubeSense - Starting Up" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Start Minikube
Write-Host "[1/4] Starting Minikube..." -ForegroundColor Yellow
$minikubeStatus = minikube status 2>&1 | Select-String "Running"
if ($minikubeStatus) {
    Write-Host "      Minikube already running. Skipping." -ForegroundColor Green
} else {
    minikube start
    Write-Host "      Minikube started." -ForegroundColor Green
}

# Step 2: Verify pods are running
Write-Host ""
Write-Host "[2/4] Waiting for pods to be ready..." -ForegroundColor Yellow
kubectl wait --for=condition=ready pod --all -n tasksphere-app --timeout=120s 2>&1 | Out-Null
Write-Host "      All pods are ready." -ForegroundColor Green

# Step 3: Show pod status
Write-Host ""
Write-Host "[3/4] Cluster Status:" -ForegroundColor Yellow
kubectl get pods -n tasksphere-app

# Step 4: Open tunnels in separate windows
Write-Host ""
Write-Host "[4/4] Opening service tunnels..." -ForegroundColor Yellow

# Open frontend tunnel in a new PowerShell window (keeps it alive)
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Write-Host 'KubeSense Frontend Tunnel - Keep this window open' -ForegroundColor Cyan; minikube service frontend-service -n tasksphere-app"
)

# Small delay so frontend tunnel starts first
Start-Sleep -Seconds 3

Write-Host "      Tunnels started in background windows." -ForegroundColor Green

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  KubeSense is LIVE!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  The browser should have opened automatically." -ForegroundColor White
Write-Host "  If not, check the tunnel window for the URL." -ForegroundColor White
Write-Host ""
Write-Host "  IMPORTANT: Keep the tunnel window open!" -ForegroundColor Yellow
Write-Host "  Closing it will disconnect the app." -ForegroundColor DarkGray
Write-Host ""
