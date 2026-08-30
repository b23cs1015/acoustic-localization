import {
  useEffect,
  useState
} from "react";

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

import {
  analyzeAudio,
  createPosition,
  getPositions,
  saveFeedback,
  updateMeasurement
} from "../lib/api";

import type {
  MeasurementStatus,
  PredictionResult,
  Position
} from "../types";


interface Props {

  onStatusChange: (
    status: MeasurementStatus
  ) => void;

  onResult: (
    result: PredictionResult
  ) => void;

  onError: (
    message: string
  ) => void;

  onMeasurementComplete: () => void;
}


export default function MeasurementPanel({
  onStatusChange,
  onResult,
  onError,
  onMeasurementComplete
}: Props) {

  const [
    isRunning,
    setIsRunning
  ] = useState(false);

  const [
    measurementId,
    setMeasurementId
  ] = useState<number | null>(null);

  const [
    positions,
    setPositions
  ] = useState<Position[]>([]);

  const [
    selectedPosition,
    setSelectedPosition
  ] = useState("");

  const [
    objectBetween,
    setObjectBetween
  ] = useState("");

  const [
    distance,
    setDistance
  ] = useState("");

  const [
    notes,
    setNotes
  ] = useState("");

  const [
    feedbackCorrect,
    setFeedbackCorrect
  ] = useState<boolean | null>(null);

  const [
    savingFeedback,
    setSavingFeedback
  ] = useState(false);

  const [
    feedbackSaved,
    setFeedbackSaved
  ] = useState(false);


  useEffect(() => {

    loadPositions();

  }, []);


  async function loadPositions() {

    try {

      const response =
        await getPositions();

      setPositions(
        response.positions
      );

    } catch (error) {

      console.error(error);

    }
  }


  async function handleAddPosition() {

    try {

      const position =
        await createPosition();

      setPositions(
        current => [
          ...current,
          position
        ]
      );

      setSelectedPosition(
        String(position.id)
      );

    } catch (error) {

      onError(
        error instanceof Error
          ? error.message
          : "Could not create position."
      );
    }
  }


  async function handleMeasurement() {

    if (isRunning) {
      return;
    }

    try {

      setIsRunning(true);

      setMeasurementId(null);

      setFeedbackSaved(false);

      setFeedbackCorrect(null);

      setSelectedPosition("");

      setObjectBetween("");

      setDistance("");

      setNotes("");

      onError("");

      onStatusChange(
        "requesting"
      );


      const microphone =
        await navigator.mediaDevices.getUserMedia(
          {
            audio: {
              channelCount: 1,
              echoCancellation: false,
              noiseSuppression: false,
              autoGainControl: false
            }
          }
        );


      microphone
        .getTracks()
        .forEach(
          track =>
            track.stop()
        );


      const recordingPromise =
        recordMicrophone(1300);


      onStatusChange(
        "recording"
      );


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


      onStatusChange(
        "processing"
      );


      const response =
        await analyzeAudio(
          wavBlob
        );

        setMeasurementId(
            response.measurement_id
            );


      onResult(
        response.result
      );


      /*
       * History is refreshed after
       * the backend has saved the
       * measurement.
       */
      onMeasurementComplete();


      onStatusChange(
        "success"
      );

    } catch (error) {

      console.error(error);

      const message =
        error instanceof Error
          ? error.message
          : "Measurement failed.";

      onError(message);

      onStatusChange(
        "error"
      );

    } finally {

      setIsRunning(false);

    }
  }


  async function handleSaveFeedback() {

    if (
      !measurementId ||
      !selectedPosition
    ) {

      onError(
        "Please select the actual location first."
      );

      return;
    }


    try {

      setSavingFeedback(true);

      onError("");


      const positionId =
        Number(
          selectedPosition
        );


      await updateMeasurement(
        measurementId,
        {
          position_id:
            positionId,

          object_between:
            objectBetween.trim()
              || null,

          distance_cm:
            distance.trim()
              ? Number(distance)
              : null,

          notes:
            notes.trim()
              || null
        }
      );


      await saveFeedback(
        measurementId,
        positionId,
        feedbackCorrect === true
      );


      setFeedbackSaved(true);

      onMeasurementComplete();

    } catch (error) {

      console.error(error);

      onError(
        error instanceof Error
          ? error.message
          : "Could not save feedback."
      );

    } finally {

      setSavingFeedback(false);

    }
  }


  /*
   * The backend currently creates
   * the measurement ID automatically.
   *
   * Therefore the feedback panel
   * becomes available through the
   * history card after saving.
   *
   * We intentionally don't invent
   * a measurement ID here.
   */

  return (
    <div className="measurement-panel">

      <button
        className="measure-button"
        onClick={
          handleMeasurement
        }
        disabled={isRunning}
      >

        {isRunning
          ? "Measuring..."
          : "Start Measurement"}

      </button>


      <p className="measurement-note">

        The device will play a 1-second
        15–20 kHz chirp and record the
        microphone response simultaneously.

      </p>


      {feedbackSaved && (

        <div className="feedback-success">

          Feedback saved successfully.

          The recording is now available
          as labeled training data.

        </div>

      )}

    </div>
  );
}