import {
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import {
  createDatasetPosition,
  createDatasetSample,
  deleteDatasetSample,
  getDatasetSample,
  getDatasetSampleAudioUrl,
  getDatasetPositions,
  getDatasetSamples,
  getDatasetSummary,
  predictDatasetSample,
  predictAllDatasetSamples,
  getDatasetFeaturesCsvUrl,
  getDatasetPredictionsCsvUrl,
  updateDatasetSample,
  type DatasetPosition,
  type DatasetSample,
  type DatasetSummary,
  type PredictionResult,
  type TargetPresence
} from "../lib/datasetApi";

import {
  DEFAULT_CHIRP_CONFIG,
  playChirp
} from "../lib/chirp";

import {
  recordMicrophone
} from "../lib/recorder";

import {
  audioBufferToWav
} from "../lib/wav";


type CollectionState =
  | "idle"
  | "recording"
  | "saving";


type EditState = {
  sample: DatasetSample;

  positionId:
    | number
    | null;

  targetPresence:
    TargetPresence;

  distanceCm: string;

  remarks: string;
};


const TARGET_OPTIONS:
  Array<{
    value: TargetPresence;
    label: string;
  }> = [

  {
    value: "yes",
    label: "Yes"
  },

  {
    value: "no",
    label: "No"
  },

  {
    value: "cant_say",
    label: "Can't say"
  }

];


const DISTANCE_OPTIONS = [
  15,
  30,
  45
];


const FEATURE_LABELS:
  Record<string, string> = {

  rms_dB:
    "RMS level",

  peak_dB:
    "Peak level",

  spectral_centroid_Hz:
    "Spectral centroid",

  spectral_bandwidth_Hz:
    "Spectral bandwidth",

  spectral_rolloff_Hz:
    "Spectral rolloff",

  spectral_flatness:
    "Spectral flatness",

  zero_crossing_rate:
    "Zero-crossing rate",

  "15_16kHz_dB":
    "15–16 kHz energy",

  "16_17kHz_dB":
    "16–17 kHz energy",

  "17_18kHz_dB":
    "17–18 kHz energy",

  "18_19kHz_dB":
    "18–19 kHz energy",

  "19_20kHz_dB":
    "19–20 kHz energy"

};


const FEATURE_ORDER = [
  "rms_dB",
  "peak_dB",
  "spectral_centroid_Hz",
  "spectral_bandwidth_Hz",
  "spectral_rolloff_Hz",
  "spectral_flatness",
  "zero_crossing_rate",
  "15_16kHz_dB",
  "16_17kHz_dB",
  "17_18kHz_dB",
  "18_19kHz_dB",
  "19_20kHz_dB"
];


function formatTarget(
  target: TargetPresence
): string {

  if (
    target === "yes"
  ) {

    return "Yes";

  }

  if (
    target === "no"
  ) {

    return "No";

  }

  return "Can't say";
}


function formatDate(
  timestamp: string
): string {

  const date =
    new Date(timestamp);


  if (
    Number.isNaN(
      date.getTime()
    )
  ) {

    return timestamp;

  }


  return date.toLocaleString();
}


/*
 * Confidence and accuracy are stored as
 * values between 0 and 1.
 *
 * Example:
 * 0.7164 -> 71.6%
 * 0.825  -> 82.5%
 */
function formatConfidence(
  confidence:
    | number
    | null
    | undefined
): string {

  if (
    typeof confidence !== "number" ||
    !Number.isFinite(confidence)
  ) {

    return "—";

  }


  return (
    `${(
      confidence * 100
    ).toFixed(1)}%`
  );
}


function formatEvaluation(
  evaluation:
    | string
    | null
    | undefined
): string {

  if (
    evaluation === "correct"
  ) {

    return "Correct";

  }


  if (
    evaluation === "incorrect"
  ) {

    return "Incorrect";

  }


  return "Not evaluable";
}


function formatDistance(
  distance:
    | number
    | null
    | undefined
): string {

  if (
    typeof distance !== "number" ||
    !Number.isFinite(distance)
  ) {

    return "—";

  }


  return distance.toFixed(3);
}


function getSampleFeatures(
  sample: DatasetSample
): Record<string, unknown> {

  const rawFeatures =
    (
      sample as DatasetSample & {
        features?: unknown;
        acoustic_features?: unknown;
      }
    ).features;


  if (
    rawFeatures &&
    typeof rawFeatures === "object" &&
    !Array.isArray(rawFeatures)
  ) {

    return rawFeatures as Record<
      string,
      unknown
    >;

  }


  const acousticFeatures =
    (
      sample as DatasetSample & {
        acoustic_features?: unknown;
      }
    ).acoustic_features;


  if (
    acousticFeatures &&
    typeof acousticFeatures === "object" &&
    !Array.isArray(acousticFeatures)
  ) {

    return acousticFeatures as Record<
      string,
      unknown
    >;

  }


  return {};
}


function formatFeatureValue(
  value: unknown
): string {

  if (
    typeof value === "number"
  ) {

    if (
      !Number.isFinite(value)
    ) {

      return "—";

    }


    return value.toFixed(4);

  }


  if (
    typeof value === "string"
  ) {

    return value;

  }


  return "—";
}


function getFeatureEntries(
  sample: DatasetSample
): Array<{
  key: string;
  label: string;
  value: unknown;
}> {

  const features =
    getSampleFeatures(sample);


  return FEATURE_ORDER
    .filter(
      key =>
        Object.prototype.hasOwnProperty.call(
          features,
          key
        )
    )
    .map(
      key => ({

        key,

        label:
          FEATURE_LABELS[key] ??
          key,

        value:
          features[key]

      })
    );

}


export default function CollectData() {

  const [
    positions,
    setPositions
  ] = useState<
    DatasetPosition[]
  >([]);


  const [
    samples,
    setSamples
  ] = useState<
    DatasetSample[]
  >([]);


  const [
    summary,
    setSummary
  ] = useState<
    DatasetSummary | null
  >(null);


  const [
    selectedPositionId,
    setSelectedPositionId
  ] = useState<
    number | null
  >(null);


  const [
    targetPresence,
    setTargetPresence
  ] = useState<TargetPresence>(
    "yes"
  );


  const [
    distanceCm,
    setDistanceCm
  ] = useState("15");


  const [
    remarks,
    setRemarks
  ] = useState("");


  const [
    newPositionName,
    setNewPositionName
  ] = useState("");


  const [
    collectionState,
    setCollectionState
  ] = useState<CollectionState>(
    "idle"
  );


  const [
    message,
    setMessage
  ] = useState<
    string | null
  >(null);


  const [
    error,
    setError
  ] = useState<
    string | null
  >(null);


  const [
    editing,
    setEditing
  ] = useState<
    EditState | null
  >(null);


  const [
    prediction,
    setPrediction
  ] = useState<
    PredictionResult | null
  >(null);


  const [
    predictionSampleId,
    setPredictionSampleId
  ] = useState<
    number | null
  >(null);


  /*
   * Tracks the bulk prediction operation.
   * While this is true, another prediction
   * operation cannot be started.
   */
  const [
    predictingAll,
    setPredictingAll
  ] = useState(false);


  const [
    featureSampleId,
    setFeatureSampleId
  ] = useState<
    number | null
  >(null);


  const [
    audioPlayingId,
    setAudioPlayingId
  ] = useState<
    number | null
  >(null);


  const audioRef =
    useRef<HTMLAudioElement | null>(
      null
    );


  async function loadDataset() {

    try {

      setError(null);


      const [
        loadedPositions,
        loadedSamples,
        loadedSummary
      ] = await Promise.all([

        getDatasetPositions(),

        getDatasetSamples(),

        getDatasetSummary()

      ]);


      setPositions(
        loadedPositions
      );

      setSamples(
        loadedSamples
      );

      setSummary(
        loadedSummary
      );


      if (
        selectedPositionId === null &&
        loadedPositions.length > 0
      ) {

        setSelectedPositionId(
          loadedPositions[0].id
        );

      }

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to load dataset."
      );

    }
  }


  useEffect(() => {

    void loadDataset();

  }, []);


  const selectedPosition =
    useMemo(

      () =>
        positions.find(
          position =>
            position.id ===
            selectedPositionId
        ) ?? null,

      [
        positions,
        selectedPositionId
      ]

    );


  const featureSample =
    useMemo(

      () => {

        if (
          featureSampleId === null
        ) {

          return null;

        }


        return (
          samples.find(
            sample =>
              sample.id ===
              featureSampleId
          ) ?? null
        );

      },

      [
        samples,
        featureSampleId
      ]

    );


  const featureEntries =
    featureSample
      ? getFeatureEntries(
          featureSample
        )
      : [];


  async function handleCreatePosition() {

    const name =
      newPositionName.trim();


    if (!name) {

      setError(
        "Enter a position name first."
      );

      return;

    }


    try {

      setError(null);

      setMessage(null);


      const created =
        await createDatasetPosition(
          name
        );


      setPositions(
        current => [
          ...current,
          created
        ]
      );


      setSelectedPositionId(
        created.id
      );


      setNewPositionName("");


      setMessage(
        `${created.name} was added as a dataset position.`
      );

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to create position."
      );

    }
  }


  async function handleCollectSample() {

    if (
      collectionState !== "idle"
    ) {

      return;

    }


    /*
     * Do not start a recording while bulk
     * prediction is modifying the dataset.
     */
    if (
      predictingAll
    ) {

      return;

    }


    if (
      positions.length === 0
    ) {

      setError(
        "Create at least one position before collecting data."
      );

      return;

    }


    if (
      targetPresence === "yes"
    ) {

      if (
        selectedPositionId === null
      ) {

        setError(
          "Select the position where the target is located."
        );

        return;

      }


      if (!distanceCm) {

        setError(
          "Select a distance for a present target."
        );

        return;

      }

    }


    try {

      setError(null);

      setMessage(null);

      setPrediction(null);

      setFeatureSampleId(null);


      setCollectionState(
        "recording"
      );


      const recordingPromise =
        recordMicrophone(1300);


      const audioContext =
        new AudioContext({
          sampleRate: 48000
        });


      await new Promise<void>(
        resolve => {

          window.setTimeout(
            resolve,
            100
          );

        }
      );


      await playChirp(
        audioContext,
        DEFAULT_CHIRP_CONFIG
      );


      await audioContext.close();


      const recording =
        await recordingPromise;


      const wavBlob =
        audioBufferToWav(
          recording.audioBuffer
        );


      setCollectionState(
        "saving"
      );


      const sample =
        await createDatasetSample(
          wavBlob,
          {
            positionId:
              targetPresence === "yes"
                ? selectedPositionId
                : null,

            targetPresence,

            distanceCm:
              targetPresence === "yes"
                ? Number(distanceCm)
                : null,

            remarks
          }
        );


      setSamples(
        current => [
          sample,
          ...current
        ]
      );


      setFeatureSampleId(
        sample.id
      );


      setRemarks("");


      setCollectionState(
        "idle"
      );


      const updatedSummary =
        await getDatasetSummary();


      setSummary(
        updatedSummary
      );


      setMessage(
        `${sample.sample_code} saved successfully. Acoustic features extracted.`
      );

    } catch (err) {

      console.error(err);


      setCollectionState(
        "idle"
      );


      setError(
        err instanceof Error
          ? err.message
          : "Unable to record and save the sample."
      );

    }
  }


  /*
   * Predict a single sample and immediately
   * update both the prediction panel and table.
   */
  async function handlePredict(
    sample: DatasetSample
  ) {

    if (
      predictionSampleId !== null ||
      predictingAll
    ) {

      return;

    }


    try {

      setError(null);

      setMessage(null);

      setPrediction(null);


      setPredictionSampleId(
        sample.id
      );


      /*
       * The API correctly reads the backend's
       * top-level prediction response.
       */
      const result =
        await predictDatasetSample(
          sample.id
        );


      /*
       * Display the prediction immediately.
       */
      setPrediction(
        result
      );


      /*
       * Fetch the actual persisted sample.
       * This keeps the table synchronized with
       * dataset.db and avoids manually constructing
       * a DatasetSample object.
       */
      const updatedSample =
        await getDatasetSample(
          sample.id
        );


      setSamples(
        current =>
          current.map(
            item =>
              item.id ===
              updatedSample.id
                ? updatedSample
                : item
          )
        );


      /*
       * Refresh summary statistics.
       */
      const updatedSummary =
        await getDatasetSummary();


      setSummary(
        updatedSummary
      );


    } catch (err) {

      console.error(
        "Dataset prediction failed:",
        err
      );


      setPrediction(null);


      setError(
        err instanceof Error
          ? err.message
          : "Unable to predict the sample."
      );


    } finally {

      setPredictionSampleId(
        null
      );

    }
  }


  /*
   * Predict every labeled sample using the
   * backend's leave-one-out KNN evaluation.
   *
   * The backend persists the resulting prediction
   * for every sample, so after completion we reload
   * the samples and summary from dataset.db.
   */
  async function handlePredictAll() {

    if (
      predictingAll ||
      predictionSampleId !== null
    ) {

      return;

    }


    if (
      samples.length === 0
    ) {

      setError(
        "There are no recordings to predict."
      );

      return;

    }


    try {

      setError(null);

      setMessage(null);

      setPrediction(null);

      setPredictingAll(true);


      const result =
        await predictAllDatasetSamples();


      /*
       * Reload the complete dataset so every
       * prediction/evaluation shown in the UI
       * comes directly from dataset.db.
       */
      const [
        updatedSamples,
        updatedSummary
      ] = await Promise.all([

        getDatasetSamples(),

        getDatasetSummary()

      ]);


      setSamples(
        updatedSamples
      );

      setSummary(
        updatedSummary
      );


      const accuracyText =
        result.accuracy === null
          ? "—"
          : `${(
              result.accuracy * 100
            ).toFixed(2)}%`;


      setMessage(
        `Prediction complete: ${result.evaluated_samples} evaluated · ${result.correct_predictions} correct · ${result.incorrect_predictions} incorrect · ${accuracyText} accuracy.`
      );

    } catch (err) {

      console.error(
        "Bulk dataset prediction failed:",
        err
      );


      setError(
        err instanceof Error
          ? err.message
          : "Unable to predict all recordings."
      );

    } finally {

      setPredictingAll(
        false
      );

    }

  }


  async function handleDelete(
    sample: DatasetSample
  ) {

    if (
      predictingAll
    ) {

      return;

    }


    const confirmed =
      window.confirm(
        `Delete ${sample.sample_code}? This will permanently remove the sample and its WAV recording.`
      );


    if (!confirmed) {

      return;

    }


    try {

      setError(null);

      setMessage(null);


      await deleteDatasetSample(
        sample.id
      );


      setSamples(
        current =>
          current.filter(
            item =>
              item.id !== sample.id
          )
      );


      if (
        prediction?.sample_id ===
        sample.id
      ) {

        setPrediction(null);

      }


      if (
        featureSampleId ===
        sample.id
      ) {

        setFeatureSampleId(null);

      }


      const updatedSummary =
        await getDatasetSummary();


      setSummary(
        updatedSummary
      );


      setMessage(
        `${sample.sample_code} was deleted.`
      );

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to delete sample."
      );

    }
  }


  function beginEdit(
    sample: DatasetSample
  ) {

    if (
      predictingAll
    ) {

      return;

    }


    setEditing({

      sample,

      positionId:
        sample.position_id,

      targetPresence:
        sample.target_presence,

      distanceCm:
        sample.distance_cm === null
          ? ""
          : String(
              sample.distance_cm
            ),

      remarks:
        sample.remarks ?? ""

    });


    setError(null);

    setMessage(null);
  }


  async function handleSaveEdit() {

    if (!editing) {

      return;

    }


    if (
      predictingAll
    ) {

      return;

    }


    if (
      editing.targetPresence === "yes" &&
      editing.positionId === null
    ) {

      setError(
        "Select a position for a present target."
      );

      return;

    }


    if (
      editing.targetPresence === "yes" &&
      !editing.distanceCm
    ) {

      setError(
        "Select a distance for a present target."
      );

      return;

    }


    try {

      setError(null);

      setMessage(null);


      const updated =
        await updateDatasetSample(
          editing.sample.id,
          {
            positionId:
              editing.targetPresence ===
              "yes"
                ? editing.positionId
                : null,

            targetPresence:
              editing.targetPresence,

            distanceCm:
              editing.targetPresence ===
                "yes" &&
              editing.distanceCm
                ? Number(
                    editing.distanceCm
                  )
                : null,

            remarks:
              editing.remarks
          }
        );


      setSamples(
        current =>
          current.map(
            sample =>
              sample.id ===
              updated.id
                ? updated
                : sample
          )
      );


      if (
        prediction?.sample_id ===
        updated.id
      ) {

        setPrediction(null);

      }


      if (
        featureSampleId ===
        updated.id
      ) {

        setFeatureSampleId(
          updated.id
        );

      }


      setEditing(null);


      const updatedSummary =
        await getDatasetSummary();


      setSummary(
        updatedSummary
      );


      setMessage(
        `${updated.sample_code} was updated.`
      );

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to update sample."
      );

    }
  }


  function playSample(
    sample: DatasetSample
  ) {

    if (
      audioRef.current
    ) {

      audioRef.current.pause();

      audioRef.current = null;

    }


    const audio =
      new Audio(
        getDatasetSampleAudioUrl(
          sample.id
        )
      );


    audioRef.current =
      audio;


    setAudioPlayingId(
      sample.id
    );


    audio.onended = () => {

      setAudioPlayingId(
        null
      );

      audioRef.current =
        null;

    };


    audio.onerror = () => {

      setAudioPlayingId(
        null
      );

      audioRef.current =
        null;

      setError(
        "Unable to play this recording."
      );

    };


    void audio
      .play()
      .catch(() => {

        setAudioPlayingId(
          null
        );

        audioRef.current =
          null;

        setError(
          "Unable to play this recording."
        );

      });
  }


  function handleTargetChange(
    value: TargetPresence
  ) {

    setTargetPresence(
      value
    );


    if (
      value !== "yes"
    ) {

      setDistanceCm("");

    } else if (
      !distanceCm
    ) {

      setDistanceCm("15");

    }
  }


  const isRecording =
    collectionState ===
    "recording";


  const isSaving =
    collectionState ===
    "saving";


  const nearestSamples =
    prediction &&
    Array.isArray(
      prediction.nearest_samples
    )
      ? prediction.nearest_samples
      : [];


  const positionDistribution =
    summary
      ? Object.entries(
          summary.positions ?? {}
        )
      : [];


  const targetDistribution =
    summary
      ? Object.entries(
          summary.target_presence ?? {}
        ) as Array<
          [
            TargetPresence,
            number
          ]
        >
      : [];


  const distanceDistribution =
    summary
      ? Object.entries(
          summary.distances ?? {}
        )
      : [];


  return (
    <main className="collect-page">

      <section className="collect-hero">

        <div>

          <p className="eyebrow">
            Experimental dataset
          </p>

          <h1>
            Collect Data
          </h1>

          <p className="collect-description">
            Build the labeled acoustic
            fingerprint dataset used to
            evaluate position prediction.
          </p>

        </div>


        <div className="collect-hero-meta">

          <span>
            {summary?.total_samples ?? 0}
            {" "}
            samples
          </span>

          <span>
            {summary?.labeled_samples ?? 0}
            {" "}
            labeled
          </span>

        </div>

      </section>


      {error && (

        <div className="dataset-alert dataset-alert-error">

          <span>
            {error}
          </span>

          <button
            type="button"
            onClick={() =>
              setError(null)
            }
          >
            Dismiss
          </button>

        </div>

      )}


      {message && (

        <div className="dataset-alert dataset-alert-success">

          <span>
            {message}
          </span>

          <button
            type="button"
            onClick={() =>
              setMessage(null)
            }
          >
            Dismiss
          </button>

        </div>

      )}


      <section className="collect-grid">

        <div className="dataset-card collection-card">

          <div className="dataset-card-header">

            <div>

              <p className="section-kicker">
                01
              </p>

              <h2>
                Record sample
              </h2>

            </div>


            <span className="recording-status">

              {isRecording
                ? "Recording"
                : isSaving
                  ? "Saving"
                  : "Ready"}

            </span>

          </div>


          <div className="form-section">

            <label className="field-label">
              Position
            </label>


            <div className="position-create-row">

              <select
                value={
                  selectedPositionId ?? ""
                }
                onChange={
                  event =>
                    setSelectedPositionId(
                      event.target.value
                        ? Number(
                            event.target.value
                          )
                        : null
                    )
                }
                disabled={
                  isRecording ||
                  isSaving ||
                  predictingAll
                }
              >

                <option value="">
                  Select position
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


              <input
                type="text"
                value={
                  newPositionName
                }
                onChange={
                  event =>
                    setNewPositionName(
                      event.target.value
                    )
                }
                placeholder="New position"
                disabled={
                  isRecording ||
                  isSaving ||
                  predictingAll
                }
                onKeyDown={
                  event => {

                    if (
                      event.key ===
                      "Enter"
                    ) {

                      event.preventDefault();

                      void handleCreatePosition();

                    }

                  }
                }
              />


              <button
                type="button"
                className="secondary-button"
                onClick={() =>
                  void handleCreatePosition()
                }
                disabled={
                  isRecording ||
                  isSaving ||
                  predictingAll ||
                  !newPositionName.trim()
                }
              >
                Add
              </button>

            </div>


            {selectedPosition && (

              <p className="field-help">

                Recording location:{" "}

                <strong>
                  {
                    selectedPosition.name
                  }
                </strong>

              </p>

            )}

          </div>


          <div className="form-section">

            <label className="field-label">
              Target presence
            </label>


            <div className="segmented-control">

              {TARGET_OPTIONS.map(
                option => (

                  <button
                    key={
                      option.value
                    }
                    type="button"
                    className={
                      targetPresence ===
                      option.value
                        ? "active"
                        : ""
                    }
                    onClick={() =>
                      handleTargetChange(
                        option.value
                      )
                    }
                    disabled={
                      isRecording ||
                      isSaving ||
                      predictingAll
                    }
                  >
                    {
                      option.label
                    }
                  </button>

                )
              )}

            </div>

          </div>


          {targetPresence === "yes" && (

            <div className="form-section">

              <label className="field-label">
                Distance
              </label>


              <div className="distance-options">

                {DISTANCE_OPTIONS.map(
                  distance => (

                    <button
                      key={
                        distance
                      }
                      type="button"
                      className={
                        distanceCm ===
                        String(
                          distance
                        )
                          ? "active"
                          : ""
                      }
                      onClick={() =>
                        setDistanceCm(
                          String(
                            distance
                          )
                        )
                      }
                      disabled={
                        isRecording ||
                        isSaving ||
                        predictingAll
                      }
                    >
                      {
                        distance
                      }{" "}
                      cm
                    </button>

                  )
                )}

              </div>

            </div>

          )}


          <div className="form-section">

            <label
              className="field-label"
              htmlFor="dataset-remarks"
            >
              Remarks
            </label>


            <textarea
              id="dataset-remarks"
              value={
                remarks
              }
              onChange={
                event =>
                  setRemarks(
                    event.target.value
                  )
              }
              placeholder="Optional notes about the recording..."
              rows={3}
              disabled={
                isRecording ||
                isSaving ||
                predictingAll
              }
            />

          </div>


          <div className="record-action">

            <button
              type="button"
              className="primary-button record-button"
              onClick={() =>
                void handleCollectSample()
              }
              disabled={
                isRecording ||
                isSaving ||
                predictingAll ||
                positions.length === 0
              }
            >

              {isRecording
                ? "Recording…"
                : isSaving
                  ? "Saving…"
                  : "Play chirp & record"}

            </button>


            <p>
              The phone plays the controlled
              chirp and records the microphone
              response for approximately
              1.3 seconds.
            </p>

          </div>

        </div>


        <div className="dataset-card summary-card">

          <div className="dataset-card-header">

            <div>

              <p className="section-kicker">
                Dataset
              </p>

              <h2>
                Overview
              </h2>

            </div>

          </div>


          <div className="summary-metrics">

            <div>

              <span>
                Total
              </span>

              <strong>
                {
                  summary?.total_samples ??
                  0
                }
              </strong>

            </div>


            <div>

              <span>
                Labeled
              </span>

              <strong>
                {
                  summary?.labeled_samples ??
                  0
                }
              </strong>

            </div>


            <div>

              <span>
                Evaluated
              </span>

              <strong>
                {
                  summary?.evaluable_predictions ??
                  0
                }
              </strong>

            </div>


            <div>

              <span>
                Accuracy
              </span>

              <strong>
                {
                  formatConfidence(
                    summary?.accuracy
                  )
                }
              </strong>

            </div>

          </div>


          <div className="summary-section">

            <h3>
              By position
            </h3>


            {positionDistribution.length > 0 ? (

              <div className="distribution-list">

                {positionDistribution.map(
                  (
                    [
                      positionName,
                      count
                    ],
                    index
                  ) => (

                    <div
                      key={
                        `${positionName}-${index}`
                      }
                    >

                      <span>
                        {
                          positionName
                        }
                      </span>

                      <strong>
                        {
                          count
                        }
                      </strong>

                    </div>

                  )
                )}

              </div>

            ) : (

              <p className="empty-copy">
                No samples collected yet.
              </p>

            )}

          </div>


          <div className="summary-section">

            <h3>
              Target presence
            </h3>


            {targetDistribution.length > 0 ? (

              <div className="distribution-list">

                {targetDistribution.map(
                  (
                    [
                      target,
                      count
                    ]
                  ) => (

                    <div
                      key={
                        target
                      }
                    >

                      <span>
                        {
                          formatTarget(
                            target
                          )
                        }
                      </span>

                      <strong>
                        {
                          count
                        }
                      </strong>

                    </div>

                  )
                )}

              </div>

            ) : (

              <p className="empty-copy">
                No samples collected yet.
              </p>

            )}

          </div>


          <div className="summary-section">

            <h3>
              Distance
            </h3>


            {distanceDistribution.length > 0 ? (

              <div className="distribution-list">

                {distanceDistribution.map(
                  (
                    [
                      distance,
                      count
                    ]
                  ) => (

                    <div
                      key={
                        distance
                      }
                    >

                      <span>
                        {
                          distance
                        }{" "}
                        cm
                      </span>

                      <strong>
                        {
                          count
                        }
                      </strong>

                    </div>

                  )
                )}

              </div>

            ) : (

              <p className="empty-copy">
                No distance labels yet.
              </p>

            )}

          </div>

        </div>

      </section>


      {/* =====================================================
          DATASET ACTIONS
          ===================================================== */}

      <section className="dataset-card dataset-actions-card">

        <div className="dataset-card-header">

          <div>

            <p className="section-kicker">
              Dataset actions
            </p>

            <h2>
              Evaluate & export
            </h2>

          </div>

        </div>


        <div className="dataset-actions-content">

          <div className="dataset-action-primary">

            <div>

              <strong>
                Run position prediction
              </strong>

              <p>
                Evaluate every labeled recording
                using leave-one-out KNN and save
                the predictions to the dataset.
              </p>

            </div>


            <button
              type="button"
              className="primary-button"
              onClick={() =>
                void handlePredictAll()
              }
              disabled={
                predictingAll ||
                predictionSampleId !== null ||
                samples.length === 0
              }
            >

              {predictingAll
                ? "Predicting all…"
                : "Predict All Recordings"}

            </button>

          </div>


          <div className="dataset-export-actions">

            <div>

              <strong>
                Export dataset
              </strong>

              <p>
                Download the acoustic feature
                vectors and prediction results
                as CSV files.
              </p>

            </div>


            <div className="dataset-export-buttons">

              <a
                className="secondary-button"
                href={
                  getDatasetFeaturesCsvUrl()
                }
                download="dataset_features.csv"
              >
                Download Features CSV
              </a>


              <a
                className="secondary-button"
                href={
                  getDatasetPredictionsCsvUrl()
                }
                download="dataset_predictions.csv"
              >
                Download Predictions CSV
              </a>

            </div>

          </div>

        </div>

      </section>


      {featureSample && (

        <section className="dataset-card feature-card">

          <div className="dataset-card-header">

            <div>

              <p className="section-kicker">
                Acoustic analysis
              </p>

              <h2>
                Extracted Acoustic Fingerprint
              </h2>

              <p className="field-help">
                {
                  featureSample.sample_code
                }
                {" · "}
                {
                  featureSample.position_name ??
                  "No position"
                }
              </p>

            </div>


            <button
              type="button"
              className="text-button"
              onClick={() =>
                setFeatureSampleId(null)
              }
            >
              Close
            </button>

          </div>


          {featureEntries.length > 0 ? (

            <>

              <div className="feature-intro">

                <p>
                  These are the acoustic features
                  extracted from the recorded
                  microphone response. Together
                  they form the 12-dimensional
                  acoustic fingerprint used by
                  the current KNN baseline.
                </p>

              </div>


              <div className="feature-grid">

                {featureEntries.map(
                  feature => (

                    <div
                      className="feature-item"
                      key={
                        feature.key
                      }
                    >

                      <span>
                        {
                          feature.label
                        }
                      </span>

                      <strong>
                        {
                          formatFeatureValue(
                            feature.value
                          )
                        }
                      </strong>

                      <small>
                        {
                          feature.key
                        }
                      </small>

                    </div>

                  )
                )}

              </div>

            </>

          ) : (

            <div className="empty-dataset">

              <h3>
                Feature values are not available
              </h3>

              <p>
                The sample was saved successfully,
                but the backend response did not
                include the extracted feature object.
                The next step is to expose the stored
                features through the dataset API.
              </p>

            </div>

          )}

        </section>

      )}


      {prediction && (

        <section className="dataset-card prediction-card">

          <div className="dataset-card-header">

            <div>

              <p className="section-kicker">
                Prediction
              </p>

              <h2>

                {prediction.sample_id
                  ? `Sample ${
                      samples.find(
                        sample =>
                          sample.id ===
                          prediction.sample_id
                      )?.sample_code ??
                      ""
                    }`
                  : "Result"}

              </h2>

            </div>


            <button
              type="button"
              className="text-button"
              onClick={() =>
                setPrediction(null)
              }
            >
              Close
            </button>

          </div>


          <div className="prediction-main">

            <div className="prediction-result">

              <span>
                Predicted position
              </span>

              <strong>
                {
                  prediction.predicted_position_name ??
                  "Unknown"
                }
              </strong>

            </div>


            <div className="prediction-result">

              <span>
                Confidence
              </span>

              <strong>
                {
                  formatConfidence(
                    prediction.confidence
                  )
                }
              </strong>

            </div>


            <div className="prediction-result">

              <span>
                Ground truth
              </span>

              <strong>
                {
                  prediction.ground_truth_position_name ??
                  "Unknown"
                }
              </strong>

            </div>


            <div className="prediction-result">

              <span>
                Evaluation
              </span>

              <strong
                className={
                  `evaluation-${prediction.evaluation ?? "not_evaluable"}`
                }
              >
                {
                  formatEvaluation(
                    prediction.evaluation
                  )
                }
              </strong>

            </div>

          </div>


          <div className="nearest-section">

            <div>

              <p className="section-kicker">
                Reference comparison
              </p>

              <h3>
                Nearest fingerprints
              </h3>

            </div>


            {nearestSamples.length > 0 ? (

              <div className="nearest-table">

                {
                  nearestSamples.map(
                    (
                      nearest,
                      index
                    ) => (

                      <div
                        className="nearest-row"
                        key={
                          `${nearest.sample_id}-${index}`
                        }
                      >

                        <span>
                          {
                            index + 1
                          }
                        </span>

                        <strong>
                          {
                            nearest.sample_code ??
                            "Unknown"
                          }
                        </strong>

                        <span>
                          {
                            nearest.position_name ??
                            "Unknown"
                          }
                        </span>

                        <span>
                          distance{" "}
                          {
                            formatDistance(
                              nearest.distance
                            )
                          }
                        </span>

                      </div>

                    )
                  )
                }

              </div>

            ) : (

              <p className="empty-copy">
                No reference samples were
                available.
              </p>

            )}

          </div>

        </section>

      )}


      <section className="dataset-card samples-card">

        <div className="dataset-card-header">

          <div>

            <p className="section-kicker">
              02
            </p>

            <h2>
              Collected samples
            </h2>

          </div>


          <span className="sample-count">

            {samples.length}{" "}

            {
              samples.length === 1
                ? "sample"
                : "samples"
            }

          </span>

        </div>


        {samples.length === 0 ? (

          <div className="empty-dataset">

            <h3>
              No samples collected
            </h3>

            <p>
              Create a position and record
              the first acoustic response
              above.
            </p>

          </div>

        ) : (

          <div className="dataset-table-wrapper">

            <table className="dataset-table">

              <thead>

                <tr>

                  <th>
                    ID
                  </th>

                  <th>
                    Position
                  </th>

                  <th>
                    Target
                  </th>

                  <th>
                    Distance
                  </th>

                  <th>
                    Prediction
                  </th>

                  <th>
                    Evaluation
                  </th>

                  <th>
                    Actions
                  </th>

                </tr>

              </thead>


              <tbody>

                {samples.map(
                  sample => (

                    <tr
                      key={
                        sample.id
                      }
                    >

                      <td>

                        <strong>
                          {
                            sample.sample_code
                          }
                        </strong>

                        <small>
                          {
                            formatDate(
                              sample.timestamp
                            )
                          }
                        </small>

                      </td>


                      <td>
                        {
                          sample.position_name ??
                          "—"
                        }
                      </td>


                      <td>
                        {
                          formatTarget(
                            sample.target_presence
                          )
                        }
                      </td>


                      <td>

                        {
                          sample.distance_cm ===
                          null

                            ? "—"

                            : `${sample.distance_cm} cm`
                        }

                      </td>


                      <td>

                        <div className="prediction-cell">

                          <span>
                            {
                              sample.predicted_position_name ??
                              "—"
                            }
                          </span>


                          {typeof sample.prediction_confidence ===
                            "number" && (

                            <small>
                              {
                                formatConfidence(
                                  sample.prediction_confidence
                                )
                              }
                            </small>

                          )}

                        </div>

                      </td>


                      <td>

                        {sample.prediction_evaluation ===
                        "correct" ? (

                          <span className="evaluation-badge evaluation-badge-correct">
                            Correct
                          </span>

                        ) : sample.prediction_evaluation ===
                          "incorrect" ? (

                          <span className="evaluation-badge evaluation-badge-incorrect">
                            Incorrect
                          </span>

                        ) : (

                          <span className="evaluation-badge">
                            —
                          </span>

                        )}

                      </td>


                      <td>

                        <div className="table-actions">

                          <button
                            type="button"
                            className="table-button"
                            onClick={() =>
                              playSample(
                                sample
                              )
                            }
                            disabled={
                              predictingAll
                            }
                          >

                            {
                              audioPlayingId ===
                              sample.id

                                ? "Playing…"

                                : "Play"
                            }

                          </button>


                          <button
                            type="button"
                            className="table-button"
                            onClick={() =>
                              setFeatureSampleId(
                                sample.id
                              )
                            }
                            disabled={
                              predictingAll
                            }
                          >
                            Features
                          </button>


                          <button
                            type="button"
                            className="table-button"
                            onClick={() =>
                              void handlePredict(
                                sample
                              )
                            }
                            disabled={
                              predictionSampleId !==
                                null ||
                              predictingAll
                            }
                          >

                            {
                              predictionSampleId ===
                              sample.id

                                ? "Predicting…"

                                : "Predict"
                            }

                          </button>


                          <button
                            type="button"
                            className="table-button"
                            onClick={() =>
                              beginEdit(
                                sample
                              )
                            }
                            disabled={
                              predictingAll
                            }
                          >
                            Edit
                          </button>


                          <button
                            type="button"
                            className="table-button table-button-danger"
                            onClick={() =>
                              void handleDelete(
                                sample
                              )
                            }
                            disabled={
                              predictingAll
                            }
                          >
                            Delete
                          </button>

                        </div>

                      </td>

                    </tr>

                  )
                )}

              </tbody>

            </table>

          </div>

        )}

      </section>


      {editing && (

        <div className="modal-backdrop">

          <div className="dataset-modal">

            <div className="dataset-card-header">

              <div>

                <p className="section-kicker">
                  Edit
                </p>

                <h2>
                  {
                    editing.sample.sample_code
                  }
                </h2>

              </div>


              <button
                type="button"
                className="text-button"
                onClick={() =>
                  setEditing(null)
                }
              >
                Close
              </button>

            </div>


            <div className="form-section">

              <label className="field-label">
                Position
              </label>


              <select
                value={
                  editing.positionId ??
                  ""
                }
                onChange={
                  event =>
                    setEditing(
                      current =>
                        current
                          ? {
                              ...current,

                              positionId:
                                event.target
                                  .value
                                  ? Number(
                                      event.target
                                        .value
                                    )
                                  : null
                            }
                          : current
                    )
                }
                disabled={
                  editing.targetPresence !==
                  "yes"
                }
              >

                <option value="">
                  Select position
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

            </div>


            <div className="form-section">

              <label className="field-label">
                Target presence
              </label>


              <div className="segmented-control">

                {TARGET_OPTIONS.map(
                  option => (

                    <button
                      key={
                        option.value
                      }
                      type="button"
                      className={
                        editing.targetPresence ===
                        option.value
                          ? "active"
                          : ""
                      }
                      onClick={() =>
                        setEditing(
                          current =>
                            current
                              ? {
                                  ...current,

                                  targetPresence:
                                    option.value,

                                  distanceCm:
                                    option.value ===
                                    "yes"

                                      ? current.distanceCm ||
                                        "15"

                                      : ""
                                }
                              : current
                        )
                      }
                    >
                      {
                        option.label
                      }
                    </button>

                  )
                )}

              </div>

            </div>


            {editing.targetPresence ===
              "yes" && (

              <div className="form-section">

                <label className="field-label">
                  Distance
                </label>


                <div className="distance-options">

                  {DISTANCE_OPTIONS.map(
                    distance => (

                      <button
                        key={
                          distance
                        }
                        type="button"
                        className={
                          editing.distanceCm ===
                          String(
                            distance
                          )
                            ? "active"
                            : ""
                        }
                        onClick={() =>
                          setEditing(
                            current =>
                              current
                                ? {
                                    ...current,

                                    distanceCm:
                                      String(
                                        distance
                                      )
                                  }
                                : current
                          )
                        }
                      >
                        {
                          distance
                        }{" "}
                        cm
                      </button>

                    )
                  )}

                </div>

              </div>

            )}


            <div className="form-section">

              <label className="field-label">
                Remarks
              </label>


              <textarea
                value={
                  editing.remarks
                }
                onChange={
                  event =>
                    setEditing(
                      current =>
                        current
                          ? {
                              ...current,

                              remarks:
                                event.target
                                  .value
                            }
                          : current
                    )
                }
                rows={4}
              />

            </div>


            <div className="modal-actions">

              <button
                type="button"
                className="secondary-button"
                onClick={() =>
                  setEditing(null)
                }
              >
                Cancel
              </button>


              <button
                type="button"
                className="primary-button"
                onClick={() =>
                  void handleSaveEdit()
                }
              >
                Save changes
              </button>

            </div>

          </div>

        </div>

      )}

    </main>
  );
}