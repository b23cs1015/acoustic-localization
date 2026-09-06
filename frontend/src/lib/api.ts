import type {
  AnalyzeResponse,
  Measurement,
  MeasurementsResponse,
  Position,
  PositionsResponse
} from "../types";


const API_BASE =
  " https://stopping-purple-hop-constructed.trycloudflare.com";


/* =======================================================
   ANALYZE
======================================================= */

export async function analyzeAudio(
  audio: Blob
): Promise<AnalyzeResponse> {

  const formData =
    new FormData();

  formData.append(
    "audio",
    audio,
    "measurement.wav"
  );

  const response =
    await fetch(
      `${API_BASE}/api/analyze`,
      {
        method: "POST",
        body: formData
      }
    );

  if (!response.ok) {

    const errorText =
      await response.text();

    throw new Error(
      errorText ||
      `Server returned ${response.status}`
    );
  }

  return response.json();
}


/* =======================================================
   MEASUREMENTS
======================================================= */

export async function getMeasurements():
  Promise<MeasurementsResponse> {

  const response =
    await fetch(
      `${API_BASE}/api/measurements`
    );

  if (!response.ok) {

    const errorText =
      await response.text();

    throw new Error(
      errorText ||
      `Server returned ${response.status}`
    );
  }

  return response.json();
}


/* =======================================================
   RESEARCH ANALYTICS
======================================================= */

export async function getAllAnalytics():
  Promise<Record<string, unknown>> {

  const response =
    await fetch(
      `${API_BASE}/api/analytics`
    );

  if (!response.ok) {

    const errorText =
      await response.text();

    throw new Error(
      errorText ||
        `Server returned ${response.status}`
    );
  }

  return response.json();
}

/* =======================================================
   AUDIO
======================================================= */

export function getMeasurementAudioUrl(
  measurementId: number
): string {

  return (
    `${API_BASE}/api/measurements/` +
    `${measurementId}/audio`
  );
}


/* =======================================================
   POSITIONS
======================================================= */

export async function getPositions():
  Promise<PositionsResponse> {

  const response =
    await fetch(
      `${API_BASE}/api/positions`
    );

  if (!response.ok) {

    const errorText =
      await response.text();

    throw new Error(
      errorText ||
      `Server returned ${response.status}`
    );
  }

  return response.json();
}


export async function createPosition(
  name?: string
): Promise<Position> {

  const response =
    await fetch(
      `${API_BASE}/api/positions`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json"
        },

        body: JSON.stringify({
          name:
            name?.trim() || null
        })
      }
    );

  if (!response.ok) {

    const errorText =
      await response.text();

    throw new Error(
      errorText ||
      `Server returned ${response.status}`
    );
  }

  const data =
    await response.json();

  return data.position;
}


/* =======================================================
   UPDATE MEASUREMENT
======================================================= */

export async function updateMeasurement(
  measurementId: number,
  data: {
    position_id: number | null;
    object_between: string | null;
    distance_cm: number | null;
    notes: string | null;
  }
): Promise<Measurement> {

  const response =
    await fetch(
      `${API_BASE}/api/measurements/` +
      `${measurementId}`,
      {
        method: "PATCH",

        headers: {
          "Content-Type":
            "application/json"
        },

        body: JSON.stringify(data)
      }
    );

  if (!response.ok) {

    const errorText =
      await response.text();

    throw new Error(
      errorText ||
      `Server returned ${response.status}`
    );
  }

  const result =
    await response.json();

  return result.measurement;
}


/* =======================================================
   FEEDBACK
======================================================= */

export async function saveFeedback(
  measurementId: number,
  positionId: number,
  correct: boolean
): Promise<Measurement> {

  const response =
    await fetch(
      `${API_BASE}/api/measurements/` +
      `${measurementId}/feedback`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json"
        },

        body: JSON.stringify({
          position_id:
            positionId,

          correct
        })
      }
    );

  if (!response.ok) {

    const errorText =
      await response.text();

    throw new Error(
      errorText ||
      `Server returned ${response.status}`
    );
  }

  const result =
    await response.json();

  return result.measurement;
}


/* =======================================================
   DISCARD
======================================================= */

export async function discardMeasurement(
  measurementId: number
): Promise<Measurement> {

  const response =
    await fetch(
      `${API_BASE}/api/measurements/` +
      `${measurementId}`,
      {
        method: "DELETE"
      }
    );

  if (!response.ok) {

    const errorText =
      await response.text();

    throw new Error(
      errorText ||
      `Server returned ${response.status}`
    );
  }

  const result =
    await response.json();

  return result.measurement;
}


/* =======================================================
   RESTORE
======================================================= */

export async function restoreMeasurement(
  measurementId: number
): Promise<Measurement> {

  const response =
    await fetch(
      `${API_BASE}/api/measurements/` +
      `${measurementId}/restore`,
      {
        method: "POST"
      }
    );

  if (!response.ok) {

    const errorText =
      await response.text();

    throw new Error(
      errorText ||
      `Server returned ${response.status}`
    );
  }

  const result =
    await response.json();

  return result.measurement;
}


/* =======================================================
   RESEARCH ANALYTICS
======================================================= */

/*
 * The backend analytics endpoint returns a collection
 * of research-oriented datasets.
 *
 * The dashboard intentionally keeps these fields flexible
 * because different analytics sections may be unavailable
 * until enough labeled training data exists.
 */

export interface AnalyticsResponse {

  success?: boolean;

  summary?:
    Record<string, unknown>;

  features?:
    Record<string, unknown>;

  position?:
    Record<string, unknown>;

  distance?:
    Record<string, unknown>;

  object?:
    Record<string, unknown>;

  pca?:
    Record<string, unknown>;

  [key: string]:
    unknown;
}
