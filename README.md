# Acoustic Localization Using Smartphone Audio

> **B.Tech Project (BTP) / Research Prototype**\
> Smartphone-based acoustic sensing for spatial localization, target
> detection, and distance estimation.

## 1. Project Overview

**Acoustic Localization** is a research prototype investigating whether
a smartphone's own speaker and microphone can be used as an active
acoustic sensing system to determine the spatial location of a nearby
target/person.

The long-term pipeline is:

``` text
Smartphone
    ↓
Controlled acoustic chirp
    ↓
Speaker
    ↓
Acoustic propagation / reflection
    ↓
Microphone
    ↓
Audio preprocessing
    ↓
Acoustic feature / fingerprint extraction
    ↓
Target detection + distance estimation + spatial localization
    ↓
Final target location
```

The project is being developed incrementally as an experimental research
system rather than a production-ready localization product.

## 2. Final Project Goal

The intended final system should:

1.  Emit a controlled acoustic signal from a smartphone speaker.
2.  Record the acoustic response using the smartphone microphone.
3.  Determine whether a target/person is present.
4.  Estimate the target's approximate distance from the phone.
5.  Determine the target's spatial position at an experimentally
    justified granularity.
6.  Combine target detection, distance estimation, and localization into
    one pipeline.

A conceptual final output is:

``` text
Target detected
Distance: approximately 45 cm
Location: Position / Region X
```

The exact spatial granularity is itself a research question: the system
may ultimately support discrete regions, distance ranges, or finer
spatial estimates. Distance estimation and person/target detection are
future stages, not completed capabilities of the current benchmark.

## 3. Current Status

### Completed

-   Controlled approximately 1-second 15--20 kHz chirp generation.
-   Smartphone/browser microphone recording.
-   React + TypeScript frontend.
-   FastAPI/Python backend.
-   Audio preprocessing.
-   Handcrafted acoustic feature extraction.
-   Dedicated experimental dataset pipeline.
-   SQLite dataset storage.
-   Raw WAV storage.
-   Weighted KNN acoustic fingerprint localization.
-   Leave-one-out evaluation.
-   Prediction confidence.
-   Research dashboard and analysis views.
-   Predict-one and predict-all dataset workflows.
-   Feature and prediction CSV exports.
-   STFT/PSD acoustic fingerprint implementation.
-   STFT/PSD evaluation and baseline comparison.

### Current Research

The current stage is comparing two acoustic representations:

``` text
12 handcrafted acoustic features
             VS
427-dimensional STFT/PSD fingerprint
```

The main questions are why the representations disagree, which spatial
positions have overlapping acoustic signatures, and whether the current
STFT/PSD temporal averaging discards useful information.

### Planned

-   Improved temporal STFT/PSD representation.
-   Echo and reflection analysis.
-   Cross-correlation and propagation-delay estimation.
-   Distance estimation.
-   Target/person presence detection.
-   Combined target + distance + position prediction.
-   More robust experiments across environmental conditions,
    orientations, noise, and potentially devices.
-   Potential on-device inference in later stages.

## 4. System Architecture

``` text
                    ┌──────────────────────────┐
                    │      Smartphone/Web       │
                    │     React + TypeScript    │
                    └────────────┬─────────────┘
                                 │
                         Play acoustic chirp
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │     Smartphone Speaker    │
                    └────────────┬─────────────┘
                                 │
                      Acoustic propagation
                       + reflection / echoes
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │   Smartphone Microphone   │
                    └────────────┬─────────────┘
                                 │
                              WAV data
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │       FastAPI API         │
                    │      Python Backend       │
                    └────────────┬─────────────┘
                                 │
             ┌───────────────────┼───────────────────┐
             ▼                   ▼                   ▼
       Preprocessing       Feature Extraction      Storage
                                  │
                        ┌─────────┴─────────┐
                        ▼                   ▼
                  Handcrafted           STFT / PSD
                    Features            Fingerprint
                        │                   │
                        └─────────┬─────────┘
                                  ▼
                           Weighted KNN
                                  │
                                  ▼
                         Position + Confidence
```

## 5. Technology Stack

  Layer              Technology
  ------------------ -----------------------------------
  Frontend           React, TypeScript, Vite
  Backend            Python, FastAPI
  Audio Processing   Librosa, NumPy, SciPy
  Machine Learning   Weighted KNN / custom ML pipeline
  Database           SQLite
  Audio              WAV
  Mobile Access      HTTPS via Cloudflare Tunnel
  Export             CSV
  Development        VS Code, PowerShell
  Version Control    Git / GitHub

## 6. Repository Structure

``` text
acoustic-localization/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── schemas.py
│   │   ├── storage.py
│   │   ├── analytics.py
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py
│   │   │   └── dataset_routes.py
│   │   │
│   │   ├── audio/
│   │   │   ├── __init__.py
│   │   │   ├── preprocessing.py
│   │   │   └── features.py
│   │   │
│   │   ├── ml/
│   │   │   ├── __init__.py
│   │   │   ├── model.py
│   │   │   └── predictor.py
│   │   │
│   │   └── dataset/
│   │       ├── __init__.py
│   │       ├── models.py
│   │       ├── predictor.py
│   │       └── storage.py
│   │
│   ├── scripts/
│   │   ├── evaluate_dataset.py
│   │   ├── export_dataset_csv.py
│   │   └── label_dataset_positions.py
│   │
│   └── data/
│       ├── measurements.db
│       ├── measurements.csv
│       ├── recordings/
│       └── dataset/
│           ├── dataset.db
│           ├── recordings/
│           └── evaluation/
│
├── frontend/
│   └── src/
│       ├── App.tsx
│       ├── index.css
│       ├── components/
│       │   ├── MeasurementPanel.tsx
│       │   ├── StatusCard.tsx
│       │   ├── ResultCard.tsx
│       │   ├── MeasurementHistory.tsx
│       │   └── ResearchDashboard.tsx
│       ├── pages/
│       │   └── CollectData.tsx
│       └── lib/
│           ├── api.ts
│           └── datasetApi.ts
│
├── .gitignore
└── README.md
```

### Important modules

-   `backend/app/audio/features.py` --- handcrafted features and
    STFT/PSD fingerprint extraction.
-   `backend/app/audio/preprocessing.py` --- audio preprocessing.
-   `backend/app/dataset/predictor.py` --- experimental dataset
    prediction algorithms.
-   `backend/app/dataset/storage.py` --- experimental dataset
    persistence.
-   `backend/app/dataset/models.py` --- dataset models.
-   `backend/app/api/dataset_routes.py` --- experimental dataset REST
    API.
-   `backend/app/api/routes.py` --- original measurement REST API.
-   `backend/app/ml/` --- original measurement-system ML implementation.
-   `backend/scripts/evaluate_dataset.py` --- reproducible research
    evaluation.
-   `frontend/src/pages/CollectData.tsx` --- experimental collection and
    prediction UI.
-   `frontend/src/components/ResearchDashboard.tsx` --- research
    analytics UI.

## 7. Acoustic Signal

The current experiment uses an approximately **1-second chirp spanning
15--20 kHz**.

Measurement flow:

``` text
Generate chirp
    ↓
Play through phone speaker
    ↓
Acoustic propagation / reflection
    ↓
Record through microphone
    ↓
Save WAV
    ↓
Extract acoustic representation
    ↓
Predict position
```

The controlled signal makes measurements from different spatial
locations comparable.

## 8. Experimental Dataset

A separate dataset subsystem was created so experimental ground truth
remains independent from the original measurement/feedback workflow.

Current benchmark:

``` text
Total recordings:        200
Spatial positions:        10
Recordings per position: 20
```

  Position      Samples
  ----------- ---------
  Pos 1              20
  Pos 2              20
  Pos 3              20
  Pos 4              20
  Pos 5              20
  Pos 6              20
  Pos 7              20
  Pos 8              20
  Pos 9              20
  Pos 10             20
  **Total**     **200**

The dataset stores sample ID, timestamp, position, target-presence
metadata, distance metadata, remarks, raw WAV, features, prediction,
confidence, and evaluation status.

The collection UI supports target labels `Yes`, `No`, and `Can't say`,
and distance values such as 15, 30, 45 cm, or Unknown. These fields
prepare the dataset for later target-detection and distance experiments;
the current 200-sample benchmark is primarily a position-classification
experiment.

## 9. Baseline Acoustic Features

The baseline representation contains 12 handcrafted features:

1.  RMS dB
2.  Peak dB
3.  Spectral centroid
4.  Spectral bandwidth
5.  Spectral rolloff
6.  Spectral flatness
7.  Zero-crossing rate
8.  15--16 kHz energy
9.  16--17 kHz energy
10. 17--18 kHz energy
11. 18--19 kHz energy
12. 19--20 kHz energy

## 10. Baseline KNN

The baseline uses normalized distance-weighted KNN:

``` text
WAV
 ↓
Preprocessing
 ↓
12 acoustic features
 ↓
Z-score normalization
 ↓
Euclidean distance
 ↓
K = 5 nearest neighbours
 ↓
Inverse-distance weighted voting
 ↓
Predicted position + confidence
```

Evaluation excludes the current sample itself.

### Baseline result

``` text
Samples:       200
Evaluated:     200
Correct:       165
Incorrect:      35
Accuracy:     82.50%
```

  Position     Correct   Accuracy
  ---------- --------- ----------
  Pos 1          17/20        85%
  Pos 2          19/20        95%
  Pos 3          18/20        90%
  Pos 4          19/20        95%
  Pos 5          13/20        65%
  Pos 6          15/20        75%
  Pos 7          18/20        90%
  Pos 8          17/20        85%
  Pos 9          12/20        60%
  Pos 10         17/20        85%

Common confusion patterns include Pos 9→8, Pos 6→7, Pos 5→2, Pos 9→10,
and Pos 8→10. These indicate that some positions have overlapping
acoustic signatures.

## 11. STFT/PSD Experiment

A second representation was implemented using Short-Time Fourier
Transform and Power Spectral Density.

Current pipeline:

``` text
WAV
 ↓
Remove DC
 ↓
STFT
 ↓
Power spectrum
 ↓
15–20 kHz restriction
 ↓
Average PSD over time
 ↓
Convert to dB
 ↓
427-dimensional fingerprint
 ↓
Weighted KNN
 ↓
Position
```

The same 200 recordings and leave-one-out protocol are used for
comparison.

### STFT/PSD result

``` text
Samples:        200
Evaluated:      200
Correct:        163
Incorrect:       37
Accuracy:      81.50%
Dimensions:      427
```

  Representation     Dimensions     Accuracy
  ---------------- ------------ ------------
  Handcrafted                12   **82.50%**
  STFT/PSD                  427   **81.50%**

The current STFT/PSD result does not improve overall accuracy, but it
changes performance differently across positions. The experiment is
therefore useful for understanding the information captured by the two
representations.

A key research hypothesis for the next experiment is that averaging PSD
over time may discard useful information from the chirp's time-frequency
evolution. This is a hypothesis to test, not an established conclusion.

## 12. APIs

The experimental dataset API is under:

``` text
/api/dataset
```

### Positions

``` http
GET    /api/dataset/positions
POST   /api/dataset/positions
DELETE /api/dataset/positions/{position_id}
```

### Samples

``` http
GET    /api/dataset/samples
POST   /api/dataset/samples
PUT    /api/dataset/samples/{sample_id}
DELETE /api/dataset/samples/{sample_id}
```

### Prediction

``` http
POST /api/dataset/samples/{sample_id}/predict
POST /api/dataset/samples/predict-all
```

The prediction endpoint excludes the current sample from its reference
set.

### Summary

``` http
GET /api/dataset/summary
```

Returns total samples, labeled samples, evaluated predictions,
correct/incorrect counts, accuracy, position distribution,
target-presence distribution, and distance distribution.

### Exports

``` http
GET /api/dataset/export/features
GET /api/dataset/export/predictions
```

The original measurement system remains available through the existing
measurement routes, including:

``` text
/api/analyze
/api/measurements
/api/positions
```

plus its feedback, discard/restore, and audio operations.

## 13. Research Dashboard

The research dashboard contains views for:

-   Dataset overview
-   Prediction behaviour
-   Position analysis
-   Distance effects
-   Environmental conditions
-   Acoustic features
-   PCA visualization

The dashboard is intended for research analysis rather than only final
prediction display.

## 14. Data Flow

``` text
User selects position
        ↓
Target/distance metadata
        ↓
Frontend generates chirp
        ↓
Phone speaker plays chirp
        ↓
Microphone records response
        ↓
WAV uploaded
        ↓
Preprocessing
        ↓
Feature extraction
        ↓
SQLite dataset storage
        ↓
Prediction
        ↓
Reference fingerprints
        ↓
KNN distance calculation
        ↓
Weighted voting
        ↓
Position + confidence
        ↓
Ground-truth evaluation
        ↓
Dashboard / CSV
```

## 15. Evaluation Methodology

The current benchmark uses **leave-one-out evaluation**.

For each sample:

``` text
Current sample
    ↓
Ground-truth position known
    ↓
Remove current sample from references
    ↓
Compare with remaining samples
    ↓
Select nearest neighbours
    ↓
Predict position
    ↓
Compare prediction with ground truth
```

The same protocol is used for the handcrafted baseline and STFT/PSD
experiment.

## 16. Research Roadmap

### Stage 1 --- Basic acoustic localization

**Completed**

``` text
Chirp → Recording → Features → KNN → Position
```

### Stage 2 --- Acoustic fingerprint comparison

**Current**

Compare handcrafted features against STFT/PSD and investigate:

-   confusion matrices
-   sample-level agreement/disagreement
-   confidence
-   nearest neighbours
-   statistical significance
-   temporal STFT/PSD representations
-   appropriate dimensionality reduction

### Stage 3 --- Echo/reflection analysis

**Planned**

Investigate:

-   cross-correlation
-   echo detection
-   impulse-response analysis
-   time-of-arrival
-   dominant-reflector analysis

Concept:

``` text
Chirp
 ↓
Direct/reflected paths
 ↓
Microphone
 ↓
Correlation / echo detection
 ↓
Delay estimation
 ↓
Physical distance information
```

### Stage 4 --- Distance estimation

**Planned**

Use acoustic propagation/reflection information to estimate distance,
initially using controlled distance classes such as:

``` text
15 cm
30 cm
45 cm
...
```

Evaluation should use distance error in addition to classification
accuracy.

### Stage 5 --- Target/person detection

**Planned**

Distinguish:

``` text
Target present
Target absent
Uncertain
```

This requires controlled target-present and target-absent recordings.

### Stage 6 --- Integrated localization

**Future**

Combine:

``` text
Target detection
      +
Distance estimation
      +
Spatial localization
```

into a unified system:

``` text
Target: Detected
Distance: ~X cm
Position: Region/Position Y
Confidence: Z%
```

## 17. Future Dataset Expansion

Later experiments should vary:

-   target presence
-   target distance
-   target position
-   target orientation
-   phone orientation
-   background noise
-   environmental conditions
-   reflecting surfaces/materials
-   repeated trials
-   potentially different smartphone devices

This will test robustness and generalization beyond the initial
controlled experiment.

## 18. Current Limitations

The current system does **not yet** provide:

-   robust person detection
-   continuous distance estimation
-   guaranteed physical coordinate estimation
-   environment-independent localization
-   multi-device generalization
-   complete echo-based ranging
-   production-grade real-time localization
-   floor-plan reconstruction

The demonstrated capability at the current checkpoint is **experimental
acoustic position classification using fingerprint-based methods**.

## 19. Running the Project

### Backend

From the repository root:

``` powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend:

``` text
http://localhost:8000
```

### Frontend

``` powershell
cd frontend
npm install
npm run dev
```

For smartphone microphone access, the frontend can be exposed through
the configured HTTPS Cloudflare tunnel.

## 20. Evaluation Script

From `backend/`:

``` powershell
python scripts/evaluate_dataset.py
```

The evaluation script can recalculate representations from stored WAV
recordings and perform leave-one-out evaluation.

The STFT/PSD evaluation output is written under:

``` text
backend/data/dataset/evaluation/stft_psd_results.csv
```

## 21. Generated Data and Git

The experimental dataset is intentionally excluded from Git:

``` gitignore
backend/data/dataset/
```

This prevents local databases and raw recordings from being committed to
the repository.

Generated research artifacts can include:

``` text
web_dataset_features.csv
web_dataset_predictions.csv
stft_psd_results.csv
```

## 22. Research Methodology

The project follows an incremental experimental process:

``` text
Baseline
   ↓
Measure
   ↓
Change one representation/component
   ↓
Evaluate under the same protocol
   ↓
Analyze differences
   ↓
Understand acoustic behaviour
   ↓
Select next experiment
```

The current progression is:

``` text
Acoustic signal
      ↓
Handcrafted acoustic fingerprint
      ↓
Weighted KNN localization
      ↓
STFT/PSD fingerprint
      ↓
Echo/correlation features
      ↓
Distance estimation
      ↓
Target detection
      ↓
Combined localization
```

## 23. Key Results

  -----------------------------------------------------------------------------
  Experiment            Samples Representation    Model                Accuracy
  ------------ ---------------- ----------------- ------------ ----------------
  Baseline                  200 12 handcrafted    Weighted KNN       **82.50%**
                                features                       

  STFT/PSD                  200 427-dimensional   Weighted KNN       **81.50%**
                                STFT/PSD                       
  -----------------------------------------------------------------------------

The 82.5% result is the current quantitative baseline. The 81.5%
STFT/PSD result is an experimental comparison, not a replacement
baseline.

## 24. Project at a Glance

``` text
                 ACOUSTIC LOCALIZATION
                          │
                          ▼
                 15–20 kHz chirp
                          │
                          ▼
               Smartphone speaker/mic
                          │
                          ▼
                   200 WAV samples
                          │
                          ▼
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
       Handcrafted                  STFT/PSD
        12 features                427 dimensions
             │                         │
             ▼                         ▼
         Weighted KNN              Weighted KNN
             │                         │
             ▼                         ▼
          82.50%                    81.50%
             │                         │
             └────────────┬────────────┘
                          ▼
                 Current research
                          │
                          ▼
              Improve fingerprint
                          │
                          ▼
              Echo / correlation
                          │
                          ▼
              Distance estimation
                          │
                          ▼
              Target detection
                          │
                          ▼
            Integrated localization
```

## 25. One-Paragraph Project Description

Acoustic Localization is a smartphone-based research prototype that uses
controlled 15--20 kHz acoustic chirps, microphone recordings, digital
signal processing, and machine learning to investigate spatial
localization. The current system provides an end-to-end data collection
and evaluation platform and implements weighted KNN acoustic fingerprint
localization across 10 spatial positions using 200 recordings, achieving
82.5% leave-one-out accuracy with 12 handcrafted acoustic features. A
427-dimensional STFT/PSD fingerprint representation has also been
implemented and evaluated at 81.5%. The current research is focused on
understanding these representations and progressing toward echo-based
distance estimation, target/person detection, and integrated target
localization.

## 26. Final Research Questions

The project is ultimately moving from:

> **Can acoustic measurements distinguish spatial positions?**

toward:

> **Can a single smartphone use its own speaker and microphone to detect
> a nearby target, estimate its distance, and determine where it is
> located?**

These questions define the next stage of the BTP.


## Running the Project

### 1. Start the Backend

Open a terminal in the backend directory:

```powershell


cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

The backend will run on:

http://localhost:8000

Keep this terminal running.

2. Start the Frontend

Open a second terminal:

cd frontend
npm run dev -- --host 0.0.0.0

The frontend will run on:

http://localhost:5173/

Keep this terminal running.

3. Start the Cloudflare HTTPS Tunnel

Open a third terminal:

cloudflared tunnel --protocol http2 --url http://localhost:5173

Cloudflare will generate an HTTPS URL similar to:

https://xxxx-xxxx.trycloudflare.com

Keep this terminal running.

Accessing the Application

On Laptop:

http://localhost:5173/

On Mobile:

Open the HTTPS URL generated by Cloudflare:

https://xxxx-xxxx.trycloudflare.com

The Cloudflare HTTPS tunnel is used for mobile testing because browser microphone access requires a secure HTTPS context.

Important

The Cloudflare URL is temporary and changes whenever the tunnel is restarted. Do not hard-code the generated trycloudflare.com URL in the README.

The frontend API configuration should point to the backend API URL, while the Cloudflare frontend URL is used to access the application from a mobile device.