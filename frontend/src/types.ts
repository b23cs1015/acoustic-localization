export type MeasurementStatus =
  | "idle"
  | "requesting"
  | "recording"
  | "processing"
  | "success"
  | "error";


/* =========================================================
   PREDICTION
========================================================= */

export interface PredictionResult {
  prediction: string;

  confidence: number | null;

  features: Record<string, number>;

  duration_seconds: number;

  sample_rate: number;
}


export interface AnalyzeResponse {
  success: boolean;

  measurement_id: number;

  result: PredictionResult;
}


/* =========================================================
   POSITIONS
========================================================= */

export interface Position {
  id: number;

  position_number: number;

  name: string;

  created_at: string;
}


export interface PositionsResponse {
  success: boolean;

  positions: Position[];
}


/* =========================================================
   MEASUREMENTS
========================================================= */

export interface Measurement {
  id: number;

  timestamp: string;

  recording_filename: string;

  prediction: string;

  confidence: number | null;

  duration_seconds: number;

  sample_rate: number;

  features: Record<string, number>;

  position_id: number | null;

  position_number: number | null;

  position_name: string | null;

  object_between: string | null;

  distance_cm: number | null;

  notes: string | null;

  feedback_correct: boolean | null;

  feedback_timestamp: string | null;

  discarded: boolean;
}


export interface MeasurementsResponse {
  success: boolean;

  count: number;

  measurements: Measurement[];
}


/* =========================================================
   ANALYTICS
========================================================= */

/*
 * The analytics backend can evolve while the research
 * experiments are being developed. These interfaces therefore
 * intentionally allow additional fields.
 */

export interface AnalyticsSummary {
  [key: string]: unknown;
}


export interface AnalyticsFeatureData {
  [key: string]: unknown;
}


export interface AnalyticsPositionData {
  [key: string]: unknown;
}


export interface AnalyticsDistanceData {
  [key: string]: unknown;
}


export interface AnalyticsObjectData {
  [key: string]: unknown;
}


export interface AnalyticsPCAData {
  [key: string]: unknown;
}


export interface AnalyticsResponse<T> {
  success: boolean;

  [key: string]: unknown;
}


/* =========================================================
   DASHBOARD TYPES
========================================================= */

export interface DashboardData {
  summary: AnalyticsSummary | null;

  features: AnalyticsFeatureData | null;

  position: AnalyticsPositionData | null;

  distance: AnalyticsDistanceData | null;

  object: AnalyticsObjectData | null;

  pca: AnalyticsPCAData | null;

  measurements: Measurement[];

  loading: boolean;

  error: string;
}