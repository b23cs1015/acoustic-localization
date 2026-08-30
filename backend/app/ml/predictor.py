from typing import Dict, Optional

from .model import AcousticModel


class Predictor:

    def __init__(
        self,
        model_path: Optional[str] = None,
    ) -> None:

        self.model = AcousticModel(
            model_path=model_path
        )

        # Load existing user feedback
        # when the server starts.
        self.refresh_learning()

    def predict(
        self,
        features: Dict[str, float],
    ) -> tuple[str, Optional[float]]:

        return self.model.predict(
            features
        )

    def refresh_learning(self) -> None:

        self.model.refresh_learning()