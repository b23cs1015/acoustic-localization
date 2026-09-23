from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .api.dataset_routes import router as dataset_router
from .api.experiment_routes import router as experiment_router

from .config import settings

from .storage import initialize_database

from .dataset.storage import (
    initialize_dataset_database,
)

from .dataset.experiments import (
    initialize_experiment_database,
)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

initialize_database()

initialize_dataset_database()

initialize_experiment_database()


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Acoustic Localization API",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTES
# ============================================================

app.include_router(router)

app.include_router(dataset_router)

app.include_router(experiment_router)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():
    return {
        "message": "Acoustic Localization Server is running."
    }