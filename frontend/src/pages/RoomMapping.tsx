import {
  useEffect,
  useRef,
  useState
} from "react";

import {
  audioBufferToWav
} from "../lib/wav";

import {
  DEFAULT_ROOM_MAPPING_CONFIG,
  RoomMappingRecorder
} from "../lib/roomMappingRecorder";

import {
  getRoomMappingDownloadUrl,
  uploadRoomMappingRecording,
  type RoomMappingUploadResult
} from "../lib/roomMappingApi";


type MappingState =
  | "idle"
  | "recording"
  | "uploading"
  | "complete"
  | "error";


function formatDuration(
  seconds: number
): string {

  const safe =
    Math.max(
      0,
      Math.floor(seconds)
    );

  const minutes =
    Math.floor(
      safe / 60
    );

  const remainingSeconds =
    safe % 60;

  return (
    `${String(minutes).padStart(2, "0")}:` +
    `${String(remainingSeconds).padStart(2, "0")}`
  );
}


export default function RoomMapping() {

  const recorderRef =
    useRef<RoomMappingRecorder | null>(
      null
    );

  const timerRef =
    useRef<number | null>(
      null
    );


  const [
    roomName,
    setRoomName
  ] = useState(
    "Room 1"
  );


  const [
    remarks,
    setRemarks
  ] = useState(
    ""
  );


  const [
    state,
    setState
  ] = useState<MappingState>(
    "idle"
  );


  const [
    elapsedSeconds,
    setElapsedSeconds
  ] = useState(
    0
  );


  const [
    error,
    setError
  ] = useState(
    ""
  );


  const [
    result,
    setResult
  ] = useState<RoomMappingUploadResult | null>(
    null
  );


  const isRecording =
    state === "recording";


  const isBusy =
    state === "recording" ||
    state === "uploading";


  useEffect(() => {

    return () => {

      if (
        timerRef.current !== null
      ) {

        window.clearInterval(
          timerRef.current
        );

      }


      if (
        recorderRef.current
      ) {

        void recorderRef.current.cancel();

      }

    };

  }, []);


  function startTimer(): void {

    if (
      timerRef.current !== null
    ) {

      window.clearInterval(
        timerRef.current
      );

    }


    timerRef.current =
      window.setInterval(
        () => {

          if (
            recorderRef.current
          ) {

            setElapsedSeconds(
              recorderRef.current.elapsedSeconds
            );

          }

        },
        100
      );

  }


  function stopTimer(): void {

    if (
      timerRef.current !== null
    ) {

      window.clearInterval(
        timerRef.current
      );

      timerRef.current = null;

    }

  }


  async function handleStart(): Promise<void> {

    if (isBusy) {
      return;
    }


    setError("");
    setResult(null);
    setElapsedSeconds(0);


    const recorder =
      new RoomMappingRecorder(
        DEFAULT_ROOM_MAPPING_CONFIG
      );


    recorderRef.current =
      recorder;


    try {

      await recorder.start();

      setState(
        "recording"
      );

      startTimer();

    } catch (startError) {

      recorderRef.current =
        null;

      setState(
        "error"
      );

      setError(
        startError instanceof Error
          ? startError.message
          : "Could not start room mapping recording."
      );

    }

  }


  async function handleStop(): Promise<void> {

    const recorder =
      recorderRef.current;


    if (
      !recorder ||
      !isRecording
    ) {

      return;

    }


    stopTimer();

    setState(
      "uploading"
    );

    setError("");


    try {

      const recording =
        await recorder.stop();


      recorderRef.current =
        null;


      if (
        recording.durationSeconds < 1
      ) {

        throw new Error(
          "The recording is too short. Record for at least a few seconds."
        );

      }


      const wavBlob =
        audioBufferToWav(
          recording.audioBuffer
        );


      const uploadResult =
        await uploadRoomMappingRecording(
          wavBlob,
          {
            roomName,
            remarks,
            durationSeconds:
              recording.durationSeconds,
            sampleRate:
              recording.sampleRate,
            startFrequency:
              DEFAULT_ROOM_MAPPING_CONFIG.startFrequency,
            endFrequency:
              DEFAULT_ROOM_MAPPING_CONFIG.endFrequency,
            chirpDuration:
              DEFAULT_ROOM_MAPPING_CONFIG.chirpDuration,
          }
        );


      setElapsedSeconds(
        recording.durationSeconds
      );

      setResult(
        uploadResult
      );

      setState(
        "complete"
      );

    } catch (stopError) {

      recorderRef.current =
        null;

      setState(
        "error"
      );

      setError(
        stopError instanceof Error
          ? stopError.message
          : "Could not finish the room mapping recording."
      );

    }

  }


  function handleReset(): void {

    stopTimer();


    if (
      recorderRef.current
    ) {

      void recorderRef.current.cancel();

      recorderRef.current =
        null;

    }


    setState(
      "idle"
    );

    setElapsedSeconds(
      0
    );

    setError("");

    setResult(
      null
    );

  }


  return (

    <main className="main-content room-mapping-page">

      <section className="room-mapping-hero">

        <p className="eyebrow">
          Task 2 · Acoustic room mapping
        </p>


        <h1>
          Record the room.
          <br />
          Build its acoustic map.
        </h1>


        <p className="hero-description">
          Play a continuous 15–20 kHz chirp while
          the phone records its acoustic response.
          Walk slowly around the room with the phone
          horizontal and keep the speaker/microphone
          side facing the room. The resulting WAV is
          saved for offline acoustic-map analysis.
        </p>

      </section>


      <section className="room-mapping-workspace">

        <div className="room-mapping-card">

          <div className="room-mapping-card-header">

            <div>

              <p className="section-kicker">
                Continuous recording
              </p>

              <h2>
                Room Acoustic Mapping
              </h2>

            </div>


            <div className="room-mapping-status">

              <span
                className={
                  isRecording
                    ? "room-mapping-status-dot recording"
                    : "room-mapping-status-dot"
                }
              />

              {
                isRecording
                  ? "Recording"
                  : state === "uploading"
                    ? "Uploading"
                    : state === "complete"
                      ? "Saved"
                      : "Ready"
              }

            </div>

          </div>


          <div className="room-mapping-form">

            <label className="field-label">
              Room / experiment name
            </label>


            <input
              value={roomName}
              onChange={
                event =>
                  setRoomName(
                    event.target.value
                  )
              }
              disabled={isBusy}
              placeholder="e.g. Room 1"
            />


            <label className="field-label">
              Remarks
            </label>


            <textarea
              value={remarks}
              onChange={
                event =>
                  setRemarks(
                    event.target.value
                  )
              }
              disabled={isBusy}
              rows={3}
              placeholder="Room size, furniture, doors/windows, noise conditions..."
            />

          </div>


          <div className="room-mapping-parameters">

            <div>
              <span>
                Chirp
              </span>

              <strong>
                15–20 kHz
              </strong>
            </div>


            <div>
              <span>
                Chirp period
              </span>

              <strong>
                1 second
              </strong>
            </div>


            <div>
              <span>
                Recorder
              </span>

              <strong>
                48 kHz target
              </strong>
            </div>


            <div>
              <span>
                Mode
              </span>

              <strong>
                Manual stop
              </strong>
            </div>

          </div>


          <div className="room-mapping-timer">

            <span>
              Elapsed recording time
            </span>

            <strong>
              {formatDuration(
                elapsedSeconds
              )}
            </strong>

          </div>


          <div className="room-mapping-actions">

            {!isRecording &&
              state !== "uploading" && (

                <button
                  type="button"
                  className="room-mapping-start-button"
                  onClick={
                    () =>
                      void handleStart()
                  }
                  disabled={
                    isBusy ||
                    !roomName.trim()
                  }
                >

                  {
                    state === "complete"
                      ? "Start New Recording"
                      : "Start Room Mapping"
                  }

                </button>

              )}


            {isRecording && (

              <button
                type="button"
                className="room-mapping-stop-button"
                onClick={
                  () =>
                    void handleStop()
                }
              >
                Stop Recording & Upload
              </button>

            )}


            {state === "uploading" && (

              <div className="room-mapping-uploading">
                Saving the WAV and metadata…
              </div>

            )}


            {state === "error" && (

              <button
                type="button"
                className="secondary-button"
                onClick={handleReset}
              >
                Reset
              </button>

            )}

          </div>


          {error && (

            <div className="error-card room-mapping-error">

              <strong>
                Room Mapping Error
              </strong>

              <p>
                {error}
              </p>

            </div>

          )}

        </div>


        <aside className="room-mapping-instructions">

          <p className="section-kicker">
            Collection protocol
          </p>


          <h2>
            Keep the movement controlled.
          </h2>


          <ol>

            <li>
              Keep the phone horizontal and
              stationary in height as much as practical.
            </li>

            <li>
              Keep the phone's speaker/microphone
              side facing the room.
            </li>

            <li>
              Start recording before beginning
              the walking path.
            </li>

            <li>
              Walk slowly through the room rather
              than changing orientation randomly.
            </li>

            <li>
              Stop after approximately 60 seconds,
              or earlier if the planned path is complete.
            </li>

            <li>
              Keep room conditions documented:
              people, fans, doors, windows,
              furniture and other noise sources.
            </li>

          </ol>


          <div className="room-mapping-warning">

            <strong>
              Research note
            </strong>

            <p>
              The first version produces an
              audio-derived acoustic room map.
              It does not claim to recover exact
              physical wall geometry from a single
              recording automatically.
            </p>

          </div>

        </aside>

      </section>


      {result && (

        <section className="room-mapping-result-card">

          <div>

            <p className="section-kicker">
              Recording saved
            </p>

            <h2>
              {result.filename}
            </h2>

            <p>
              {result.duration_seconds.toFixed(2)}
              {" seconds · "}
              {result.sample_rate}
              {" Hz · mapping ID "}
              {result.mapping_id}
            </p>

          </div>


          <a
            className="primary-button room-mapping-download"
            href={
              getRoomMappingDownloadUrl(
                result.mapping_id
              )
            }
          >
            Download WAV
          </a>

        </section>

      )}

    </main>

  );
}