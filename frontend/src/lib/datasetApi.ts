const API_BASE_URL =
  "https://life-leonard-greensboro-rabbit.trycloudflare.com";


export type TargetPresence =
  | "yes"
  | "no"
  | "cant_say";


export type PredictionEvaluation =
  | "correct"
  | "incorrect"
  | "not_evaluable";


export interface DatasetPosition {

  id: number;

  name: string;

  position_number: number;

  created_at: string;

}


export interface DatasetSample {

  id: number;

  sample_code: string;

  timestamp: string;

  recording_filename: string;

  position_id: number | null;

  position_name: string | null;

  target_presence: TargetPresence;

  distance_cm: number | null;

  remarks: string | null;

  features: Record<string, number>;

  duration_seconds: number;

  sample_rate: number;

  predicted_position_id:
    | number
    | null;

  predicted_position_name:
    | string
    | null;

  prediction_confidence:
    | number
    | null;

  prediction_evaluation:
    | PredictionEvaluation
    | null;

  prediction_timestamp:
    | string
    | null;

}


export interface NearestSample {

  sample_id: number;

  sample_code: string;

  position_id?: number;

  position_name: string | null;

  distance: number;

}


export interface PredictionResult {

  sample_id: number;

  predicted_position_id:
    | number
    | null;

  predicted_position_name:
    | string
    | null;

  confidence:
    | number
    | null;

  ground_truth_position_id:
    | number
    | null;

  ground_truth_position_name:
    | string
    | null;

  evaluation:
    PredictionEvaluation;

  nearest_samples:
    NearestSample[];

}


/* =======================================================
   BULK PREDICTION
   ======================================================= */

export interface PredictAllResult {

  total_samples: number;

  evaluated_samples: number;

  skipped_samples: number;

  correct_predictions: number;

  incorrect_predictions: number;

  accuracy: number | null;

  results: Array<{

    sample_id: number;

    sample_code: string;

    ground_truth_position_id:
      number | null;

    ground_truth_position_name:
      string | null;

    predicted_position_id:
      number | null;

    predicted_position_name:
      string | null;

    confidence:
      number | null;

    evaluation:
      PredictionEvaluation;

  }>;

}


export interface DatasetSummary {

  total_samples: number;

  labeled_samples: number;

  evaluable_predictions: number;

  correct_predictions: number;

  incorrect_predictions: number;

  accuracy: number | null;

  positions: Record<string, number>;

  target_presence: Record<
    TargetPresence,
    number
  >;

  distances: Record<
    string,
    number
  >;

}


interface ApiResponse<T> {

  success: boolean;

  message?: string;

  [key: string]: unknown;

}


async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {

  const response =
    await fetch(
      `${API_BASE_URL}${path}`,
      options
    );


  let payload:
    ApiResponse<T> | null = null;


  try {

    payload =
      await response.json();

  } catch {

    throw new Error(
      `Server returned an invalid response (${response.status}).`
    );

  }


  if (
    !response.ok ||
    payload === null ||
    !payload.success
  ) {

    throw new Error(
      payload?.message ||
      `Request failed with status ${response.status}.`
    );

  }


  return payload as T;

}


/* =======================================================
   POSITIONS
   ======================================================= */

export async function getDatasetPositions():
  Promise<DatasetPosition[]> {

  const response =
    await request<{
      positions:
        DatasetPosition[];
    }>(
      "/api/dataset/positions"
    );


  return Array.isArray(
    response.positions
  )
    ? response.positions
    : [];

}


export async function createDatasetPosition(
  name: string
): Promise<DatasetPosition> {

  const response =
    await request<{
      position:
        DatasetPosition;
    }>(
      "/api/dataset/positions",
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json"
        },

        body: JSON.stringify({
          name
        })
      }
    );


  if (
    !response.position
  ) {

    throw new Error(
      "Server did not return the created position."
    );

  }


  return response.position;

}


/* =======================================================
   SAMPLES
   ======================================================= */

export async function getDatasetSamples():
  Promise<DatasetSample[]> {

  const response =
    await request<{
      samples:
        DatasetSample[];
    }>(
      "/api/dataset/samples"
    );


  return Array.isArray(
    response.samples
  )
    ? response.samples
    : [];

}


export async function getDatasetSample(
  id: number
): Promise<DatasetSample> {

  const response =
    await request<{
      sample:
        DatasetSample;
    }>(
      `/api/dataset/samples/${id}`
    );


  if (
    !response.sample
  ) {

    throw new Error(
      "Server did not return the requested dataset sample."
    );

  }


  return response.sample;

}


export async function createDatasetSample(
  audio: Blob,
  options: {
    positionId: number | null;

    targetPresence:
      TargetPresence;

    distanceCm: number | null;

    remarks: string;
  }
): Promise<DatasetSample> {

  const formData =
    new FormData();


  formData.append(
    "audio",
    audio,
    "recording.wav"
  );


  if (
    options.positionId !== null
  ) {

    formData.append(
      "position_id",
      String(
        options.positionId
      )
    );

  }


  formData.append(
    "target_presence",
    options.targetPresence
  );


  if (
    options.distanceCm !== null
  ) {

    formData.append(
      "distance_cm",
      String(
        options.distanceCm
      )
    );

  }


  if (
    options.remarks.trim()
  ) {

    formData.append(
      "remarks",
      options.remarks.trim()
    );

  }


  const response =
    await request<{
      sample:
        DatasetSample;
    }>(
      "/api/dataset/samples",
      {
        method: "POST",

        body: formData
      }
    );


  if (
    !response.sample
  ) {

    throw new Error(
      "Server did not return the created dataset sample."
    );

  }


  return response.sample;

}


export async function updateDatasetSample(
  id: number,
  options: {
    positionId: number | null;

    targetPresence:
      TargetPresence;

    distanceCm: number | null;

    remarks: string;
  }
): Promise<DatasetSample> {

  const response =
    await request<{
      sample:
        DatasetSample;
    }>(
      `/api/dataset/samples/${id}`,
      {
        method: "PATCH",

        headers: {
          "Content-Type":
            "application/json"
        },

        body: JSON.stringify({

          position_id:
            options.positionId,

          target_presence:
            options.targetPresence,

          distance_cm:
            options.distanceCm,

          remarks:
            options.remarks.trim() ||
            null

        })
      }
    );


  if (
    !response.sample
  ) {

    throw new Error(
      "Server did not return the updated dataset sample."
    );

  }


  return response.sample;

}


export async function deleteDatasetSample(
  id: number
): Promise<void> {

  await request<unknown>(
    `/api/dataset/samples/${id}`,
    {
      method: "DELETE"
    }
  );

}


/* =======================================================
   PREDICTION
   ======================================================= */

export async function predictDatasetSample(
  id: number
): Promise<PredictionResult> {

  const response =
    await request<
      PredictionResult
    >(
      `/api/dataset/samples/${id}/predict`,
      {
        method: "POST"
      }
    );


  if (
    typeof response.sample_id !==
    "number"
  ) {

    throw new Error(
      "Server did not return a valid prediction sample ID."
    );

  }


  if (
    !Array.isArray(
      response.nearest_samples
    )
  ) {

    throw new Error(
      "Server did not return nearest fingerprint results."
    );

  }


  return {

    sample_id:
      response.sample_id,

    predicted_position_id:
      response.predicted_position_id ??
      null,

    predicted_position_name:
      response.predicted_position_name ??
      null,

    confidence:
      typeof response.confidence ===
      "number"
        ? response.confidence
        : null,

    ground_truth_position_id:
      response.ground_truth_position_id ??
      null,

    ground_truth_position_name:
      response.ground_truth_position_name ??
      null,

    evaluation:
      response.evaluation ??
      "not_evaluable",

    nearest_samples:
      response.nearest_samples

  };

}


/* =======================================================
   PREDICT ALL
   ======================================================= */

export async function predictAllDatasetSamples():
  Promise<PredictAllResult> {

  const response =
    await request<
      PredictAllResult
    >(
      "/api/dataset/samples/predict-all",
      {
        method: "POST"
      }
    );


  return {

    total_samples:
      typeof response.total_samples ===
      "number"
        ? response.total_samples
        : 0,

    evaluated_samples:
      typeof response.evaluated_samples ===
      "number"
        ? response.evaluated_samples
        : 0,

    skipped_samples:
      typeof response.skipped_samples ===
      "number"
        ? response.skipped_samples
        : 0,

    correct_predictions:
      typeof response.correct_predictions ===
      "number"
        ? response.correct_predictions
        : 0,

    incorrect_predictions:
      typeof response.incorrect_predictions ===
      "number"
        ? response.incorrect_predictions
        : 0,

    accuracy:
      typeof response.accuracy ===
      "number"
        ? response.accuracy
        : null,

    results:
      Array.isArray(response.results)
        ? response.results
        : []

  };

}


/* =======================================================
   SUMMARY
   ======================================================= */

export async function getDatasetSummary():
  Promise<DatasetSummary> {

  const response =
    await request<{
      summary:
        DatasetSummary;
    }>(
      "/api/dataset/summary"
    );


  if (
    !response.summary
  ) {

    throw new Error(
      "Server did not return the dataset summary."
    );

  }


  return response.summary;

}


/* =======================================================
   CSV DOWNLOADS
   ======================================================= */

export function getDatasetFeaturesCsvUrl():
  string {

  return (
    `${API_BASE_URL}/api/dataset/export/features`
  );

}


export function getDatasetPredictionsCsvUrl():
  string {

  return (
    `${API_BASE_URL}/api/dataset/export/predictions`
  );

}


/* =======================================================
   AUDIO
   ======================================================= */

export function getDatasetSampleAudioUrl(
  id: number
): string {

  return (
    `${API_BASE_URL}/api/dataset/samples/${id}/audio`
  );

}