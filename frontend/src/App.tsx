import {
  useState
} from "react";

import MeasurementPanel from "./components/MeasurementPanel";

import StatusCard from "./components/StatusCard";

import ResultCard from "./components/ResultCard";

import MeasurementHistory from "./components/MeasurementHistory";

import type {
  MeasurementStatus,
  PredictionResult
} from "./types";


function App() {

  const [
    status,
    setStatus
  ] = useState<MeasurementStatus>(
    "idle"
  );


  const [
    result,
    setResult
  ] = useState<PredictionResult | null>(
    null
  );


  const [
    error,
    setError
  ] = useState("");


  /*
   * Changing this number causes
   * MeasurementHistory to fetch
   * the latest data from SQLite.
   */
  const [
    historyRefreshKey,
    setHistoryRefreshKey
  ] = useState(0);


  function handleMeasurementComplete() {

    setHistoryRefreshKey(
      (current) =>
        current + 1
    );

  }


  return (
    <main className="app">

      <section className="hero">

        <div className="eyebrow">
          BTP RESEARCH PROTOTYPE
        </div>


        <h1>
          Acoustic
          <br />
          Localization
        </h1>


        <p className="intro">

          A browser-based acoustic sensing
          prototype that emits a controlled
          chirp, records the response, and
          sends it to a central machine
          learning server.

        </p>

      </section>


      <section className="workspace">

        <StatusCard
          status={status}
        />


        <MeasurementPanel
          onStatusChange={
            setStatus
          }
          onResult={
            setResult
          }
          onError={
            setError
          }
          onMeasurementComplete={
            handleMeasurementComplete
          }
        />


        {error && (

          <div className="error-card">

            <strong>
              Measurement Error
            </strong>

            <p>
              {error}
            </p>

          </div>

        )}


        <ResultCard
          result={result}
        />


        <MeasurementHistory
          refreshKey={
            historyRefreshKey
          }
        />

      </section>


      <footer>

        <span>
          15–20 kHz · 1 second chirp
        </span>


        <span>
          Central server inference
        </span>

      </footer>

    </main>
  );
}


export default App;