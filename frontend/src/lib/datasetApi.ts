/*
 * ============================================================
 * DATASET API
 * ============================================================
 *
 * Experiment-scoped acoustic dataset API.
 *
 * Important design rule:
 *
 * Every dataset operation is scoped by experiment_id.
 *
 * EXP-001 data must never be used when EXP-002 is selected.
 */

const API_BASE =
  import.meta.env.VITE_API_BASE_URL

const DATASET_BASE =
  `${API_BASE}/api/dataset`;

const EXPERIMENT_BASE =
  `${API_BASE}/api/experiments`;


/* ============================================================
   TYPES
   ============================================================ */

export type TargetPresence =
  | "yes"
  | "no"
  | "cant_say";


export interface DatasetPosition {
  id: number;
  name: string;
  experiment_id?: number | null;
  created_at?: string | null;
}


export interface DatasetSample {
  id: number;

  sample_code: string;

  timestamp: string;

  experiment_id?: number | null;

  position_id?: number | null;

  position_name?: string | null;

  target_presence: TargetPresence;

  distance_cm?: number | null;

  remarks?: string | null;

  recording_filename?: string | null;

  recording_path?: string | null;

  predicted_position_id?: number | null;

  predicted_position_name?: string | null;

  prediction_confidence?: number | null;

  prediction_evaluation?:
    | "correct"
    | "incorrect"
    | "not_evaluable"
    | string
    | null;

  prediction_timestamp?: string | null;

  features?: Record<string, unknown> | null;

  acoustic_features?: Record<string, unknown> | null;

  [key: string]: unknown;
}


export interface DatasetSummary {
  total_samples: number;

  labeled_samples: number;

  evaluable_predictions: number;

  correct_predictions: number;

  incorrect_predictions: number;

  accuracy: number | null;

  positions: Record<string, number>;

  target_presence: Record<string, number>;

  distances: Record<string, number>;
}


export interface Experiment {
  id: number;

  name: string;

  description?: string | null;

  created_at: string;
}


export interface ExperimentStats {
  experiment_id: number;

  experiment_name?: string | null;

  total_samples: number;

  total_positions: number;

  completed_predictions?: number | null;

  correct_predictions?: number | null;

  incorrect_predictions?: number | null;

  unclassified_predictions?: number | null;
}


export interface CreateExperimentRequest {
  name: string;

  description?: string;
}


export interface CreatePositionRequest {
  name: string;
}


export interface DatasetSampleFilters {
  experiment_id?: number;
}


export interface SaveSampleData {
  experiment_id?: number;

  experimentId?: number;

  position_id?: number | null;

  positionId?: number | null;

  target_presence?: TargetPresence;

  targetPresence?: TargetPresence;

  distance_cm?: number | null;

  distanceCm?: number | null;

  remarks?: string;
}


export interface NearestSample {
  sample_id: number;

  sample_code?: string | null;

  position_id?: number | null;

  position_name?: string | null;

  distance: number;
}


export interface PredictionResult {
  sample_id?: number | null;

  predicted_position_id?: number | null;

  predicted_position_name?: string | null;

  confidence?: number | null;

  ground_truth_position_id?: number | null;

  ground_truth_position_name?: string | null;

  evaluation?:
    | "correct"
    | "incorrect"
    | "not_evaluable"
    | string
    | null;

  nearest_samples: NearestSample[];

  [key: string]: unknown;
}


export interface PredictAllResult {
  experiment_id?: number;

  total_samples?: number;

  evaluated_samples: number;

  skipped_samples?: number;

  correct_predictions: number;

  incorrect_predictions: number;

  accuracy: number | null;

  [key: string]: unknown;
}


/* ============================================================
   RESPONSE HELPERS
   ============================================================ */

async function parseResponse<T>(
  response: Response
): Promise<T> {

  if (!response.ok) {

    let message =
      `Request failed with status ${response.status}`;

    try {

      const data =
        await response.json();

      if (
        typeof data?.detail ===
        "string"
      ) {
        message =
          data.detail;
      } else if (
        typeof data?.message ===
        "string"
      ) {
        message =
          data.message;
      }

    } catch {
      /* Ignore malformed error response. */
    }

    throw new Error(message);
  }

  return response.json();
}


/* ============================================================
   GENERIC UNWRAPPERS
   ============================================================ */

function unwrapObject<T>(
  data: unknown,
  key: string
): T {

  if (
    data &&
    typeof data === "object" &&
    key in data
  ) {

    const value =
      (data as Record<string, unknown>)[
        key
      ];

    return value as T;
  }

  return data as T;
}


/* ============================================================
   EXPERIMENT API
   ============================================================ */

export async function getExperiments(): Promise<Experiment[]> {
  const response = await fetch(`${EXPERIMENT_BASE}`);

  const data = await parseResponse<
    | Experiment[]
    | {
        value?: Experiment[];
        experiments?: Experiment[];
        Count?: number;
      }
  >(response);

  if (Array.isArray(data)) {
    return data;
  }

  return data.value ?? data.experiments ?? [];
}


export async function getExperiment(
  experimentId: number
): Promise<Experiment> {

  const response =
    await fetch(
      `${EXPERIMENT_BASE}/${experimentId}`
    );

  const data =
    await parseResponse<unknown>(
      response
    );

  return unwrapObject<Experiment>(
    data,
    "experiment"
  );
}


export async function createExperiment(
  data: CreateExperimentRequest
): Promise<Experiment> {

  const response =
    await fetch(
      `${EXPERIMENT_BASE}`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",
        },

        body:
          JSON.stringify(data),
      }
    );

  const result =
    await parseResponse<unknown>(
      response
    );

  return unwrapObject<Experiment>(
    result,
    "experiment"
  );
}


export async function getExperimentStats(
  experimentId: number
): Promise<ExperimentStats> {

  const response =
    await fetch(
      `${EXPERIMENT_BASE}/${experimentId}/stats`
    );

  const data =
    await parseResponse<unknown>(
      response
    );

  return unwrapObject<ExperimentStats>(
    data,
    "stats"
  );
}


/* ============================================================
   EXPERIMENT POSITIONS
   ============================================================ */

/*
 * We first try the experiment API.
 *
 * If that endpoint is unavailable or returns no positions,
 * we fall back to the dataset-scoped endpoint:
 *
 * /api/dataset/positions?experiment_id=X
 *
 * This is important because the dataset router already
 * explicitly scopes positions by experiment.
 */

export async function getExperimentPositions(
  experimentId: number
): Promise<DatasetPosition[]> {

  let experimentError:
    | unknown
    | null = null;

  try {

    const response =
      await fetch(
        `${EXPERIMENT_BASE}/${experimentId}/positions`
      );

    if (response.ok) {

      const data =
        await parseResponse<unknown>(
          response
        );

      const positions =
        extractPositions(data);

      if (
        positions.length > 0
      ) {
        return positions;
      }
    }

  } catch (error) {

    experimentError =
      error;
  }


  /*
   * Fallback to dataset API.
   */

  try {

    const response =
      await fetch(
        `${DATASET_BASE}/positions?experiment_id=${experimentId}`
      );

    const data =
      await parseResponse<unknown>(
        response
      );

    const positions =
      extractPositions(data);

    return positions;

  } catch (datasetError) {

    if (experimentError) {
      throw experimentError;
    }

    throw datasetError;
  }
}


function extractPositions(
  data: unknown
): DatasetPosition[] {

  if (
    Array.isArray(data)
  ) {
    return data as DatasetPosition[];
  }

  if (
    data &&
    typeof data === "object"
  ) {

    const object =
      data as Record<
        string,
        unknown
      >;

    if (
      Array.isArray(
        object.positions
      )
    ) {
      return object.positions as DatasetPosition[];
    }

    if (
      Array.isArray(
        object.value
      )
    ) {
      return object.value as DatasetPosition[];
    }
  }

  return [];
}


/* ============================================================
   CREATE POSITION
   ============================================================ */

export async function createExperimentPosition(
  experimentId: number,

  data: CreatePositionRequest
): Promise<DatasetPosition> {

  /*
   * Use the dataset endpoint because it explicitly accepts
   * experiment_id and returns experiment-scoped positions.
   */

  const response =
    await fetch(
      `${DATASET_BASE}/positions?experiment_id=${experimentId}`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",
        },

        body:
          JSON.stringify(data),
      }
    );

  const result =
    await parseResponse<unknown>(
      response
    );

  return unwrapObject<DatasetPosition>(
    result,
    "position"
  );
}


/* ============================================================
   POSITION API
   ============================================================ */

export async function getPositions(
  experimentId = 1
): Promise<DatasetPosition[]> {

  return getExperimentPositions(
    experimentId
  );
}


export async function createPosition(
  name: string,

  experimentId = 1
): Promise<DatasetPosition> {

  return createExperimentPosition(
    experimentId,
    { name }
  );
}


/* ============================================================
   SAMPLE API
   ============================================================ */

export async function getSamples(
  experimentId = 1
): Promise<DatasetSample[]> {

  const response =
    await fetch(
      `${DATASET_BASE}/samples?experiment_id=${experimentId}`
    );

  const data =
    await parseResponse<unknown>(
      response
    );

  if (
    Array.isArray(data)
  ) {
    return data as DatasetSample[];
  }

  if (
    data &&
    typeof data === "object"
  ) {

    const object =
      data as Record<
        string,
        unknown
      >;

    if (
      Array.isArray(
        object.samples
      )
    ) {
      return object.samples as DatasetSample[];
    }

    if (
      Array.isArray(
        object.value
      )
    ) {
      return object.value as DatasetSample[];
    }
  }

  return [];
}


export async function getSample(
  sampleId: number,

  experimentId = 1
): Promise<DatasetSample> {

  const response =
    await fetch(
      `${DATASET_BASE}/samples/${sampleId}?experiment_id=${experimentId}`
    );

  const data =
    await parseResponse<unknown>(
      response
    );

  return unwrapObject<DatasetSample>(
    data,
    "sample"
  );
}


/* ============================================================
   CREATE SAMPLE
   ============================================================ */

export async function createSample(
  audioBlob: Blob,

  data: SaveSampleData
): Promise<DatasetSample> {

  const formData =
    new FormData();


  const experimentId =
    data.experiment_id ??
    data.experimentId;


  const positionId =
    data.position_id ??
    data.positionId ??
    null;


  const targetPresence =
    data.target_presence ??
    data.targetPresence ??
    "cant_say";


  const distanceCm =
    data.distance_cm ??
    data.distanceCm ??
    null;


  formData.append(
    "audio",
    audioBlob,
    `recording_${Date.now()}.wav`
  );


  if (
    positionId !== null &&
    positionId !== undefined
  ) {

    formData.append(
      "position_id",
      String(positionId)
    );
  }


  formData.append(
    "target_presence",
    targetPresence
  );


  if (
    distanceCm !== null &&
    distanceCm !== undefined
  ) {

    formData.append(
      "distance_cm",
      String(distanceCm)
    );
  }


  if (
    data.remarks?.trim()
  ) {

    formData.append(
      "remarks",
      data.remarks.trim()
    );
  }


  if (
    experimentId !== null &&
    experimentId !== undefined
  ) {

    formData.append(
      "experiment_id",
      String(experimentId)
    );
  }


  const response =
    await fetch(
      `${DATASET_BASE}/samples`,
      {
        method: "POST",

        body:
          formData,
      }
    );


  const result =
    await parseResponse<unknown>(
      response
    );


  return unwrapObject<DatasetSample>(
    result,
    "sample"
  );
}


/* ============================================================
   UPDATE SAMPLE
   ============================================================ */

export async function updateSample(
  sampleId: number,

  data: {
    position_id?: number | null;

    target_presence?:
      TargetPresence;

    distance_cm?: number | null;

    remarks?: string;

    positionId?: number | null;

    targetPresence?:
      TargetPresence;

    distanceCm?: number | null;
  },

  experimentId = 1
): Promise<DatasetSample> {

  const positionId =
    data.position_id ??
    data.positionId;


  const targetPresence =
    data.target_presence ??
    data.targetPresence;


  const distanceCm =
    data.distance_cm ??
    data.distanceCm;


  const payload:
    Record<string, unknown> = {};


  if (
    positionId !== undefined
  ) {

    payload.position_id =
      positionId;
  }


  if (
    targetPresence !== undefined
  ) {

    payload.target_presence =
      targetPresence;
  }


  if (
    distanceCm !== undefined
  ) {

    payload.distance_cm =
      distanceCm;
  }


  if (
    data.remarks !== undefined
  ) {

    payload.remarks =
      data.remarks;
  }


  /*
   * Backend uses PATCH.
   */

  const response =
    await fetch(
      `${DATASET_BASE}/samples/${sampleId}?experiment_id=${experimentId}`,
      {
        method: "PATCH",

        headers: {
          "Content-Type":
            "application/json",
        },

        body:
          JSON.stringify(payload),
      }
    );


  const result =
    await parseResponse<unknown>(
      response
    );


  return unwrapObject<DatasetSample>(
    result,
    "sample"
  );
}


/* ============================================================
   DELETE SAMPLE
   ============================================================ */

export async function deleteSample(
  sampleId: number,

  experimentId = 1
): Promise<void> {

  const response =
    await fetch(
      `${DATASET_BASE}/samples/${sampleId}?experiment_id=${experimentId}`,
      {
        method: "DELETE",
      }
    );


  await parseResponse<unknown>(
    response
  );
}


/* ============================================================
   AUDIO
   ============================================================ */

export function getSampleAudioUrl(
  sampleId: number,

  experimentId = 1
): string {

  return (
    `${DATASET_BASE}/samples/${sampleId}/audio` +
    `?experiment_id=${experimentId}`
  );
}


/* ============================================================
   PREDICTION
   ============================================================ */

export async function predictSample(
  sampleId: number,

  experimentId = 1
): Promise<PredictionResult> {

  const response =
    await fetch(
      `${DATASET_BASE}/samples/${sampleId}/predict?experiment_id=${experimentId}`,
      {
        method: "POST",
      }
    );


  return parseResponse<PredictionResult>(
    response
  );
}


export async function predictAllSamples(
  experimentId = 1
): Promise<PredictAllResult> {

  const response =
    await fetch(
      `${DATASET_BASE}/samples/predict-all?experiment_id=${experimentId}`,
      {
        method: "POST",
      }
    );


  return parseResponse<PredictAllResult>(
    response
  );
}


/* ============================================================
   SUMMARY
   ============================================================ */

export async function getDatasetSummary(
  experimentId = 1
): Promise<DatasetSummary> {

  const response =
    await fetch(
      `${DATASET_BASE}/summary?experiment_id=${experimentId}`
    );


  const data =
    await parseResponse<unknown>(
      response
    );


  return unwrapObject<DatasetSummary>(
    data,
    "summary"
  );
}


/* ============================================================
   CSV
   ============================================================ */

export function getFeaturesCsvUrl(
  experimentId = 1
): string {

  return (
    `${DATASET_BASE}/export/features` +
    `?experiment_id=${experimentId}`
  );
}


export function getPredictionsCsvUrl(
  experimentId = 1
): string {

  return (
    `${DATASET_BASE}/export/predictions` +
    `?experiment_id=${experimentId}`
  );
}


export async function downloadFeaturesCsv(
  experimentId = 1
): Promise<void> {

  const response =
    await fetch(
      getFeaturesCsvUrl(
        experimentId
      )
    );


  if (!response.ok) {

    throw new Error(
      "Failed to download feature CSV"
    );
  }


  const blob =
    await response.blob();


  const url =
    window.URL.createObjectURL(
      blob
    );


  const link =
    document.createElement(
      "a"
    );


  link.href =
    url;

  link.download =
    `dataset_features_EXP-${String(
      experimentId
    ).padStart(3, "0")}.csv`;


  document.body.appendChild(
    link
  );

  link.click();

  link.remove();

  window.URL.revokeObjectURL(
    url
  );
}


export async function downloadPredictionsCsv(
  experimentId = 1
): Promise<void> {

  const response =
    await fetch(
      getPredictionsCsvUrl(
        experimentId
      )
    );


  if (!response.ok) {

    throw new Error(
      "Failed to download prediction CSV"
    );
  }


  const blob =
    await response.blob();


  const url =
    window.URL.createObjectURL(
      blob
    );


  const link =
    document.createElement(
      "a"
    );


  link.href =
    url;

  link.download =
    `dataset_predictions_EXP-${String(
      experimentId
    ).padStart(3, "0")}.csv`;


  document.body.appendChild(
    link
  );

  link.click();

  link.remove();

  window.URL.revokeObjectURL(
    url
  );
}


/* ============================================================
   BACKWARD COMPATIBILITY
   ============================================================ */

export const getDatasetPositions =
  getPositions;

export const createDatasetPosition =
  createPosition;

export const getDatasetSamples =
  getSamples;

export const getDatasetSample =
  getSample;

export const createDatasetSample =
  createSample;

export const updateDatasetSample =
  updateSample;

export const deleteDatasetSample =
  deleteSample;

export const getDatasetSampleAudioUrl =
  getSampleAudioUrl;

export const predictDatasetSample =
  predictSample;

export const predictAllDatasetSamples =
  predictAllSamples;

export const getDatasetFeaturesCsvUrl =
  getFeaturesCsvUrl;

export const getDatasetPredictionsCsvUrl =
  getPredictionsCsvUrl;

export const downloadDatasetFeaturesCsv =
  downloadFeaturesCsv;

export const downloadDatasetPredictionsCsv =
  downloadPredictionsCsv;