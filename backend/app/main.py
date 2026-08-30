from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import settings
from .storage import initialize_database


# Initialize SQLite database and ensure
# Position 1–25 exist.
initialize_database()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.2.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)


@app.get("/")
async def root():

    return {
        "message": (
            "Acoustic Localization "
            "Server is running."
        )
    }