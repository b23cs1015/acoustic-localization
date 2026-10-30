import { useEffect, useMemo, useRef, useState } from "react";
import { audioBufferToWav } from "../lib/wav";
import { DEFAULT_ROOM_MAPPING_CONFIG, RoomMappingRecorder } from "../lib/roomMappingRecorder";
import {
  uploadRoomMappingRecording,
  createExperiment,
  getExperiments,
  getRecordingHistory,
  getRoomMappingDownloadUrl,
  getRoomMappingMetadataUrl,
  deleteExperiment,
  deleteBatch,
  type RoomMappingUploadResult,
  type Experiment,
  type RecordingHistoryItem,
} from "../lib/roomMappingApi";

type MappingState = "idle" | "recording" | "uploading" | "complete" | "error";
type ExperimentMode = "new" | "existing";

function formatDuration(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(safe / 60)).padStart(2, "0")}:${String(safe % 60).padStart(2, "0")}`;
}

function groupByBatch(items: RecordingHistoryItem[]) {
  const groups = new Map<string, RecordingHistoryItem[]>();

  for (const item of items) {
    const key = `${item.experiment_number}::${item.batch_id || `MANUAL_${item.mapping_id}`}`;
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }

  return [...groups.entries()].map(([key, recordings]) => ({
    key,
    recordings,
    first: recordings[0],
  }));
}

export default function RoomMapping() {
  const recorderRef = useRef<RoomMappingRecorder | null>(null);
  const timerRef = useRef<number | null>(null);
  const batchCancelRef = useRef(false);
  const activeExperimentRef = useRef<Experiment | null>(null);

  const [roomName, setRoomName] = useState("Room 1");
  const [remarks, setRemarks] = useState("");
  const [state, setState] = useState<MappingState>("idle");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState("");
  const [result, setResult] = useState<RoomMappingUploadResult | null>(null);

  const [experimentMode, setExperimentMode] = useState<ExperimentMode>("new");
  const [experimentNumber, setExperimentNumber] = useState("EXP-015");
  const [experimentTitle, setExperimentTitle] = useState("");
  const [experimentDescription, setExperimentDescription] = useState("");
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedExperiment, setSelectedExperiment] = useState("");

  const [positionId, setPositionId] = useState("P1");
  const [distanceCm, setDistanceCm] = useState("");
  const [xCm, setXCm] = useState("");
  const [yCm, setYCm] = useState("");
  const [phoneHeightCm, setPhoneHeightCm] = useState("");

  const [batchCount, setBatchCount] = useState(10);
  const [sampleDurationSeconds, setSampleDurationSeconds] = useState(5);
  const [delaySeconds, setDelaySeconds] = useState(2);
  const [batchRunning, setBatchRunning] = useState(false);
  const [batchCompleted, setBatchCompleted] = useState(0);
  const [batchTarget, setBatchTarget] = useState(0);
  const [batchFailures, setBatchFailures] = useState<string[]>([]);

  const [recordings, setRecordings] = useState<RecordingHistoryItem[]>([]);
  const [historyFilter, setHistoryFilter] = useState("");
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [deletingKey, setDeletingKey] = useState("");

  const isRecording = state === "recording";

  const isBusy =
    isRecording ||
    state === "uploading" ||
    batchRunning ||
    Boolean(deletingKey);

  const batchGroups = useMemo(
    () => groupByBatch(recordings),
    [recordings]
  );

  useEffect(() => {
    void loadExperiments();
    void loadRecordings();

    return () => {
      if (timerRef.current !== null) {
        window.clearInterval(timerRef.current);
      }

      batchCancelRef.current = true;

      if (recorderRef.current) {
        void recorderRef.current.cancel();
      }
    };
  }, []);

  async function loadExperiments() {
    try {
      const data = await getExperiments();
      setExperiments(data);

      if (
        selectedExperiment &&
        !data.some(item => item.experiment_number === selectedExperiment)
      ) {
        setSelectedExperiment("");
      }
    } catch (err) {
      console.error("Could not load experiments:", err);
    }
  }

  async function loadRecordings(
    experiment?: string,
    position?: string
  ) {
    setHistoryLoading(true);
    setHistoryError("");

    try {
      const data = await getRecordingHistory(experiment, position);
      setRecordings(data.recordings);
    } catch (err) {
      setHistoryError(
        err instanceof Error
          ? err.message
          : "Could not load recording history."
      );
    } finally {
      setHistoryLoading(false);
    }
  }

  function startTimer() {
    stopTimer();

    timerRef.current = window.setInterval(() => {
      if (recorderRef.current) {
        setElapsedSeconds(recorderRef.current.elapsedSeconds);
      }
    }, 100);
  }

  function stopTimer() {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  async function resolveExperiment(): Promise<Experiment> {
    if (experimentMode === "new") {
      if (!experimentNumber.trim()) {
        throw new Error("Enter an experiment number.");
      }

      if (!experimentTitle.trim()) {
        throw new Error("Enter an experiment title.");
      }

      const created = await createExperiment({
        experimentNumber: experimentNumber.trim(),
        experimentTitle: experimentTitle.trim(),
        description: experimentDescription.trim(),
        roomName: roomName.trim(),
      });

      await loadExperiments();

      setSelectedExperiment(created.experiment_number);
      setExperimentMode("existing");

      return created;
    }

    const existing = experiments.find(
      item => item.experiment_number === selectedExperiment
    );

    if (!existing) {
      throw new Error("Select an existing experiment.");
    }

    return existing;
  }

  function validatePosition() {
    if (!roomName.trim()) {
      throw new Error("Enter a room name.");
    }

    if (!positionId.trim()) {
      throw new Error("Enter a position ID.");
    }

    const values: [string, string][] = [
      ["Distance from target", distanceCm],
      ["X coordinate", xCm],
      ["Y coordinate", yCm],
      ["Phone height", phoneHeightCm],
    ];

    for (const [label, value] of values) {
      if (
        value.trim() &&
        (!Number.isFinite(Number(value)) || Number(value) < 0)
      ) {
        throw new Error(
          `${label} must be a valid non-negative number.`
        );
      }
    }
  }

  async function uploadRecording(
    recording: {
      audioBuffer: AudioBuffer;
      durationSeconds: number;
      sampleRate: number;
    },
    experiment: Experiment,
    batchId?: string,
    recordingNumber?: number,
    totalRecordings?: number
  ): Promise<RoomMappingUploadResult> {
    const wavBlob = audioBufferToWav(recording.audioBuffer);

    return uploadRoomMappingRecording(wavBlob, {
      roomName,
      remarks,
      durationSeconds: recording.durationSeconds,
      sampleRate: recording.sampleRate,

      startFrequency: DEFAULT_ROOM_MAPPING_CONFIG.startFrequency,
      endFrequency: DEFAULT_ROOM_MAPPING_CONFIG.endFrequency,
      chirpDuration: DEFAULT_ROOM_MAPPING_CONFIG.chirpDuration,

      experimentNumber: experiment.experiment_number,
      experimentTitle: experiment.experiment_title,

      positionId: positionId.trim(),

      distanceCm: distanceCm.trim()
        ? Number(distanceCm)
        : undefined,

      xCm: xCm.trim()
        ? Number(xCm)
        : undefined,

      yCm: yCm.trim()
        ? Number(yCm)
        : undefined,

      phoneHeightCm: phoneHeightCm.trim()
        ? Number(phoneHeightCm)
        : undefined,

      batchId,
      recordingNumber,
      totalRecordings,
    });
  }

  async function handleStart() {
    if (isBusy) return;

    setError("");
    setResult(null);
    setElapsedSeconds(0);

    try {
      validatePosition();

      const experiment = await resolveExperiment();
      activeExperimentRef.current = experiment;

      const recorder = new RoomMappingRecorder(
        DEFAULT_ROOM_MAPPING_CONFIG
      );

      recorderRef.current = recorder;

      await recorder.start();

      setState("recording");
      startTimer();
    } catch (err) {
      recorderRef.current = null;
      setState("error");

      setError(
        err instanceof Error
          ? err.message
          : "Could not start recording."
      );
    }
  }

  async function handleStop() {
    const recorder = recorderRef.current;
    const experiment = activeExperimentRef.current;

    if (!recorder || !experiment || !isRecording) return;

    stopTimer();
    setState("uploading");
    setError("");

    try {
      const recording = await recorder.stop();
      recorderRef.current = null;

      if (recording.durationSeconds < 1) {
        throw new Error("Recording is too short.");
      }

      const uploaded = await uploadRecording(
        recording,
        experiment
      );

      setElapsedSeconds(recording.durationSeconds);
      setResult(uploaded);
      setState("complete");

      await loadExperiments();
      await loadRecordings(experiment.experiment_number);
    } catch (err) {
      recorderRef.current = null;
      setState("error");

      setError(
        err instanceof Error
          ? err.message
          : "Recording upload failed."
      );
    }
  }

  async function handleStartBatch() {
    if (isBusy) return;

    const count = Math.floor(batchCount);
    const duration = Number(sampleDurationSeconds);
    const delay = Number(delaySeconds);

    setError("");
    setResult(null);
    setBatchFailures([]);
    setBatchCompleted(0);
    setBatchTarget(0);

    try {
      validatePosition();

      if (!Number.isFinite(count) || count < 1 || count > 100) {
        throw new Error("Batch size must be between 1 and 100.");
      }

      if (
        !Number.isFinite(duration) ||
        duration < 1 ||
        duration > 300
      ) {
        throw new Error(
          "Recording duration must be between 1 and 300 seconds."
        );
      }

      if (
        !Number.isFinite(delay) ||
        delay < 0 ||
        delay > 60
      ) {
        throw new Error(
          "Delay must be between 0 and 60 seconds."
        );
      }

      const experiment = await resolveExperiment();
      activeExperimentRef.current = experiment;

      const randomSuffix =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID().slice(0, 8)
          : Math.random().toString(16).slice(2, 10);

      const batchId = `BATCH_${Date.now()}_${randomSuffix}`;

      batchCancelRef.current = false;
      setBatchTarget(count);
      setBatchRunning(true);

      const failures: string[] = [];
      let successes = 0;

      for (let index = 1; index <= count; index++) {
        if (batchCancelRef.current) break;

        setElapsedSeconds(0);
        setState("recording");

        const recorder = new RoomMappingRecorder(
          DEFAULT_ROOM_MAPPING_CONFIG
        );

        recorderRef.current = recorder;

        try {
          await recorder.start();
          startTimer();

          await new Promise<void>(resolve =>
            window.setTimeout(resolve, duration * 1000)
          );

          if (batchCancelRef.current) {
            stopTimer();
            await recorder.cancel();
            recorderRef.current = null;
            break;
          }

          stopTimer();
          setState("uploading");

          const recording = await recorder.stop();
          recorderRef.current = null;

          if (recording.durationSeconds < 1) {
            throw new Error("Recording was too short.");
          }

          await uploadRecording(
            recording,
            experiment,
            batchId,
            index,
            count
          );

          successes++;
          setBatchCompleted(successes);
        } catch (sampleError) {
          stopTimer();

          if (recorderRef.current) {
            await recorderRef.current
              .cancel()
              .catch(() => undefined);

            recorderRef.current = null;
          }

          if (batchCancelRef.current) break;

          failures.push(
            `Recording ${index}: ${
              sampleError instanceof Error
                ? sampleError.message
                : "Unknown error"
            }`
          );

          setBatchFailures([...failures]);
        }

        if (
          index < count &&
          !batchCancelRef.current &&
          delay > 0
        ) {
          setState("idle");

          await new Promise<void>(resolve =>
            window.setTimeout(resolve, delay * 1000)
          );
        }
      }

      setBatchFailures([...failures]);

      if (batchCancelRef.current) {
        setState("complete");
        setError(
          `Batch cancelled. ${successes} recording(s) saved.`
        );
      } else if (failures.length) {
        setState("error");
        setError(
          `Batch finished. ${successes} saved, ${failures.length} failed.`
        );
      } else {
        setState("complete");
      }

      await loadExperiments();
      await loadRecordings(experiment.experiment_number);
    } catch (err) {
      setState("error");

      setError(
        err instanceof Error
          ? err.message
          : "Batch collection failed."
      );
    } finally {
      stopTimer();
      recorderRef.current = null;
      setBatchRunning(false);
    }
  }

  function handleCancelBatch() {
    batchCancelRef.current = true;
    stopTimer();

    if (recorderRef.current) {
      void recorderRef.current.cancel();
      recorderRef.current = null;
    }
  }

  function handleReset() {
    stopTimer();

    if (recorderRef.current) {
      void recorderRef.current.cancel();
      recorderRef.current = null;
    }

    setState("idle");
    setElapsedSeconds(0);
    setError("");
    setResult(null);
  }

  async function handleDeleteExperiment(experiment: Experiment) {
    const label =
      `${experiment.experiment_number} — ${experiment.experiment_title}`;

    if (
      !window.confirm(
        `Permanently delete ${label} and ALL its batches, WAV files and metadata? This cannot be undone.`
      )
    ) {
      return;
    }

    setDeletingKey(`experiment:${experiment.experiment_number}`);

    try {
      await deleteExperiment(experiment.experiment_number);

      if (selectedExperiment === experiment.experiment_number) {
        setSelectedExperiment("");
        setExperimentMode("new");
      }

      if (historyFilter === experiment.experiment_number) {
        setHistoryFilter("");
      }

      await loadExperiments();

      await loadRecordings(
        historyFilter === experiment.experiment_number
          ? undefined
          : historyFilter || undefined
      );
    } catch (err) {
      setHistoryError(
        err instanceof Error
          ? err.message
          : "Could not delete experiment."
      );
    } finally {
      setDeletingKey("");
    }
  }

  async function handleDeleteBatch(
    experimentNumberValue: string,
    batchId: string,
    count: number
  ) {
    if (
      !window.confirm(
        `Delete batch ${batchId} and its ${count} recording(s), WAV files and metadata?`
      )
    ) {
      return;
    }

    const key = `batch:${experimentNumberValue}:${batchId}`;
    setDeletingKey(key);

    try {
      await deleteBatch(experimentNumberValue, batchId);

      await loadExperiments();
      await loadRecordings(historyFilter || undefined);
    } catch (err) {
      setHistoryError(
        err instanceof Error
          ? err.message
          : "Could not delete batch."
      );
    } finally {
      setDeletingKey("");
    }
  }

  return (
    <main className="main-content room-mapping-page">
      <section className="room-mapping-hero">
        <p className="eyebrow">BTP · Acoustic Localization</p>
        <h1>Room Acoustic Mapping</h1>
        <p className="hero-description">
          Collect acoustic measurements at known positions. Organize
          recordings into experiments and batches for further analysis.
        </p>
      </section>

      <section className="room-mapping-workspace">
        <div className="room-mapping-card">
          <h2>Experiment Configuration</h2>

          <div className="room-mapping-coordinate-grid">
            <button
              type="button"
              className={
                experimentMode === "new"
                  ? "room-mapping-start-button"
                  : "secondary-button"
              }
              onClick={() => setExperimentMode("new")}
              disabled={isBusy}
            >
              Create New Experiment
            </button>

            <button
              type="button"
              className={
                experimentMode === "existing"
                  ? "room-mapping-start-button"
                  : "secondary-button"
              }
              onClick={() => setExperimentMode("existing")}
              disabled={isBusy}
            >
              Continue Existing
            </button>
          </div>

          {experimentMode === "new" ? (
            <>
              <label className="field-label">Experiment Number</label>
              <input
                value={experimentNumber}
                onChange={e => setExperimentNumber(e.target.value)}
                disabled={isBusy}
                placeholder="EXP-015"
              />

              <label className="field-label">Experiment Title</label>
              <input
                value={experimentTitle}
                onChange={e => setExperimentTitle(e.target.value)}
                disabled={isBusy}
                placeholder="Spatial Acoustic Repeatability"
              />

              <label className="field-label">Experiment Description</label>
              <textarea
                value={experimentDescription}
                onChange={e => setExperimentDescription(e.target.value)}
                disabled={isBusy}
                rows={3}
                placeholder="Describe the purpose of this experiment..."
              />
            </>
          ) : (
            <>
              <label className="field-label">
                Select Existing Experiment
              </label>

              <select
                value={selectedExperiment}
                onChange={e => setSelectedExperiment(e.target.value)}
                disabled={isBusy}
              >
                <option value="">Select experiment</option>

                {experiments.map(item => (
                  <option
                    key={item.experiment_number}
                    value={item.experiment_number}
                  >
                    {item.experiment_number} — {item.experiment_title}
                  </option>
                ))}
              </select>

              {experiments.find(
                item => item.experiment_number === selectedExperiment
              ) && (
                <p className="section-kicker">
                  {
                    experiments.find(
                      item => item.experiment_number === selectedExperiment
                    )?.total_recordings
                  }{" "}
                  existing recordings ·{" "}
                  {
                    experiments.find(
                      item => item.experiment_number === selectedExperiment
                    )?.total_positions
                  }{" "}
                  positions
                </p>
              )}
            </>
          )}

          <h2>Room Information</h2>

          <label className="field-label">Room Name</label>
          <input
            value={roomName}
            onChange={e => setRoomName(e.target.value)}
            disabled={isBusy}
            placeholder="Room 1"
          />

          <label className="field-label">Remarks</label>
          <textarea
            value={remarks}
            onChange={e => setRemarks(e.target.value)}
            disabled={isBusy}
            rows={2}
            placeholder="Environmental conditions, furniture, noise..."
          />

          <h2>Position Information</h2>

          <label className="field-label">Position ID</label>
          <input
            value={positionId}
            onChange={e => setPositionId(e.target.value)}
            disabled={isBusy}
            placeholder="P1"
          />

          <div className="room-mapping-coordinate-grid">
            <div>
              <label className="field-label">
                Distance from target (cm)
              </label>
              <input
                type="number"
                min="0"
                step="any"
                value={distanceCm}
                onChange={e => setDistanceCm(e.target.value)}
                disabled={isBusy}
                placeholder="Optional"
              />
            </div>

            <div>
              <label className="field-label">X coordinate (cm)</label>
              <input
                type="number"
                min="0"
                step="any"
                value={xCm}
                onChange={e => setXCm(e.target.value)}
                disabled={isBusy}
                placeholder="Optional"
              />
            </div>

            <div>
              <label className="field-label">Y coordinate (cm)</label>
              <input
                type="number"
                min="0"
                step="any"
                value={yCm}
                onChange={e => setYCm(e.target.value)}
                disabled={isBusy}
                placeholder="Optional"
              />
            </div>

            <div>
              <label className="field-label">Phone Height (cm)</label>
              <input
                type="number"
                min="0"
                step="any"
                value={phoneHeightCm}
                onChange={e => setPhoneHeightCm(e.target.value)}
                disabled={isBusy}
                placeholder="Optional"
              />
            </div>
          </div>

          <h2>Batch Collection</h2>

          <div className="room-mapping-coordinate-grid">
            <div>
              <label className="field-label">
                Number of Recordings
              </label>
              <input
                type="number"
                min="1"
                max="100"
                value={batchCount}
                onChange={e => setBatchCount(Number(e.target.value))}
                disabled={isBusy}
              />
            </div>

            <div>
              <label className="field-label">
                Recording Duration (seconds)
              </label>
              <input
                type="number"
                min="1"
                max="300"
                value={sampleDurationSeconds}
                onChange={e =>
                  setSampleDurationSeconds(Number(e.target.value))
                }
                disabled={isBusy}
              />
            </div>

            <div>
              <label className="field-label">
                Delay Between Recordings (seconds)
              </label>
              <input
                type="number"
                min="0"
                max="60"
                value={delaySeconds}
                onChange={e => setDelaySeconds(Number(e.target.value))}
                disabled={isBusy}
              />
            </div>
          </div>

          <div className="room-mapping-parameters">
            <div>
              <span>Frequency</span>
              <strong>15–20 kHz</strong>
            </div>
            <div>
              <span>Chirp Duration</span>
              <strong>1 second</strong>
            </div>
            <div>
              <span>Sample Rate</span>
              <strong>48 kHz target</strong>
            </div>
            <div>
              <span>Recording Mode</span>
              <strong>Manual + Batch</strong>
            </div>
          </div>

          <div className="room-mapping-timer">
            <span>Elapsed Time</span>
            <strong>{formatDuration(elapsedSeconds)}</strong>
          </div>

          <div className="room-mapping-actions">
            {!batchRunning && !isRecording && state !== "uploading" && (
              <>
                <button
                  type="button"
                  className="room-mapping-start-button"
                  onClick={() => void handleStartBatch()}
                  disabled={isBusy}
                >
                  Start Batch Collection
                </button>

                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => void handleStart()}
                  disabled={isBusy}
                >
                  Start Manual Recording
                </button>
              </>
            )}

            {batchRunning && (
              <div className="room-mapping-uploading">
                <strong>
                  Batch Progress: {batchCompleted}/{batchTarget}
                </strong>

                <progress
                  value={batchCompleted}
                  max={batchTarget || 1}
                />

                <button
                  type="button"
                  className="room-mapping-stop-button"
                  onClick={handleCancelBatch}
                >
                  Cancel Batch
                </button>
              </div>
            )}

            {isRecording && !batchRunning && (
              <button
                type="button"
                className="room-mapping-stop-button"
                onClick={() => void handleStop()}
              >
                Stop Recording &amp; Upload
              </button>
            )}

            {state === "uploading" && <p>Uploading recording...</p>}
          </div>

          {batchFailures.length > 0 && (
            <div className="error-card">
              <strong>Failed Recordings</strong>
              <ul>
                {batchFailures.map((failure, index) => (
                  <li key={index}>{failure}</li>
                ))}
              </ul>
            </div>
          )}

          {error && (
            <div className="error-card room-mapping-error">
              <strong>Notice</strong>
              <p>{error}</p>
              <button type="button" onClick={handleReset}>
                Reset
              </button>
            </div>
          )}

          {result && (
            <div className="room-mapping-result-card">
              <h3>Recording Saved</h3>
              <p>{result.filename}</p>

              <a href={getRoomMappingDownloadUrl(result.mapping_id)}>
                Download WAV
              </a>

              <a href={getRoomMappingMetadataUrl(result.mapping_id)}>
                Download Metadata
              </a>
            </div>
          )}
        </div>

        <aside className="room-mapping-instructions">
          <p className="section-kicker">Collection Protocol</p>
          <h2>Experimental Guidelines</h2>

          <ol>
            <li>Select or create an experiment.</li>
            <li>Enter the position ID and distance.</li>
            <li>Keep the phone orientation consistent.</li>
            <li>Configure the number of recordings.</li>
            <li>Start batch collection.</li>
            <li>Wait until all recordings are saved.</li>
          </ol>

          <div className="room-mapping-warning">
            <strong>Research Note</strong>
            <p>
              Distance refers to phone-to-target distance. Leave it empty
              if no identifiable target exists. Coordinates must represent
              measured physical positions.
            </p>
          </div>
        </aside>
      </section>

      <section className="room-mapping-card room-mapping-history-card">
        <div className="room-mapping-history-heading">
          <div>
            <h2>Experiment &amp; Recording History</h2>
            <p>
              Review, download or permanently delete saved experiment data.
            </p>
          </div>

          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              void loadExperiments();
              void loadRecordings(historyFilter || undefined);
            }}
          >
            Refresh History
          </button>
        </div>

        <div className="room-mapping-experiment-list">
          {experiments.map(experiment => (
            <article
              className="room-mapping-experiment-item"
              key={experiment.experiment_number}
            >
              <div>
                <strong>
                  {experiment.experiment_number} —{" "}
                  {experiment.experiment_title}
                </strong>

                <p>
                  {experiment.total_recordings} recordings ·{" "}
                  {experiment.total_positions} positions ·{" "}
                  {experiment.room_name}
                </p>

                <small>
                  Created {new Date(experiment.created_at).toLocaleString()}
                </small>
              </div>

              <button
                type="button"
                className="room-mapping-delete-button"
                disabled={isBusy}
                onClick={() => void handleDeleteExperiment(experiment)}
              >
                {deletingKey === `experiment:${experiment.experiment_number}`
                  ? "Deleting…"
                  : "Delete Experiment"}
              </button>
            </article>
          ))}

          {experiments.length === 0 && (
            <p className="room-mapping-empty">
              No experiments have been created yet.
            </p>
          )}
        </div>

        <div className="room-mapping-history-filter">
          <div>
            <label className="field-label">
              Filter recordings by experiment
            </label>

            <select
              value={historyFilter}
              onChange={async e => {
                const value = e.target.value;
                setHistoryFilter(value);
                await loadRecordings(value || undefined);
              }}
            >
              <option value="">All Experiments</option>

              {experiments.map(item => (
                <option
                  key={item.experiment_number}
                  value={item.experiment_number}
                >
                  {item.experiment_number} — {item.experiment_title}
                </option>
              ))}
            </select>
          </div>

          <span>{recordings.length} recording(s)</span>
        </div>

        {historyLoading && <p>Loading recordings...</p>}

        {historyError && (
          <div className="error-card">{historyError}</div>
        )}

        {!historyLoading &&
          recordings.length === 0 &&
          !historyError && (
            <p className="room-mapping-empty">No recordings found.</p>
          )}

        <div className="room-mapping-batch-list">
          {batchGroups.map(group => {
            const first = group.first;

            const isDeleting =
              deletingKey ===
              `batch:${first.experiment_number}:${first.batch_id}`;

            return (
              <article
                className="room-mapping-batch-card"
                key={group.key}
              >
                <div className="room-mapping-batch-header">
                  <div>
                    <span className="room-mapping-batch-label">
                      BATCH
                    </span>

                    <h3>{first.batch_id || "Manual recording"}</h3>

                    <p>
                      {first.experiment_number} · Position{" "}
                      {first.position_id} · {group.recordings.length}{" "}
                      recording(s)
                    </p>
                  </div>

                  <button
                    type="button"
                    className="room-mapping-delete-button"
                    disabled={isBusy || !first.batch_id}
                    onClick={() =>
                      void handleDeleteBatch(
                        first.experiment_number,
                        first.batch_id,
                        group.recordings.length
                      )
                    }
                  >
                    {isDeleting ? "Deleting…" : "Delete Batch"}
                  </button>
                </div>

                <div className="room-mapping-recording-grid">
                  {group.recordings.map(recording => (
                    <div
                      className="room-mapping-history-item"
                      key={recording.mapping_id}
                    >
                      <div className="room-mapping-recording-title">
                        <strong>
                          Recording {recording.recording_number ?? "—"}
                          {recording.total_recordings
                            ? ` / ${recording.total_recordings}`
                            : ""}
                        </strong>

                        <span>
                          {new Date(recording.created_at).toLocaleString()}
                        </span>
                      </div>

                      <p>
                        Distance:{" "}
                        {recording.distance_cm !== null
                          ? `${recording.distance_cm} cm`
                          : "Not specified"}
                      </p>

                      <p>
                        Coordinates:{" "}
                        {recording.x_cm !== null &&
                        recording.y_cm !== null
                          ? `(${recording.x_cm}, ${recording.y_cm}) cm`
                          : "Not specified"}{" "}
                        · Phone height:{" "}
                        {recording.phone_height_cm !== null
                          ? `${recording.phone_height_cm} cm`
                          : "—"}
                      </p>

                      <p>
                        Duration:{" "}
                        {Number(recording.duration_seconds).toFixed(2)} s ·
                        Sample rate: {recording.sample_rate} Hz
                      </p>

                      <div className="room-mapping-download-actions">
                        <a
                          href={getRoomMappingDownloadUrl(
                            recording.mapping_id
                          )}
                          className="primary-button"
                        >
                          Download WAV
                        </a>

                        <a
                          href={getRoomMappingMetadataUrl(
                            recording.mapping_id
                          )}
                          className="secondary-button"
                        >
                          Download JSON
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </main>
  );
}