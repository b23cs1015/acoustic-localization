from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .api.dataset_routes import router as dataset_router

from .config import settings
from .storage import initialize_database


# =========================================================
# EXISTING DATABASE
# =========================================================

initialize_database()


# =========================================================
# APPLICATION
# =========================================================

app = FastAPI(
    title=settings.APP_NAME,
    version="0.2.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# =========================================================
# EXISTING API
# =========================================================

app.include_router(
    router
)


# =========================================================
# DATASET API
# =========================================================

app.include_router(
    dataset_router
)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
async def root():

    return {
        "message": (
            "Acoustic Localization "
            "Server is running."
        )
    }