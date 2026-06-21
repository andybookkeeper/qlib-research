"""Model training API endpoints."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from src.qlib_research.app.api.dependencies import get_training_runtime_service
from src.qlib_research.app.api.schemas.ml import ModelConfigSchema, TrainingRequest
from src.qlib_research.app.services.training_runtime_service import TrainingRuntimeService

router = APIRouter()


@router.post("/train")
async def train_model(
    request: TrainingRequest,
    runtime: TrainingRuntimeService = Depends(get_training_runtime_service),
) -> Dict[str, Any]:
    """Train model and persist run metadata/artifacts."""
    return runtime.train(request)


@router.get("/models")
async def list_models(
    runtime: TrainingRuntimeService = Depends(get_training_runtime_service),
) -> Dict[str, Any]:
    """List trained models."""
    return runtime.list_models()


@router.get("/models/{model_id}")
async def get_model(
    model_id: str,
    runtime: TrainingRuntimeService = Depends(get_training_runtime_service),
) -> Dict[str, Any]:
    """Get model details by model id."""
    model = runtime.get_model(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    return model


@router.post("/run-config")
async def run_config_workflow(
    workflow_config: Dict[str, Any],
    runtime: TrainingRuntimeService = Depends(get_training_runtime_service),
) -> Dict[str, Any]:
    """Run optional config-driven workflow without replacing existing training endpoints."""
    return runtime.run_config_workflow(workflow_config)


@router.get("/config/defaults")
async def get_default_config() -> ModelConfigSchema:
    """Get default model configuration."""
    return ModelConfigSchema()
