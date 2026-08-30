import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    APP_NAME: str = os.getenv(
        "APP_NAME",
        "Acoustic Localization Server",
    )

    HOST: str = os.getenv(
        "HOST",
        "0.0.0.0",
    )

    PORT: int = int(
        os.getenv(
            "PORT",
            "8000",
        )
    )

    SAMPLE_RATE: int = int(
        os.getenv(
            "SAMPLE_RATE",
            "48000",
        )
    )

    CHIRP_START_FREQUENCY: int = int(
        os.getenv(
            "CHIRP_START_FREQUENCY",
            "15000",
        )
    )

    CHIRP_END_FREQUENCY: int = int(
        os.getenv(
            "CHIRP_END_FREQUENCY",
            "20000",
        )
    )

    CHIRP_DURATION: float = float(
        os.getenv(
            "CHIRP_DURATION",
            "1.0",
        )
    )


settings = Settings()