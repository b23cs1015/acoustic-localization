import type {
  PredictionResult
} from "../types";

interface Props {
  result: PredictionResult | null;
}

export default function ResultCard({
  result
}: Props) {
  if (!result) {
    return (
      <div className="result-card empty">
        <span className="result-label">
          Prediction
        </span>

        <h2>
          No measurement yet
        </h2>

        <p>
          Run a measurement to see the
          server-side ML result.
        </p>
      </div>
    );
  }

  return (
    <div className="result-card">
      <span className="result-label">
        Predicted Location
      </span>

      <h2>
        {result.prediction}
      </h2>

      {result.confidence !== null && (
        <p>
          Confidence:{" "}
          {(
            result.confidence * 100
          ).toFixed(1)}
          %
        </p>
      )}

      <div className="result-meta">
        <div>
          <span>Duration</span>
          <strong>
            {result.duration_seconds.toFixed(
              2
            )} s
          </strong>
        </div>

        <div>
          <span>Sample Rate</span>
          <strong>
            {result.sample_rate.toLocaleString()} Hz
          </strong>
        </div>
      </div>

      <div className="feature-section">
        <span className="result-label">
          Extracted Features
        </span>

        <div className="feature-grid">
          {Object.entries(
            result.features
          ).map(([name, value]) => (
            <div
              className="feature"
              key={name}
            >
              <span>{name}</span>

              <strong>
                {value.toFixed(4)}
              </strong>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}