import {
  useState
} from "react";

import MeasurementPanel from "./components/MeasurementPanel";
import MeasurementHistory from "./components/MeasurementHistory";
import ResultCard from "./components/ResultCard";
import StatusCard from "./components/StatusCard";
import ResearchDashboard from "./components/ResearchDashboard";

import CollectData from "./pages/CollectData";

import type {
  MeasurementStatus,
  PredictionResult
} from "./types";

import "./index.css";


type AppPage =
  | "measurement"
  | "collect";


export default function App() {

  const [
    page,
    setPage
  ] = useState<AppPage>(
    "measurement"
  );


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


  const [
    refreshKey,
    setRefreshKey
  ] = useState(0);


  function handleStatusChange(
    nextStatus: MeasurementStatus
  ) {

    setStatus(
      nextStatus
    );
  }


  function handleResult(
    nextResult: PredictionResult
  ) {

    setResult(
      nextResult
    );
  }


  function handleError(
    message: string
  ) {

    setError(
      message
    );
  }


  function handleMeasurementComplete() {

    setRefreshKey(
      current =>
        current + 1
    );
  }


  return (
    <div className="app-shell">

      <header className="site-header">

        <div className="brand-block">

          <span className="brand-mark">
            AL
          </span>

          <div>

            <p className="brand-name">
              Acoustic Localization
            </p>

            <p className="brand-subtitle">
              BTP Research Prototype
            </p>

          </div>

        </div>


        <nav className="main-navigation">

          <button
            type="button"
            className={
              page === "measurement"
                ? "active"
                : ""
            }
            onClick={() =>
              setPage("measurement")
            }
          >
            Measurement
          </button>


          <button
            type="button"
            className={
              page === "collect"
                ? "active"
                : ""
            }
            onClick={() =>
              setPage("collect")
            }
          >
            Collect Data
          </button>

        </nav>

      </header>


      {page === "collect" ? (

        <CollectData />

      ) : (

        <main className="main-content">

          <section className="hero-section">

            <p className="eyebrow">
              Acoustic localization system
            </p>

            <h1>
              Measure distance
              <br />
              through sound.
            </h1>

            <p className="hero-description">
              Play a controlled ultrasonic chirp,
              capture the acoustic response, and
              estimate the target position using
              the current acoustic fingerprint
              model.
            </p>

          </section>


          <section className="measurement-workspace">

            <div>

              <MeasurementPanel
                onStatusChange={
                  handleStatusChange
                }
                onResult={
                  handleResult
                }
                onError={
                  handleError
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

            </div>


            <div className="measurement-side">

              <StatusCard
                status={status}
              />

              <ResultCard
                result={result}
              />

            </div>

          </section>


          <MeasurementHistory
            refreshKey={refreshKey}
          />


          <ResearchDashboard />

        </main>

      )}


      <footer className="site-footer">

        <span>
          Acoustic Localization · B.Tech Project
        </span>

        <span>
          Research prototype
        </span>

      </footer>

    </div>
  );
}