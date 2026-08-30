export type MeasurementStatus =
  | "idle"
  | "requesting"
  | "recording"
  | "processing"
  | "success"
  | "error";


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


export interface Position {

  id: number;

  position_number: number;

  name: string;

  created_at: string;
}


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


export interface PositionsResponse {

  success: boolean;

  positions: Position[];
}