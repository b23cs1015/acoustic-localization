import {
  useEffect,
  useState
} from "react";

import {
  createPosition,
  discardMeasurement,
  getMeasurementAudioUrl,
  getMeasurements,
  getPositions,
  saveFeedback,
  updateMeasurement
} from "../lib/api";

import type {
  Measurement,
  Position
} from "../types";


interface Props {

  refreshKey: number;
}


export default function MeasurementHistory({
  refreshKey
}: Props) {

  const [
    measurements,
    setMeasurements
  ] = useState<Measurement[]>([]);

  const [
    positions,
    setPositions
  ] = useState<Position[]>([]);

  const [
    loading,
    setLoading
  ] = useState(true);

  const [
    error,
    setError
  ] = useState("");

  const [
    editingId,
    setEditingId
  ] = useState<number | null>(null);

  const [
    selectedPosition,
    setSelectedPosition
  ] = useState<number | null>(null);

  const [
    objectBetween,
    setObjectBetween
  ] = useState("");

  const [
    distance,
    setDistance
  ] = useState("");

  const [
    notes,
    setNotes
  ] = useState("");

  const [
    feedbackCorrect,
    setFeedbackCorrect
  ] = useState<boolean | null>(null);

  const [
    saving,
    setSaving
  ] = useState(false);


  useEffect(() => {

    loadData();

  }, [refreshKey]);


  async function loadData() {

    try {

      setLoading(true);

      setError("");

      const [
        measurementsResponse,
        positionsResponse
      ] = await Promise.all([
        getMeasurements(),
        getPositions()
      ]);

      setMeasurements(
        measurementsResponse.measurements
      );

      setPositions(
        positionsResponse.positions
      );

    } catch (error) {

      console.error(error);

      setError(
        error instanceof Error
          ? error.message
          : "Failed to load measurements."
      );

    } finally {

      setLoading(false);

    }
  }


  function startEditing(
    measurement: Measurement
  ) {

    setEditingId(
      measurement.id
    );

    setSelectedPosition(
      measurement.position_id
    );

    setObjectBetween(
      measurement.object_between || ""
    );

    setDistance(
      measurement.distance_cm !== null
        ? String(
            measurement.distance_cm
          )
        : ""
    );

    setNotes(
      measurement.notes || ""
    );

    setFeedbackCorrect(
      measurement.feedback_correct
    );

    setError("");
  }


  function cancelEditing() {

    setEditingId(null);

    setSelectedPosition(null);

    setObjectBetween("");

    setDistance("");

    setNotes("");

    setFeedbackCorrect(null);
  }


  async function handleAddPosition() {

    try {

      const position =
        await createPosition();

      setPositions(
        current => [
          ...current,
          position
        ]
      );

      setSelectedPosition(
        position.id
      );

    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : "Could not create position."
      );
    }
  }


  async function handleSave(
    measurement: Measurement
  ) {

    if (
      selectedPosition === null
    ) {

      setError(
        "Please select the actual location."
      );

      return;
    }


    try {

      setSaving(true);

      setError("");


      const updated =
        await updateMeasurement(
          measurement.id,
          {
            position_id:
              selectedPosition,

            object_between:
              objectBetween.trim()
                || null,

            distance_cm:
              distance.trim()
                ? Number(distance)
                : null,

            notes:
              notes.trim()
                || null
          }
        );


      const finalMeasurement =
        await saveFeedback(
          measurement.id,
          selectedPosition,
          feedbackCorrect === true
        );


      setMeasurements(
        current =>
          current.map(item =>
            item.id === measurement.id
              ? finalMeasurement
              : item
          )
      );


      cancelEditing();

    } catch (error) {

      console.error(error);

      setError(
        error instanceof Error
          ? error.message
          : "Could not save measurement."
      );

    } finally {

      setSaving(false);

    }
  }


  async function handleDiscard(
    measurement: Measurement
  ) {

    const confirmed =
      window.confirm(
        `Discard Measurement ${measurement.id}?`
      );

    if (!confirmed) {
      return;
    }


    try {

      await discardMeasurement(
        measurement.id
      );

      setMeasurements(
        current =>
          current.filter(
            item =>
              item.id !== measurement.id
          )
      );

    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : "Could not discard recording."
      );
    }
  }


  function formatTimestamp(
    timestamp: string
  ) {

    return new Date(
      timestamp
    ).toLocaleString();
  }


  function formatFeatureName(
    name: string
  ) {

    return name
      .replace(
        /_/g,
        " "
      )
      .replace(
        /\b\w/g,
        letter =>
          letter.toUpperCase()
      );
  }


  if (loading) {

    return (
      <section className="measurement-history">

        <div className="history-header">

          <span className="result-label">
            Measurement History
          </span>

          <h2>
            Loading measurements...
          </h2>

        </div>

      </section>
    );
  }


  return (
    <section className="measurement-history">

      <div className="history-header">

        <span className="result-label">
          Measurement History
        </span>

        <h2>
          {measurements.length === 0
            ? "No recordings yet"
            : `${measurements.length} Recording${
                measurements.length === 1
                  ? ""
                  : "s"
              }`}
        </h2>

        <p>
          Review, label and improve
          every recording.
        </p>

      </div>


      {error && (

        <div className="error-card">

          <strong>
            Measurement Error
          </strong>

          <p>
            {error}
          </p>

        </div>
      )}


      {measurements.length > 0 && (

        <div className="history-list">

          {measurements.map(
            measurement => {

              const audioUrl =
                getMeasurementAudioUrl(
                  measurement.id
                );

              const isEditing =
                editingId ===
                measurement.id;


              return (

                <article
                  className="measurement-history-card"
                  key={measurement.id}
                >

                  <div className="history-card-header">

                    <div>

                      <span className="result-label">
                        Measurement{" "}
                        {measurement.id}
                      </span>

                      <h3>
                        {measurement.prediction}
                      </h3>

                      <p>
                        {formatTimestamp(
                          measurement.timestamp
                        )}
                      </p>

                    </div>


                    {measurement.feedback_correct !==
                      null && (

                      <span
                        className={
                          measurement.feedback_correct
                            ? "feedback-badge correct"
                            : "feedback-badge incorrect"
                        }
                      >
                        {measurement.feedback_correct
                          ? "Correct"
                          : "Incorrect"}
                      </span>

                    )}

                  </div>


                  {/* RECORDING */}

                  <div className="recording-section">

                    <span className="result-label">
                      Recording
                    </span>

                    <p className="recording-name">
                      {
                        measurement.recording_filename
                      }
                    </p>


                    <div className="recording-controls">

                      <audio
                        controls
                        preload="none"
                        src={audioUrl}
                      />


                      <a
                        className="download-button"
                        href={audioUrl}
                        download={
                          measurement.recording_filename
                        }
                      >
                        Download WAV
                      </a>

                    </div>

                  </div>


                  {/* ACTUAL LOCATION */}

                  {isEditing ? (

                    <div className="feedback-editor">

                      <span className="result-label">
                        Ground Truth
                      </span>


                      <label>
                        Actual Location
                      </label>


                      <select
                        value={
                          selectedPosition ??
                          ""
                        }
                        onChange={
                          event =>
                            setSelectedPosition(
                              event.target.value
                                ? Number(
                                    event.target.value
                                  )
                                : null
                            )
                        }
                      >

                        <option value="">
                          Select actual position
                        </option>


                        {positions.map(
                          position => (

                            <option
                              key={
                                position.id
                              }
                              value={
                                position.id
                              }
                            >
                              {
                                position.name
                              }
                            </option>

                          )
                        )}

                      </select>


                      <button
                        type="button"
                        className="secondary-button"
                        onClick={
                          handleAddPosition
                        }
                      >
                        + Add Position
                      </button>


                      <label>
                        Was the prediction correct?
                      </label>


                      <div className="feedback-buttons">

                        <button
                          type="button"
                          className={
                            feedbackCorrect === true
                              ? "feedback-choice active"
                              : "feedback-choice"
                          }
                          onClick={() =>
                            setFeedbackCorrect(
                              true
                            )
                          }
                        >
                          Yes
                        </button>


                        <button
                          type="button"
                          className={
                            feedbackCorrect === false
                              ? "feedback-choice active"
                              : "feedback-choice"
                          }
                          onClick={() =>
                            setFeedbackCorrect(
                              false
                            )
                          }
                        >
                          No
                        </button>

                      </div>


                      <label>
                        Object between source
                        and microphone
                      </label>


                      <input
                        type="text"
                        placeholder="e.g. chair, wall, table"
                        value={
                          objectBetween
                        }
                        onChange={
                          event =>
                            setObjectBetween(
                              event.target.value
                            )
                        }
                      />


                      <label>
                        Distance (cm)
                      </label>


                      <input
                        type="number"
                        min="0"
                        step="0.1"
                        placeholder="e.g. 250"
                        value={
                          distance
                        }
                        onChange={
                          event =>
                            setDistance(
                              event.target.value
                            )
                        }
                      />


                      <label>
                        Notes
                      </label>


                      <textarea
                        placeholder="Add experiment details..."
                        value={
                          notes
                        }
                        onChange={
                          event =>
                            setNotes(
                              event.target.value
                            )
                        }
                      />


                      <div className="edit-actions">

                        <button
                          type="button"
                          className="save-button"
                          disabled={saving}
                          onClick={() =>
                            handleSave(
                              measurement
                            )
                          }
                        >
                          {saving
                            ? "Saving..."
                            : "Save Feedback"}
                        </button>


                        <button
                          type="button"
                          className="cancel-button"
                          onClick={
                            cancelEditing
                          }
                        >
                          Cancel
                        </button>

                      </div>

                    </div>

                  ) : (

                    <div className="measurement-details">

                      <span className="result-label">
                        Ground Truth
                      </span>


                      <div className="detail-grid">

                        <div>

                          <span>
                            Actual Location
                          </span>

                          <strong>
                            {
                              measurement
                                .position_name
                              ||
                              "Not labelled"
                            }
                          </strong>

                        </div>


                        <div>

                          <span>
                            Object
                          </span>

                          <strong>
                            {
                              measurement
                                .object_between
                              ||
                              "None specified"
                            }
                          </strong>

                        </div>


                        <div>

                          <span>
                            Distance
                          </span>

                          <strong>
                            {
                              measurement
                                .distance_cm !==
                              null
                                ? `${measurement.distance_cm} cm`
                                : "Not specified"
                            }
                          </strong>

                        </div>

                      </div>


                      {measurement.notes && (

                        <p className="measurement-notes">
                          {measurement.notes}
                        </p>

                      )}

                    </div>

                  )}


                  {/* METADATA */}

                  <div className="result-meta">

                    <div>

                      <span>
                        Duration
                      </span>

                      <strong>
                        {measurement.duration_seconds.toFixed(
                          2
                        )}{" "}
                        s
                      </strong>

                    </div>


                    <div>

                      <span>
                        Sample Rate
                      </span>

                      <strong>
                        {measurement.sample_rate.toLocaleString()}{" "}
                        Hz
                      </strong>

                    </div>


                    {measurement.confidence !==
                      null && (

                      <div>

                        <span>
                          Confidence
                        </span>

                        <strong>
                          {(
                            measurement.confidence *
                            100
                          ).toFixed(1)}
                          %
                        </strong>

                      </div>
                    )}

                  </div>


                  {/* FEATURES */}

                  <div className="feature-section">

                    <span className="result-label">
                      Extracted Features
                    </span>


                    <div className="feature-grid">

                      {Object.entries(
                        measurement.features
                      ).map(
                        ([name, value]) => (

                          <div
                            className="feature"
                            key={name}
                          >

                            <span>
                              {formatFeatureName(
                                name
                              )}
                            </span>

                            <strong>
                              {value.toFixed(
                                4
                              )}
                            </strong>

                          </div>

                        )
                      )}

                    </div>

                  </div>


                  {/* ACTIONS */}

                  {!isEditing && (

                    <div className="history-actions">

                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() =>
                          startEditing(
                            measurement
                          )
                        }
                      >
                        {measurement.position_id
                          ? "Edit Details"
                          : "Add Location & Feedback"}
                      </button>


                      <button
                        type="button"
                        className="discard-button"
                        onClick={() =>
                          handleDiscard(
                            measurement
                          )
                        }
                      >
                        Discard
                      </button>

                    </div>

                  )}

                </article>

              );

            }
          )}

        </div>

      )}

    </section>
  );
}