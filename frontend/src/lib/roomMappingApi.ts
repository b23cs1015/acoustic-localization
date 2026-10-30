const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";


// =====================================================
// INTERFACES
// =====================================================

export interface RoomMappingUploadMetadata {
  roomName: string;
  remarks?: string;

  durationSeconds: number;
  sampleRate: number;

  startFrequency: number;
  endFrequency: number;
  chirpDuration: number;

  experimentNumber: string;
  experimentTitle: string;

  batchId?: string;
  recordingNumber?: number;
  totalRecordings?: number;

  positionId: string;

  distanceCm?: number;
  xCm?: number;
  yCm?: number;
  phoneHeightCm?: number;
}


export interface RoomMappingUploadResult {
  success: boolean;
  mapping_id: string;
  filename: string;

  duration_seconds: number;
  sample_rate: number;
  created_at: string;

  experiment_number: string;
  position_id: string;

  download_url?: string;
  metadata_url?: string;
}


export interface Experiment {
  experiment_number: string;
  experiment_title: string;
  description: string;
  room_name: string;
  created_at: string;

  total_recordings: number;
  total_positions: number;

  positions: string[];
}


export interface RecordingHistoryItem {
  mapping_id: string;

  experiment_number: string;
  experiment_title: string;

  room_name: string;

  position_id: string;
  distance_cm: number | null;

  x_cm: number | null;
  y_cm: number | null;
  phone_height_cm: number | null;

  batch_id: string;

  recording_number: number | null;
  total_recordings: number | null;

  duration_seconds: number;
  sample_rate: number;

  created_at: string;

  saved_filename: string;
}


export interface RecordingHistoryResponse {
  total: number;
  recordings: RecordingHistoryItem[];
}


// =====================================================
// COMMON RESPONSE HANDLER
// =====================================================

async function handleResponse<T>(
  response: Response
): Promise<T> {
  if (!response.ok) {
    let message = `Server returned ${response.status}`;

    try {
      const data = await response.json();

      if (typeof data?.detail === "string") {
        message = data.detail;
      }
    } catch {
      // Retain default status message.
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}


// =====================================================
// UPLOAD RECORDING
// =====================================================

export async function uploadRoomMappingRecording(
  audioBlob: Blob,
  metadata: RoomMappingUploadMetadata
): Promise<RoomMappingUploadResult> {
  const form = new FormData();

  form.append(
    "audio",
    audioBlob,
    `room_mapping_${Date.now()}.wav`
  );

  const fields: Record<string, string | number | undefined> = {
    room_name: metadata.roomName,
    remarks: metadata.remarks ?? "",

    duration_seconds: metadata.durationSeconds,
    sample_rate: metadata.sampleRate,

    start_frequency: metadata.startFrequency,
    end_frequency: metadata.endFrequency,
    chirp_duration: metadata.chirpDuration,

    experiment_number: metadata.experimentNumber,
    experiment_title: metadata.experimentTitle,

    position_id: metadata.positionId,

    distance_cm: metadata.distanceCm,
    x_cm: metadata.xCm,
    y_cm: metadata.yCm,
    phone_height_cm: metadata.phoneHeightCm,

    batch_id: metadata.batchId,
    recording_number: metadata.recordingNumber,
    total_recordings: metadata.totalRecordings,
  };

  Object.entries(fields).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      form.append(key, String(value));
    }
  });

  const response = await fetch(
    `${API_BASE}/api/room-mapping/recordings`,
    {
      method: "POST",
      body: form,
    }
  );

  return handleResponse<RoomMappingUploadResult>(response);
}


// =====================================================
// CREATE EXPERIMENT
// =====================================================

export async function createExperiment(
  data: {
    experimentNumber: string;
    experimentTitle: string;
    description: string;
    roomName: string;
  }
): Promise<Experiment> {
  const form = new FormData();

  form.append("experiment_number", data.experimentNumber);
  form.append("experiment_title", data.experimentTitle);
  form.append("description", data.description);
  form.append("room_name", data.roomName);

  const response = await fetch(
    `${API_BASE}/api/room-mapping/experiments`,
    {
      method: "POST",
      body: form,
    }
  );

  return handleResponse<Experiment>(response);
}


// =====================================================
// GET ALL EXPERIMENTS
// =====================================================

export async function getExperiments(): Promise<Experiment[]> {
  const response = await fetch(
    `${API_BASE}/api/room-mapping/experiments`
  );

  return handleResponse<Experiment[]>(response);
}


// =====================================================
// GET RECORDING HISTORY
// =====================================================

export async function getRecordingHistory(
  experimentNumber?: string,
  positionId?: string
): Promise<RecordingHistoryResponse> {
  const params = new URLSearchParams();

  if (experimentNumber) {
    params.set("experiment_number", experimentNumber);
  }

  if (positionId) {
    params.set("position_id", positionId);
  }

  const response = await fetch(
    `${API_BASE}/api/room-mapping/recordings?${params.toString()}`
  );

  return handleResponse<RecordingHistoryResponse>(response);
}


// =====================================================
// DELETE EXPERIMENT
// =====================================================

export async function deleteExperiment(
  experimentNumber: string
): Promise<{
  success: boolean;
  deleted_experiment: string;
  deleted_batches: number;
  deleted_recordings: number;
}> {
  const response = await fetch(
    `${API_BASE}/api/room-mapping/experiments/${encodeURIComponent(
      experimentNumber
    )}`,
    {
      method: "DELETE",
    }
  );

  return handleResponse(response);
}


// =====================================================
// DELETE BATCH
// =====================================================

export async function deleteBatch(
  experimentNumber: string,
  batchId: string
): Promise<{
  success: boolean;
  deleted_batch: string;
  deleted_recordings: number;
}> {
  const response = await fetch(
    `${API_BASE}/api/room-mapping/experiments/${encodeURIComponent(
      experimentNumber
    )}/batches/${encodeURIComponent(batchId)}`,
    {
      method: "DELETE",
    }
  );

  return handleResponse(response);
}


// =====================================================
// DOWNLOAD WAV
// =====================================================

export function getRoomMappingDownloadUrl(
  mappingId: string
): string {
  return (
    `${API_BASE}/api/room-mapping/recordings/` +
    `${encodeURIComponent(mappingId)}/audio`
  );
}


// =====================================================
// DOWNLOAD METADATA
// =====================================================

export function getRoomMappingMetadataUrl(
  mappingId: string
): string {
  return (
    `${API_BASE}/api/room-mapping/recordings/` +
    `${encodeURIComponent(mappingId)}/metadata`
  );
}