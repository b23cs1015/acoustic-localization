from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..dataset.experiments import (
    list_experiments,
    create_experiment,
    get_experiment,
    get_experiment_stats,
    list_experiment_positions,
    create_experiment_position,
)


router = APIRouter(
    prefix="/api/experiments",
    tags=["Experiments"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class ExperimentCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class PositionCreateRequest(BaseModel):
    name: str


# ============================================================
# EXPERIMENT ROUTES
# ============================================================

@router.get("")
def get_experiments():
    """
    Return all experiments.
    """
    return list_experiments()


@router.get("/{experiment_id}")
def get_single_experiment(experiment_id: int):
    """
    Return one experiment by ID.
    """
    experiment = get_experiment(experiment_id)

    if experiment is None:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment {experiment_id} not found.",
        )

    return experiment


@router.post("")
def add_experiment(request: ExperimentCreateRequest):
    """
    Create a new experiment.
    """
    return create_experiment(
        name=request.name,
        description=request.description,
    )


@router.get("/{experiment_id}/stats")
def get_stats(experiment_id: int):
    """
    Return statistics for one experiment.
    """
    experiment = get_experiment(experiment_id)

    if experiment is None:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment {experiment_id} not found.",
        )

    return get_experiment_stats(experiment_id)


@router.get("/{experiment_id}/positions")
def get_positions(experiment_id: int):
    """
    Return positions belonging to one experiment.
    """
    experiment = get_experiment(experiment_id)

    if experiment is None:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment {experiment_id} not found.",
        )

    return list_experiment_positions(experiment_id)


@router.post("/{experiment_id}/positions")
def add_position(
    experiment_id: int,
    request: PositionCreateRequest,
):
    """
    Create a position inside an experiment.
    """
    experiment = get_experiment(experiment_id)

    if experiment is None:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment {experiment_id} not found.",
        )

    return create_experiment_position(
        experiment_id=experiment_id,
        name=request.name,
    )