import {
  useEffect,
  useMemo,
  useState
} from "react";

import {
  getAllAnalytics,
  getMeasurements
} from "../lib/api";

import type {
  Measurement
} from "../types";


/* =======================================================
   TYPES
======================================================= */

interface ResearchDashboardProps {
  refreshKey?: number;
}


interface AnalyticsData {
  summary: Record<string, unknown>;
  features: Record<string, unknown>;
  position: Record<string, unknown>;
  distance: Record<string, unknown>;
  object: Record<string, unknown>;
  pca: Record<string, unknown>;
}


/* =======================================================
   HELPERS
======================================================= */

function numberValue(
  value: unknown
): number | null {

  if (
    typeof value === "number" &&
    Number.isFinite(value)
  ) {
    return value;
  }

  if (
    typeof value === "string"
  ) {

    const parsed = Number(value);

    if (
      Number.isFinite(parsed)
    ) {
      return parsed;
    }
  }

  return null;
}


function formatNumber(
  value: unknown,
  decimals = 2
): string {

  const number = numberValue(value);

  if (number === null) {
    return "—";
  }

  return number.toFixed(decimals);
}


function formatPercentage(
  value: unknown
): string {

  const number = numberValue(value);

  if (number === null) {
    return "—";
  }

  const percentage =
    number <= 1
      ? number * 100
      : number;

  return `${percentage.toFixed(1)}%`;
}


function findArray(
  data: Record<string, unknown>
): unknown[] {

  const possibleKeys = [
    "data",
    "items",
    "results",
    "positions",
    "features",
    "points",
    "distances",
    "objects"
  ];

  for (const key of possibleKeys) {

    const value = data[key];

    if (Array.isArray(value)) {
      return value;
    }
  }

  return [];
}


function objectLabel(
  value: unknown
): string {

  if (
    typeof value === "string"
  ) {
    return value;
  }

  if (
    typeof value === "number"
  ) {
    return String(value);
  }

  if (
    value &&
    typeof value === "object"
  ) {

    const object =
      value as Record<string, unknown>;

    const possibleKeys = [
      "name",
      "label",
      "position",
      "position_name",
      "object",
      "condition"
    ];

    for (const key of possibleKeys) {

      if (
        object[key] !== undefined &&
        object[key] !== null
      ) {
        return String(object[key]);
      }
    }
  }

  return "Unknown";
}


function asAnalyticsData(
  value: unknown
): AnalyticsData {

  if (
    !value ||
    typeof value !== "object"
  ) {
    return {
      summary: {},
      features: {},
      position: {},
      distance: {},
      object: {},
      pca: {}
    };
  }

  const data =
    value as Record<string, unknown>;

  return {
    summary:
      data.summary &&
      typeof data.summary === "object"
        ? data.summary as Record<string, unknown>
        : {},

    features:
      data.features &&
      typeof data.features === "object"
        ? data.features as Record<string, unknown>
        : {},

    position:
      data.position &&
      typeof data.position === "object"
        ? data.position as Record<string, unknown>
        : {},

    distance:
      data.distance &&
      typeof data.distance === "object"
        ? data.distance as Record<string, unknown>
        : {},

    object:
      data.object &&
      typeof data.object === "object"
        ? data.object as Record<string, unknown>
        : {},

    pca:
      data.pca &&
      typeof data.pca === "object"
        ? data.pca as Record<string, unknown>
        : {}
  };
}


/* =======================================================
   COMPONENT
======================================================= */

function ResearchDashboard({
  refreshKey = 0
}: ResearchDashboardProps) {

  const [
    analytics,
    setAnalytics
  ] = useState<AnalyticsData | null>(null);


  const [
    measurements,
    setMeasurements
  ] = useState<Measurement[]>([]);


  const [
    loading,
    setLoading
  ] = useState(true);


  const [
    error,
    setError
  ] = useState("");


  /* =====================================================
     LOAD DATA
  ===================================================== */

  useEffect(() => {

    let cancelled = false;


    async function loadData() {

      setLoading(true);
      setError("");


      try {

        const [
          analyticsResponse,
          measurementsResponse
        ] = await Promise.all([
          getAllAnalytics(),
          getMeasurements()
        ]);


        if (cancelled) {
          return;
        }


        setAnalytics(
          asAnalyticsData(
            analyticsResponse
          )
        );


        setMeasurements(
          measurementsResponse.measurements || []
        );

      } catch (err) {

        if (!cancelled) {

          setError(
            err instanceof Error
              ? err.message
              : "Could not load research analytics."
          );
        }

      } finally {

        if (!cancelled) {
          setLoading(false);
        }
      }
    }


    loadData();


    return () => {
      cancelled = true;
    };

  }, [refreshKey]);


  /* =====================================================
     DERIVED VALUES
  ===================================================== */

  const summary =
    analytics?.summary || {};


  const totalMeasurements =
    numberValue(
      summary.total_measurements
    ) ??
    measurements.length;


  const labeledMeasurements =
    numberValue(
      summary.labeled_measurements
    ) ??
    measurements.filter(
      measurement =>
        measurement.position_id !== null
    ).length;


  const correctPredictions =
    numberValue(
      summary.correct_predictions
    ) ??
    measurements.filter(
      measurement =>
        measurement.feedback_correct === true
    ).length;


  const incorrectPredictions =
    numberValue(
      summary.incorrect_predictions
    ) ??
    measurements.filter(
      measurement =>
        measurement.feedback_correct === false
    ).length;


  const accuracy =
    numberValue(
      summary.accuracy
    );


  const averageConfidence =
    numberValue(
      summary.average_confidence
    );


  /* =====================================================
     ANALYTICS ARRAYS
  ===================================================== */

  const positionData =
    analytics
      ? findArray(analytics.position)
      : [];


  const distanceData =
    analytics
      ? findArray(analytics.distance)
      : [];


  const objectData =
    analytics
      ? findArray(analytics.object)
      : [];


  const pcaData =
    analytics
      ? findArray(analytics.pca)
      : [];


  const featureData =
    analytics
      ? findArray(analytics.features)
      : [];


  /* =====================================================
     POSITION MAX
  ===================================================== */

  const positionMaxCount =
    useMemo(() => {

      return Math.max(
        ...positionData.map(item => {

          if (
            !item ||
            typeof item !== "object"
          ) {
            return 0;
          }

          const object =
            item as Record<string, unknown>;

          return (
            numberValue(
              object.count ??
              object.measurements ??
              object.value ??
              object.total
            ) ?? 0
          );
        }),
        1
      );

    }, [positionData]);


  /* =====================================================
     RENDER
  ===================================================== */

  return (

    <section className="research-dashboard">

      {/* =================================================
          HEADER
      ================================================= */}

      <div className="research-header">

        <div>

          <div className="research-eyebrow">
            RESEARCH ANALYTICS
          </div>

          <h2>
            Acoustic Fingerprint
            <br />
            Analysis
          </h2>

          <p>
            Central-server analysis of recorded
            acoustic measurements, extracted
            features, positional labels, recording
            conditions, and model behaviour.
          </p>

        </div>


        <div className="research-status">

          <span
            className={
              loading
                ? "research-status-dot loading"
                : "research-status-dot"
            }
          />

          {loading
            ? "Updating"
            : "Analytics ready"}

        </div>

      </div>


      {/* =================================================
          ERROR
      ================================================= */}

      {error && (

        <div className="research-error">

          <strong>
            Analytics unavailable
          </strong>

          <p>
            {error}
          </p>

        </div>

      )}


      {/* =================================================
          OVERVIEW
      ================================================= */}

      <div className="research-section">

        <div className="research-section-heading">

          <span>01</span>

          <h3>
            Dataset Overview
          </h3>

        </div>


        <div className="research-stat-grid">

          <div className="research-stat">

            <span>
              Measurements
            </span>

            <strong>
              {totalMeasurements}
            </strong>

            <small>
              recorded samples
            </small>

          </div>


          <div className="research-stat">

            <span>
              Labeled
            </span>

            <strong>
              {labeledMeasurements}
            </strong>

            <small>
              with known position
            </small>

          </div>


          <div className="research-stat">

            <span>
              Correct
            </span>

            <strong>
              {correctPredictions}
            </strong>

            <small>
              confirmed predictions
            </small>

          </div>


          <div className="research-stat">

            <span>
              Incorrect
            </span>

            <strong>
              {incorrectPredictions}
            </strong>

            <small>
              corrected predictions
            </small>

          </div>


          <div className="research-stat">

            <span>
              Accuracy
            </span>

            <strong>
              {formatPercentage(accuracy)}
            </strong>

            <small>
              feedback-based
            </small>

          </div>


          <div className="research-stat">

            <span>
              Confidence
            </span>

            <strong>
              {formatPercentage(
                averageConfidence
              )}
            </strong>

            <small>
              average prediction confidence
            </small>

          </div>

        </div>

      </div>


      {/* =================================================
          MODEL FEEDBACK
      ================================================= */}

      <div className="research-section">

        <div className="research-section-heading">

          <span>02</span>

          <h3>
            Prediction Behaviour
          </h3>

        </div>


        <div className="research-panel">

          <div className="research-panel-header">

            <div>

              <strong>
                Model feedback
              </strong>

              <p>
                Comparison between the predicted
                position and the user-confirmed
                position.
              </p>

            </div>

          </div>


          <div className="prediction-bars">

            <div className="prediction-bar-row">

              <div className="prediction-bar-label">

                <span>
                  Correct
                </span>

                <strong>
                  {correctPredictions}
                </strong>

              </div>


              <div className="prediction-bar-track">

                <div
                  className="prediction-bar correct"
                  style={{
                    width:
                      `${
                        totalMeasurements > 0
                          ? Math.min(
                              100,
                              (
                                correctPredictions /
                                totalMeasurements
                              ) * 100
                            )
                          : 0
                      }%`
                  }}
                />

              </div>

            </div>


            <div className="prediction-bar-row">

              <div className="prediction-bar-label">

                <span>
                  Incorrect
                </span>

                <strong>
                  {incorrectPredictions}
                </strong>

              </div>


              <div className="prediction-bar-track">

                <div
                  className="prediction-bar incorrect"
                  style={{
                    width:
                      `${
                        totalMeasurements > 0
                          ? Math.min(
                              100,
                              (
                                incorrectPredictions /
                                totalMeasurements
                              ) * 100
                            )
                          : 0
                      }%`
                  }}
                />

              </div>

            </div>

          </div>

        </div>

      </div>


      {/* =================================================
          POSITION ANALYSIS
      ================================================= */}

      <div className="research-section">

        <div className="research-section-heading">

          <span>03</span>

          <h3>
            Position Analysis
          </h3>

        </div>


        <div className="research-panel">

          <div className="research-panel-header">

            <div>

              <strong>
                Position distribution
              </strong>

              <p>
                Measurements grouped according to
                the recorded position labels.
              </p>

            </div>

          </div>


          {positionData.length === 0 ? (

            <div className="research-empty">

              Position analytics will appear after
              measurements contain position information.

            </div>

          ) : (

            <div className="research-bars">

              {positionData
                .slice(0, 20)
                .map((item, index) => {

                  if (
                    !item ||
                    typeof item !== "object"
                  ) {
                    return null;
                  }


                  const object =
                    item as Record<string, unknown>;


                  const label =
                    objectLabel(object);


                  const count =
                    numberValue(
                      object.count ??
                      object.measurements ??
                      object.value ??
                      object.total
                    ) ?? 0;


                  return (

                    <div
                      className="research-bar-row"
                      key={index}
                    >

                      <div className="research-bar-meta">

                        <span>
                          {label}
                        </span>

                        <strong>
                          {count}
                        </strong>

                      </div>


                      <div className="research-bar-track">

                        <div
                          className="research-bar-fill"
                          style={{
                            width:
                              `${
                                (
                                  count /
                                  positionMaxCount
                                ) * 100
                              }%`
                          }}
                        />

                      </div>

                    </div>

                  );

                })}

            </div>

          )}

        </div>

      </div>


      {/* =================================================
          DISTANCE
      ================================================= */}

      <div className="research-section">

        <div className="research-section-heading">

          <span>04</span>

          <h3>
            Distance Effects
          </h3>

        </div>


        <div className="research-panel">

          <div className="research-panel-header">

            <div>

              <strong>
                Recording distance
              </strong>

              <p>
                Relationship between measurement
                distance and acoustic observations.
              </p>

            </div>

          </div>


          {distanceData.length === 0 ? (

            <div className="research-empty">

              Distance analysis will appear when
              recordings contain distance metadata.

            </div>

          ) : (

            <div className="research-table">

              <div className="research-table-head">

                <span>Distance</span>

                <span>Measurements</span>

                <span>Confidence</span>

              </div>


              {distanceData
                .slice(0, 15)
                .map((item, index) => {

                  if (
                    !item ||
                    typeof item !== "object"
                  ) {
                    return null;
                  }


                  const object =
                    item as Record<string, unknown>;


                  return (

                    <div
                      className="research-table-row"
                      key={index}
                    >

                      <span>

                        {
                          formatNumber(
                            object.distance_cm ??
                            object.distance,
                            1
                          )
                        }

                        {" cm"}

                      </span>


                      <span>
                        {String(
                            object.count ??
                            object.measurements ??
                            object.value ??
                            "—"
                        )}
                        </span>


                      <span>

                        {
                          formatPercentage(
                            object.confidence
                          )
                        }

                      </span>

                    </div>

                  );

                })}

            </div>

          )}

        </div>

      </div>


      {/* =================================================
          ENVIRONMENT
      ================================================= */}

      <div className="research-section">

        <div className="research-section-heading">

          <span>05</span>

          <h3>
            Environmental Conditions
          </h3>

        </div>


        <div className="research-panel">

          <div className="research-panel-header">

            <div>

              <strong>
                Object-between analysis
              </strong>

              <p>
                Comparison of recordings captured
                with different objects or obstructions
                between transmitter and receiver.
              </p>

            </div>

          </div>


          {objectData.length === 0 ? (

            <div className="research-empty">

              Condition analysis will appear when
              recordings contain object metadata.

            </div>

          ) : (

            <div className="research-condition-grid">

              {objectData
                .slice(0, 12)
                .map((item, index) => {

                  if (
                    !item ||
                    typeof item !== "object"
                  ) {
                    return null;
                  }


                  const object =
                    item as Record<string, unknown>;


                  const label =
                    objectLabel(object);


                  const count =
                    numberValue(
                      object.count ??
                      object.measurements ??
                      object.value
                    ) ?? 0;


                  return (

                    <div
                      className="research-condition"
                      key={index}
                    >

                      <span>
                        Condition
                      </span>

                      <strong>
                        {label}
                      </strong>


                      <div>

                        <span>
                          Samples
                        </span>

                        <b>
                          {count}
                        </b>

                      </div>


                      <div>

                        <span>
                          Confidence
                        </span>

                        <b>
                          {formatPercentage(
                            object.confidence
                          )}
                        </b>

                      </div>

                    </div>

                  );

                })}

            </div>

          )}

        </div>

      </div>


      {/* =================================================
          ACOUSTIC FEATURES
      ================================================= */}

      <div className="research-section">

        <div className="research-section-heading">

          <span>06</span>

          <h3>
            Acoustic Features
          </h3>

        </div>


        <div className="research-panel">

          <div className="research-panel-header">

            <div>

              <strong>
                Extracted acoustic fingerprint
              </strong>

              <p>
                Numerical features used by the
                localization model to represent
                the recorded acoustic response.
              </p>

            </div>

          </div>


          {featureData.length === 0 ? (

            measurements.length === 0 ? (

              <div className="research-empty">

                Acoustic feature analysis will
                appear after measurements are
                recorded.

              </div>

            ) : (

              <div className="research-feature-fallback">

                {Object.entries(
                  measurements[0].features || {}
                )
                  .slice(0, 24)
                  .map(([name, value]) => (

                    <div
                      className="research-feature"
                      key={name}
                    >

                      <span>
                        {name}
                      </span>

                      <strong>
                        {formatNumber(
                          value,
                          4
                        )}
                      </strong>

                    </div>

                  ))}

              </div>

            )

          ) : (

            <div className="research-feature-fallback">

              {featureData
                .slice(0, 24)
                .map((item, index) => {

                  if (
                    !item ||
                    typeof item !== "object"
                  ) {
                    return null;
                  }


                  const object =
                    item as Record<string, unknown>;


                  const name =
                    objectLabel(object);


                  const value =
                    object.mean ??
                    object.average ??
                    object.value ??
                    object.std ??
                    object.max;


                  return (

                    <div
                      className="research-feature"
                      key={index}
                    >

                      <span>
                        {name}
                      </span>

                      <strong>
                        {formatNumber(
                          value,
                          4
                        )}
                      </strong>

                    </div>

                  );

                })}

            </div>

          )}

        </div>

      </div>


      {/* =================================================
          PCA
      ================================================= */}

      <div className="research-section">

        <div className="research-section-heading">

          <span>07</span>

          <h3>
            Feature-Space Separation
          </h3>

        </div>


        <div className="research-panel">

          <div className="research-panel-header">

            <div>

              <strong>
                PCA projection
              </strong>

              <p>
                A lower-dimensional view of the
                acoustic feature space. Clustering
                can indicate whether recordings from
                different locations produce distinct
                acoustic fingerprints.
              </p>

            </div>

          </div>


          {pcaData.length === 0 ? (

            <div className="research-empty">

              PCA visualization will appear once
              sufficient labeled training data is
              available.

            </div>

          ) : (

            <div className="pca-chart">

              {pcaData
                .slice(0, 250)
                .map((item, index) => {

                  if (
                    !item ||
                    typeof item !== "object"
                  ) {
                    return null;
                  }


                  const object =
                    item as Record<string, unknown>;


                  const x =
                    numberValue(
                      object.x ??
                      object.pc1 ??
                      object.PC1
                    ) ?? 0;


                  const y =
                    numberValue(
                      object.y ??
                      object.pc2 ??
                      object.PC2
                    ) ?? 0;


                  const label =
                    objectLabel(object);


                  const boundedX =
                    Math.max(
                      -3,
                      Math.min(3, x)
                    );


                  const boundedY =
                    Math.max(
                      -3,
                      Math.min(3, y)
                    );


                  const xPosition =
                    50 +
                    (boundedX / 3) * 42;


                  const yPosition =
                    50 -
                    (boundedY / 3) * 42;


                  return (

                    <div
                      className="pca-point"
                      key={index}
                      title={
                        `${label} · ` +
                        `PC1 ${x.toFixed(2)} · ` +
                        `PC2 ${y.toFixed(2)}`
                      }
                      style={{
                        left:
                          `${xPosition}%`,
                        top:
                          `${yPosition}%`
                      }}
                    />

                  );

                })}


              <div className="pca-axis-label pca-axis-x">
                PC1
              </div>

              <div className="pca-axis-label pca-axis-y">
                PC2
              </div>

            </div>

          )}

        </div>

      </div>


      {/* =================================================
          INTERPRETATION
      ================================================= */}

      <div className="research-section">

        <div className="research-section-heading">

          <span>08</span>

          <h3>
            Research Interpretation
          </h3>

        </div>


        <div className="research-interpretation">

          <div>

            <span>
              What this dashboard measures
            </span>

            <p>
              Whether the acoustic response contains
              measurable information that can be
              associated with different recording
              positions and environmental conditions.
            </p>

          </div>


          <div>

            <span>
              What the fingerprint represents
            </span>

            <p>
              The fingerprint is the combination of
              extracted acoustic features describing
              the recorded response rather than a
              direct visual representation of the
              physical room.
            </p>

          </div>


          <div>

            <span>
              Important dataset limitation
            </span>

            <p>
              The original Task 1 experiments were
              exploratory experiments used to determine
              whether acoustic differences between
              positions and conditions could be detected.
              They should not automatically be treated
              as the final training dataset.
            </p>

          </div>


          <div>

            <span>
              Current research direction
            </span>

            <p>
              Future controlled recordings can be
              collected specifically for model training,
              while this dashboard provides the central
              server interface for inspecting recordings,
              acoustic features, labels, conditions,
              predictions, and model behaviour.
            </p>

          </div>

        </div>

      </div>

    </section>
  );
}


export default ResearchDashboard;