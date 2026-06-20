from fastapi import APIRouter, Depends
from services.prometheus_service import PrometheusService

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

# Service instantiation helper
def get_prometheus_service():
    return PrometheusService()

@router.get("/cpu")
async def get_cpu(service: PrometheusService = Depends(get_prometheus_service)):
    return await service.get_cpu_metrics()

@router.get("/memory")
async def get_memory(service: PrometheusService = Depends(get_prometheus_service)):
    return await service.get_memory_metrics()

@router.get("/storage")
async def get_storage(service: PrometheusService = Depends(get_prometheus_service)):
    return await service.get_storage_metrics()

@router.get("/pvc")
async def get_pvc(service: PrometheusService = Depends(get_prometheus_service)):
    return await service.get_pvc_metrics()

@router.get("/summary")
async def get_summary(service: PrometheusService = Depends(get_prometheus_service)):
    return await service.get_summary_metrics()
