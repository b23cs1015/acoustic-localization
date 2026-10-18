const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";


export interface RoomMappingUploadMetadata {

  roomName: string;

  remarks?: string;

  durationSeconds: number;

  sampleRate: number;

  startFrequency: number;

  endFrequency: number;

  chirpDuration: number;

}


export interface RoomMappingUploadResult {

  success: boolean;

  mapping_id: string;

  filename: string;

  duration_seconds: number;

  sample_rate: number;

  created_at: string;

  download_url: string;

  metadata_url: string;

}


export async function uploadRoomMappingRecording(

  audioBlob: Blob,

  metadata: RoomMappingUploadMetadata

): Promise<RoomMappingUploadResult> {

  const formData =
    new FormData();


  formData.append(
    "audio",
    audioBlob,
    `room_mapping_${Date.now()}.wav`
  );


  formData.append(
    "room_name",
    metadata.roomName
  );


  formData.append(
    "remarks",
    metadata.remarks ?? ""
  );


  formData.append(
    "duration_seconds",
    String(
      metadata.durationSeconds
    )
  );


  formData.append(
    "sample_rate",
    String(
      metadata.sampleRate
    )
  );


  formData.append(
    "start_frequency",
    String(
      metadata.startFrequency
    )
  );


  formData.append(
    "end_frequency",
    String(
      metadata.endFrequency
    )
  );


  formData.append(
    "chirp_duration",
    String(
      metadata.chirpDuration
    )
  );


  const response =
    await fetch(
      `${API_BASE}/api/room-mapping/recordings`,
      {
        method: "POST",
        body: formData,
      }
    );


  if (!response.ok) {

    let message =
      `Server returned ${response.status}`;


    try {

      const data =
        await response.json();


      if (
        typeof data?.detail === "string"
      ) {

        message =
          data.detail;

      }

    } catch {
      // Keep status message.
    }


    throw new Error(
      message
    );

  }


  return response.json();

}


export function getRoomMappingDownloadUrl(
  mappingId: string
): string {

  return (
    `${API_BASE}/api/room-mapping/recordings/` +
    `${encodeURIComponent(mappingId)}/audio`
  );

}


export function getRoomMappingMetadataUrl(
  mappingId: string
): string {

  return (
    `${API_BASE}/api/room-mapping/recordings/` +
    `${encodeURIComponent(mappingId)}/metadata`
  );

}