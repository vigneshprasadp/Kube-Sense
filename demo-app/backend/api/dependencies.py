from fastapi import APIRouter
from agents import dependency_mapper

router = APIRouter(prefix="/api/dependencies", tags=["dependencies"])

@router.get("")
def get_dependencies():
    return dependency_mapper.latest_topology
