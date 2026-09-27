Acoustic Localization Using Smartphone Audio

B.Tech Project (BTP) / Research Prototype
Smartphone-based acoustic sensing for spatial localization, target detection, and distance estimation.

1. Project Overview

Acoustic Localization is a research prototype investigating whether a smartphone's own speaker and microphone can be used as an active acoustic sensing system to infer the location and distance of a nearby target.

The project is being developed incrementally as an experimental research system rather than a production-ready localization product.

The long-term pipeline is:

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
Target detection
   ↓
Distance estimation
   ↓
Spatial localization
   ↓
Final target location

The current implementation has already established an end-to-end experimental platform for recording, feature extraction, position prediction, distance prediction, evaluation, and research-data export.

2. Final Project Goal

The intended final system should:

Emit a controlled acoustic signal from a smartphone speaker.
Record the acoustic response using the smartphone microphone.
Determine whether a target/person is present.
Estimate the target's approximate distance from the phone.
Determine the target's spatial position at an experimentally justified granularity.
Combine target detection, distance estimation, and localization into one pipeline.

A conceptual final output is:

Target detected
Distance: approximately 20 cm
Location: Position / Region X
Confidence: Z%

The exact spatial granularity remains a research question. The system may ultimately operate using discrete spatial regions, distance ranges, or finer estimates.

3. Current Project Status
3.1 Completed System Components

The following components are implemented:

Controlled approximately 1-second, 15–20 kHz chirp generation.
Smartphone/browser microphone recording.
React + TypeScript frontend.
FastAPI/Python backend.
Audio preprocessing.
Handcrafted acoustic feature extraction.
Dedicated experimental dataset subsystem.
SQLite storage.
Raw WAV storage.
Weighted KNN acoustic fingerprint localization.
Leave-one-out evaluation.
Prediction confidence.
Research dashboard.
Dataset collection interface.
Predict-one workflow.
Predict-all workflow.
Feature CSV export.
Prediction CSV export.
STFT/PSD fingerprint implementation.
STFT/PSD benchmark comparison.
Experimental target-presence metadata.
Experimental distance metadata.
Distance regression using Extra Trees.
Leakage-aware distance prediction for individual samples.
Position + distance prediction in the dataset prediction workflow.
Distance error reporting.
3.2 Current Research Position

The project has progressed beyond the initial position-classification benchmark.

The current research pipeline contains three related experiments:

Experiment 1
12 handcrafted features
        ↓
Weighted KNN
        ↓
Spatial position classification
        ↓
82.50% LOOCV accuracy
Experiment 2
427-dimensional STFT/PSD fingerprint
        ↓
Weighted KNN
        ↓
Spatial position classification
        ↓
81.50% LOOCV accuracy
Experiment 3 / EXP-013
12 acoustic features
        ↓
Position classification
        +
Target-presence analysis
        +
Distance regression
        ↓
Experimental validation

The latest integration also allows the application to run a position prediction and distance prediction together.

3.3 Important Scientific Limitation

The current distance model is a supervised feature-to-distance regression model.

It should not be described as a completed physical echolocation / time-of-flight system.

A true propagation-delay-based ranging experiment would require estimating a measurable acoustic delay, for example using matched filtering or cross-correlation, and relating that delay to propagation distance under controlled assumptions.

That experiment remains a planned research stage.

4. System Architecture
                    ┌──────────────────────────┐
                    │      Smartphone/Web      │
                    │    React + TypeScript    │
                    └────────────┬─────────────┘
                                 │
                          Generate chirp
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │    Smartphone Speaker    │
                    └────────────┬─────────────┘
                                 │
                     Acoustic propagation
                       + reflection/echoes
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │  Smartphone Microphone   │
                    └────────────┬─────────────┘
                                 │
                               WAV
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │       FastAPI API        │
                    │      Python Backend      │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
       Preprocessing      Feature Extraction     Storage
              │                  │
              │          ┌───────┴────────┐
              │          ▼                ▼
              │   Handcrafted        STFT / PSD
              │     Features          Fingerprint
              │          │                │
              └──────────┴───────┬────────┘
                                 ▼
                         Position Prediction
                                 │
                                 ▼
                         Distance Prediction
                                 │
                                 ▼
                    Position + Distance + Error
                                 │
                                 ▼
                         Dashboard / CSV
5. Technology Stack
Layer	Technology
Frontend	React, TypeScript, Vite
Backend	Python, FastAPI, Uvicorn
Audio Processing	Librosa, NumPy, SciPy
Machine Learning	scikit-learn, Weighted KNN, Extra Trees
Database	SQLite
Audio Format	WAV
Mobile Access	HTTPS via Cloudflare Tunnel
Export	CSV
Development	VS Code, PowerShell
Version Control	Git / GitHub
6. Repository Structure
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
│   │   │   ├── predictor.py
│   │   │   └── distance_predictor.py
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
6.1 Important Modules
Original measurement system
backend/app/api/routes.py
backend/app/ml/model.py
backend/app/ml/predictor.py
backend/app/storage.py

This system provides the original measurement workflow and routes such as:

/api/analyze
/api/measurements
/api/positions
Experimental dataset system
backend/app/api/dataset_routes.py
backend/app/dataset/
frontend/src/pages/CollectData.tsx
frontend/src/lib/datasetApi.ts

This system is used for controlled research experiments, dataset collection, prediction, evaluation, and CSV export.

Distance prediction
backend/app/ml/distance_predictor.py

This module implements the current supervised distance-regression experiment using Extra Trees and the controlled distance-labelled dataset.

7. Important Separation Between the Two Systems

The repository intentionally contains two related but separate workflows.

A. Original Measurement System
backend/app/api/routes.py
backend/app/ml/
backend/app/storage.py

Used for the original measurement and feedback workflow.

B. Experimental Dataset System
backend/app/api/dataset_routes.py
backend/app/dataset/
frontend/src/pages/CollectData.tsx
frontend/src/lib/datasetApi.ts

Used for controlled experiments.

Keeping these systems separated makes it possible to change research experiments without unnecessarily breaking the original measurement workflow.

8. Acoustic Signal

The current controlled experiment uses an approximately:

Duration:       ~1 second
Frequency:      15–20 kHz
Signal:         Chirp

Measurement flow:

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
Predict

The controlled signal makes measurements from different experimental conditions comparable.

9. Experimental Dataset
9.1 Original Position Benchmark

The original benchmark contains:

Total recordings:        200
Spatial positions:       10
Recordings per position: 20
Position	Samples
Pos 1	20
Pos 2	20
Pos 3	20
Pos 4	20
Pos 5	20
Pos 6	20
Pos 7	20
Pos 8	20
Pos 9	20
Pos 10	20
Total	200

The dataset stores:

Sample ID
Timestamp
Position
Target-presence metadata
Distance metadata
Remarks
Raw WAV recording
Extracted features
Prediction
Confidence
Evaluation status

Target labels supported by the collection interface:

Yes
No
Can't say

Distance metadata can contain values such as:

15 cm
30 cm
45 cm
Unknown

The original 200-sample benchmark is primarily a position-classification experiment.

10. Environment Layout of the 200-Sample Benchmark

The original 10-position dataset was collected across different environments:

Positions 1–5  → Room 1
Positions 6–9  → Room 2
Position 10    → Open area

The open-area position contains additional environmental activity, including people speaking and comparatively higher background noise.

This is important when interpreting per-position performance because acoustic differences can arise from both spatial geometry and environmental conditions.

11. Baseline Acoustic Features

The baseline representation contains 12 handcrafted features:

RMS dB
Peak dB
Spectral centroid
Spectral bandwidth
Spectral rolloff
Spectral flatness
Zero-crossing rate
15–16 kHz energy
16–17 kHz energy
17–18 kHz energy
18–19 kHz energy
19–20 kHz energy

These features provide a compact representation of the recorded acoustic response.

12. Baseline Position Model

The baseline uses normalized distance-weighted KNN.

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

Evaluation excludes the current sample from the reference set.

13. Baseline Position Result

The original 200-sample benchmark produced:

Samples:       200
Evaluated:     200
Correct:       165
Incorrect:      35
Accuracy:      82.50%

Per-position results:

Position	Correct	Accuracy
Pos 1	17/20	85%
Pos 2	19/20	95%
Pos 3	18/20	90%
Pos 4	19/20	95%
Pos 5	13/20	65%
Pos 6	15/20	75%
Pos 7	18/20	90%
Pos 8	17/20	85%
Pos 9	12/20	60%
Pos 10	17/20	85%

Common confusion patterns included:

Pos 9 → Pos 8
Pos 6 → Pos 7
Pos 5 → Pos 2
Pos 9 → Pos 10
Pos 8 → Pos 10

These patterns indicate that some positions have overlapping acoustic signatures under the experimental conditions.

14. STFT / PSD Experiment

A second acoustic representation was implemented using Short-Time Fourier Transform and Power Spectral Density.

Parameters:

N_FFT       = 4096
HOP_LENGTH  = 1024
Frequency   = 15–20 kHz

Pipeline:

WAV
 ↓
Remove DC
 ↓
STFT
 ↓
Power = |STFT|²
 ↓
Restrict to 15–20 kHz
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

The same 200 recordings and leave-one-out evaluation protocol were used.

STFT/PSD Result
Samples:       200
Evaluated:     200
Correct:       163
Incorrect:      37
Accuracy:      81.50%
Dimensions:     427
Representation	Dimensions	Model	Accuracy
Handcrafted	12	Weighted KNN	82.50%
STFT/PSD	427	Weighted KNN	81.50%

The STFT/PSD representation did not improve overall accuracy in this experiment.

A key research hypothesis is that averaging the PSD over time may remove useful information about the chirp's time-frequency evolution. This is a hypothesis for further testing, not an established conclusion.

15. EXP-013: Target and Distance Experiment

A separate experiment, EXP-013, was created to move beyond the original 10-position benchmark and investigate target presence and distance.

Dataset:

Total recordings:          220
Positions:                   7
Target present:            185
Target absent:              35

Known target-present distance classes include:

5 cm
10 cm
15 cm
20 cm
25 cm
30 cm

The experiment uses the same family of handcrafted acoustic features for its initial supervised analysis.

16. EXP-013 Position Classification

Using the EXP-013 data, the position classifier achieved:

Correct:     117
Total:       220
Accuracy:    53.18%

There are 7 positions, so the nominal balanced chance level for a uniform 7-class problem is approximately:

14.29%

Per-position accuracy observed in the experiment:

Position	Accuracy
P1	10.0%
P2	68.6%
P3	40.0%
P4	42.9%
P5	94.3%
P6	31.4%
P7	54.3%

Important confusion patterns included:

P4 ↔ P6
P3 → P2
P6 → P3 / P7

This experiment demonstrates that performance is highly dependent on the experimental setup and dataset composition. The 82.50% result from the original benchmark should therefore not be treated as a universal localization accuracy.

17. EXP-013 Target-Presence Analysis

EXP-013 also contains target-present and target-absent recordings.

The initial analysis showed that raw classification accuracy could appear around the low-80% range while balanced performance was much lower, around 50%.

Therefore:

The current EXP-013 data does not justify claiming robust target/person detection.

The imbalance between target-present and target-absent samples must be considered when evaluating detection performance.

Future target detection experiments should use a controlled and better-balanced target-present vs target-absent dataset and report metrics such as:

Accuracy
Precision
Recall
F1-score
Confusion matrix
Balanced accuracy
ROC-AUC where appropriate
18. EXP-013 Acoustic-Distance Analysis

Correlation analysis on the handcrafted features showed that some high-frequency energy bands contained measurable relationships with distance.

For example:

18–19 kHz feature correlation ≈ -0.314
19–20 kHz feature correlation ≈ -0.283

These correlations are not strong enough by themselves to establish a reliable physical distance relationship.

They are useful as evidence that distance-related information may exist in the acoustic representation and can motivate supervised regression experiments.

19. EXP-013 PCA Analysis

PCA was also used to inspect whether the acoustic feature space naturally separates the experimental samples.

Observed explained variance:

PC1 = 65.39%
PC2 = 11.44%
PC3 =  8.35%

Therefore:

PC1 + PC2 ≈ 76.8%

The projected samples showed substantial overlap.

This suggests that the 12-dimensional handcrafted feature space does not produce cleanly separated clusters for all experimental conditions.

PCA is used here as an exploratory visualization tool and is not itself a localization model.

20. Distance Regression

The project now includes a supervised distance-regression experiment.

The current training subset contains:

185 target-present recordings
Known distances
5, 10, 15, 20, 25, 30 cm

The model uses the same family of handcrafted acoustic features.

20.1 Model

The current distance predictor uses:

ExtraTreesRegressor

with preprocessing that handles non-finite feature values through median imputation.

The evaluation uses a leave-one-position-out (LOPO) protocol for the experimental distance model.

The reason for selecting Extra Trees was empirical:

It produced the lowest LOPO MAE among the tested regression models on this dataset.

It was not selected because Extra Trees is universally superior for acoustic ranging.

21. Distance Regression Results

Current LOPO results:

Model	MAE (cm)	RMSE (cm)	R²	±2 cm	±5 cm	±10 cm
Extra Trees	6.777	8.368	0.067	19.459%	41.081%	76.216%
Ridge	7.043	10.467	-0.460	—	—	—
Gradient Boosting	7.103	9.064	-0.095	—	—	—
Random Forest	7.181	9.003	-0.080	—	—	—
KNN	7.270	8.797	-0.031	—	—	—

The current Extra Trees result is:

MAE:       6.777 cm
RMSE:      8.368 cm
R²:        0.067
Within ±2 cm:   19.459%
Within ±5 cm:   41.081%
Within ±10 cm:  76.216%

The low R² indicates that the current features and dataset do not yet provide a strong continuous distance model.

The model should therefore be treated as an experimental baseline rather than a completed ranging solution.

22. Distance Error by Ground-Truth Distance

The current Extra Trees experiment showed different errors across distance classes:

Ground-truth distance	MAE
5 cm	10.01 cm
10 cm	4.44 cm
15 cm	3.46 cm
20 cm	3.24 cm
25 cm	6.65 cm
30 cm	12.32 cm

This indicates that the current model does not perform uniformly across the tested distance range.

In particular, the smallest and largest tested distances showed larger errors than the middle distance classes.

23. Example Distance Predictions

Representative examples from the experiment include:

Actual 30 cm → Predicted ≈ 12.26 cm
Actual  5 cm → Predicted ≈ 21.51 cm
Actual 10 cm → Predicted ≈ 10.01 cm
Actual 20 cm → Predicted ≈ 20.02 cm

These examples illustrate why aggregate error metrics are necessary.

A model can predict some individual distances closely while making large errors on other samples.

24. Distance Prediction Methodology

The current distance model does not calculate distance directly from the speed of sound.

Instead, it learns a statistical mapping:

Recorded WAV
     ↓
Preprocessing
     ↓
12 acoustic features
     ↓
Trained regression model
     ↓
Predicted distance in cm

Conceptually:

features → learned relationship → distance

The model learns this relationship from recordings whose distances are already known.

For example, training data contains:

Feature vector A → 5 cm
Feature vector B → 10 cm
Feature vector C → 15 cm
...
Feature vector F → 30 cm

The regression model learns patterns in the feature space associated with those labelled distances.

This is fundamentally different from physical time-of-flight ranging.

25. Physical Echolocation / Time-of-Flight: Future Method

A more physically interpretable ranging system would use the transmitted chirp as a reference.

Conceptually:

Transmitted chirp
       +
Recorded microphone signal
       ↓
Cross-correlation / matched filtering
       ↓
Detect direct / reflected peaks
       ↓
Estimate propagation delay Δt
       ↓
Distance estimation

For a simple round-trip reflection model:

d = c × Δt / 2

where:

d  = target distance
c  = speed of sound
Δt = measured round-trip delay

This requires careful experimental control because the microphone recording contains:

Direct acoustic leakage
Speaker-to-microphone coupling
Room reflections
Multiple paths
Background noise
Hardware latency
Device-specific processing

This is the planned direction for a more physically grounded distance-estimation experiment.

26. Current Distance Prediction Integration

The application now integrates distance prediction into the dataset prediction workflow.

For a single sample:

Sample
 ↓
Extract / retrieve features
 ↓
Position prediction
 ↓
Distance model
 ↓
Exclude current sample from distance-training references
 ↓
Predicted distance
 ↓
Compare with known distance when available
 ↓
Distance error

For bulk prediction:

All dataset samples
       ↓
For each sample
       ↓
Position prediction
       +
Leakage-aware distance prediction
       ↓
Results

The current sample is excluded from the distance model's training set when making its own prediction.

This is important because including the sample being evaluated in its own training set would cause data leakage and could make the reported prediction artificially optimistic.

27. Prediction Output

The prediction workflow can provide fields such as:

Predicted position
Position confidence
Ground-truth position
Evaluation status

Predicted distance
Ground-truth distance
Distance error

Conceptually:

Position:       P4
Confidence:     87.2%

Distance:       18.4 cm
Ground truth:   20.0 cm
Error:           1.6 cm

The exact values depend on the recording being evaluated.

28. Experimental Dataset API

The experimental dataset API is under:

/api/dataset
28.1 Positions
GET    /api/dataset/positions
POST   /api/dataset/positions
DELETE /api/dataset/positions/{position_id}
28.2 Samples
GET    /api/dataset/samples
POST   /api/dataset/samples
PUT    /api/dataset/samples/{sample_id}
DELETE /api/dataset/samples/{sample_id}
28.3 Prediction
POST /api/dataset/samples/{sample_id}/predict
POST /api/dataset/samples/predict-all

These endpoints support the position and distance prediction workflow.

28.4 Summary
GET /api/dataset/summary

The summary provides dataset-level information such as:

Total samples
Labelled samples
Evaluated predictions
Correct/incorrect counts
Position accuracy
Position distribution
Target-presence distribution
Distance distribution
28.5 Exports
GET /api/dataset/export/features
GET /api/dataset/export/predictions

Generated research artifacts include:

web_dataset_features.csv
web_dataset_predictions.csv
stft_psd_results.csv
29. Original Measurement API

The original measurement system remains available through:

/api/analyze
/api/measurements
/api/positions

It also contains the original measurement feedback, audio, discard/restore, and history operations.

The original and experimental APIs should be treated as separate workflows.

30. Research Dashboard

The research dashboard provides views for:

Dataset overview
Prediction behaviour
Position analysis
Distance effects
Environmental conditions
Acoustic features
PCA visualization

The dashboard is intended for research analysis rather than only final prediction display.

31. Data Collection Interface

The experimental collection interface supports:

Create/select position
        ↓
Select target presence
        ↓
Select distance
        ↓
Add remarks
        ↓
Generate chirp
        ↓
Record audio
        ↓
Save sample
        ↓
Extract features
        ↓
Run prediction
        ↓
Inspect nearest samples
        ↓
Evaluate prediction

The interface also supports:

Sample editing
Sample deletion
WAV playback
Dataset summaries
Predict-all
Feature CSV download
Prediction CSV download
32. Data Flow
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
Position prediction
        ↓
Reference fingerprints
        ↓
KNN distance calculation
        ↓
Weighted voting
        ↓
Position + confidence
        ↓
Distance regression
        ↓
Predicted distance + error
        ↓
Ground-truth evaluation
        ↓
Dashboard / CSV
33. Evaluation Methodology
33.1 Position Evaluation

The original position benchmark uses leave-one-out evaluation.

For each sample:

Current sample
      ↓
Ground-truth position known
      ↓
Remove current sample from reference set
      ↓
Compare with remaining samples
      ↓
Select nearest neighbours
      ↓
Predict position
      ↓
Compare with ground truth

The same protocol is used for the handcrafted and STFT/PSD position experiments.

33.2 Distance Evaluation

The EXP-013 distance experiment uses a leave-one-position-out evaluation strategy.

The purpose is to evaluate generalization across spatial groups rather than allowing the same position's recordings to dominate the training data.

For integrated single-sample prediction, the current sample is explicitly excluded from the distance-training references.

34. Research Leakage Considerations

The project explicitly avoids evaluating a sample using itself as a training reference.

For position KNN:

Current sample
     X
Reference set

The current sample is removed before nearest-neighbour prediction.

For distance regression:

Current sample
     X
Distance training data

The current sample is excluded when the application performs a prediction for that sample.

This separation is necessary for meaningful experimental evaluation.

35. Research Roadmap
Stage 1 — Basic Acoustic Localization

Completed

Chirp
  ↓
Recording
  ↓
Features
  ↓
KNN
  ↓
Position

Current benchmark:

82.50% LOOCV accuracy
Stage 2 — Acoustic Fingerprint Comparison

Completed / ongoing analysis

Compare:

12 handcrafted features
        VS
427-dimensional STFT/PSD fingerprint

Research questions:

Which samples do the models agree on?
Which samples do they disagree on?
Which positions are acoustically ambiguous?
How does confidence change?
What nearest neighbours cause errors?
Does temporal averaging remove useful chirp information?
Which dimensionality-reduction methods are appropriate?
Stage 3 — EXP-013 Target and Distance Experiment

Implemented

Investigate:

Target presence
Distance metadata
Position classification
Distance regression

Current distance regression baseline:

Extra Trees
MAE = 6.777 cm

The experiment remains limited by the current dataset size, class distribution, and acoustic variability.

Stage 4 — Echo / Reflection Analysis

Next major research stage

Investigate:

Cross-correlation
Matched filtering
Echo detection
Impulse-response analysis
Time-of-arrival
Dominant-reflector analysis

Concept:

Chirp
  ↓
Direct/reflected paths
  ↓
Microphone
  ↓
Correlation / matched filtering
  ↓
Delay estimation
  ↓
Physical distance information
Stage 5 — Physically Grounded Distance Estimation

Planned

Move from purely supervised feature-to-distance regression toward propagation-delay-based ranging.

Initial controlled distances can include:

5 cm
10 cm
15 cm
20 cm
25 cm
30 cm

The evaluation should report:

MAE
RMSE
Maximum error
Median error
Error distribution
Error by distance
Percentage within ±2 cm
Percentage within ±5 cm
Percentage within ±10 cm
Stage 6 — Target / Person Detection

Planned

Build a controlled target-presence dataset:

Target present
Target absent

Potential models:

Threshold-based baseline
Logistic Regression
SVM
Random Forest
KNN
Other lightweight classifiers

Evaluation should include:

Precision
Recall
F1-score
Balanced accuracy
Confusion matrix
ROC-AUC where appropriate
Stage 7 — Integrated Localization

Future

Combine:

Target detection
       +
Distance estimation
       +
Spatial localization

into:

Target: Detected
Distance: ~X cm
Position: Region / Position Y
Confidence: Z%
36. Future Dataset Expansion

Future experiments should vary:

Target presence
Target distance
Target position
Target orientation
Phone orientation
Background noise
Environmental conditions
Reflecting surfaces/materials
Repeated trials
Smartphone devices

The goal is to determine whether the learned acoustic patterns generalize beyond the initial controlled setup.

37. Current Limitations

The current system does not yet provide:

Robust person detection.
Reliable continuous physical distance estimation.
Guaranteed physical coordinate estimation.
Environment-independent localization.
Multi-device generalization.
Complete echo-based ranging.
Production-grade real-time localization.
Floor-plan reconstruction.

The demonstrated capability at the current checkpoint is:

Experimental acoustic position classification using fingerprint-based methods, with an additional supervised distance-regression prototype.

The distance-regression prototype should not be confused with completed physical echolocation.

38. Important Research Interpretation

The current results should be interpreted as dataset- and environment-specific experimental results.

In particular:

82.50% on the original 200-sample benchmark

does not imply that the system can localize a person with 82.5% accuracy in arbitrary environments.

Similarly:

6.777 cm MAE

from EXP-013 does not imply that the smartphone can physically measure distance to a person with 6.777 cm accuracy in general.

These results are baselines for the controlled experiments that produced them.

39. Running the Project
39.1 Backend

From the repository root:

cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Backend:

http://localhost:8000
39.2 Frontend

Open a second terminal:

cd frontend
npm install
npm run dev

For smartphone microphone access, the frontend can be exposed through the configured HTTPS Cloudflare tunnel.

40. Development Validation

Before committing changes:

cd frontend
npx tsc --noEmit
npm run build

Backend can be started with:

cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
41. Evaluation Script

From backend/:

python scripts/evaluate_dataset.py

The evaluation script can recalculate representations from stored WAV recordings and perform leave-one-out evaluation.

The STFT/PSD evaluation output is written under:

backend/data/dataset/evaluation/stft_psd_results.csv
42. Research Data Files

Important generated research files include:

web_dataset_features.csv
web_dataset_predictions.csv
stft_psd_results.csv

For EXP-013, the research outputs include:

dataset_features_EXP-013.csv
dataset_predictions_EXP-013.csv

These files are used for offline analysis, visualizations, PCA, confusion matrices, distance-regression evaluation, and model comparison.

Large raw datasets and recordings are intentionally kept outside the Git repository where appropriate.

43. Generated Data and Git

The experimental dataset is intentionally excluded from Git:

backend/data/dataset/

This prevents local databases and raw recordings from being committed to the repository.

Generated research artifacts can be retained separately when required for analysis.

44. Research Methodology

The project follows an incremental experimental process:

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

The research progression is:

Acoustic signal
      ↓
Handcrafted acoustic fingerprint
      ↓
Weighted KNN localization
      ↓
STFT/PSD fingerprint
      ↓
Target/distance experiment
      ↓
Echo/correlation features
      ↓
Physical distance estimation
      ↓
Target detection
      ↓
Combined localization

The intention is to avoid jumping directly to a complex deep-learning model before understanding the signal and dataset behaviour.

45. Key Quantitative Results
Original Position Benchmark
Experiment	Samples	Representation	Model	Evaluation	Accuracy
Baseline	200	12 handcrafted features	Weighted KNN	LOOCV	82.50%
STFT/PSD	200	427-dimensional fingerprint	Weighted KNN	LOOCV	81.50%
EXP-013
Experiment	Samples	Result
Position classification	220	53.18% accuracy
Target-present samples	185	Used for distance regression
Target-absent samples	35	Used in target-presence analysis
Distance regression	185	Extra Trees MAE = 6.777 cm

The EXP-013 position result is not directly comparable to the original 200-sample 10-position benchmark because the dataset, number of positions, target conditions, and experimental setup differ.

46. Model Summary
Position Localization
Input:
    WAV recording

Features:
    12 handcrafted acoustic features
    OR
    427-dimensional STFT/PSD fingerprint

Model:
    Distance-weighted KNN

Evaluation:
    Leave-one-out

Output:
    Position + confidence
Distance Regression
Input:
    12 handcrafted acoustic features

Training:
    Target-present samples with known distances

Model:
    Extra Trees Regressor

Evaluation:
    Leave-one-position-out

Output:
    Estimated distance in cm
Future Physical Ranging
Input:
    Transmitted chirp + microphone recording

Signal processing:
    Matched filtering / cross-correlation

Output:
    Propagation delay

Physical model:
    Distance from acoustic time-of-flight
47. Why Extra Trees Is Currently Used for Distance Prediction

Several regression models were evaluated on the EXP-013 distance task.

Extra Trees produced the lowest observed LOPO MAE:

Extra Trees:       6.777 cm
Ridge:             7.043 cm
Gradient Boosting: 7.103 cm
Random Forest:     7.181 cm
KNN:               7.270 cm

Therefore Extra Trees is the current experimental model.

The selection is empirical and specific to the current dataset and evaluation protocol.

It should be re-evaluated when:

More recordings are collected.
New acoustic features are added.
Echo-based features are introduced.
The distance range is expanded.
Multiple devices are tested.
48. Research Questions

The project is currently investigating:

Position
Can acoustic fingerprints distinguish spatial positions?
Which acoustic features contain the most location information?
Why do some positions have overlapping fingerprints?
How much does the environment affect localization?
Does time-frequency information improve over handcrafted features?
Distance
Can acoustic features encode enough information for distance regression?
Are the observed correlations stable across experiments?
Can echo delays provide a more physically meaningful distance signal?
How much error is introduced by hardware and room reflections?
Target Detection
Can the acoustic response distinguish target-present from target-absent conditions?
How much do class imbalance and background noise affect detection?
Can controlled target experiments produce a robust classifier?
Integrated System
Can target presence, distance, and spatial position be inferred from the same acoustic measurement?
Can the system generalize across rooms, orientations, noise levels, and smartphones?
49. Recommended Experimental Progression

The research should progress in controlled stages:

1. Understand current handcrafted baseline
            ↓
2. Improve time-frequency representation
            ↓
3. Analyze reflections and echoes
            ↓
4. Estimate physical delay
            ↓
5. Validate distance under controlled conditions
            ↓
6. Build target-present / target-absent dataset
            ↓
7. Validate target detection
            ↓
8. Combine target + distance + position
            ↓
9. Test environmental/device robustness

Each stage should have its own dataset, evaluation protocol, and quantitative metrics.

50. Project at a Glance
                  ACOUSTIC LOCALIZATION
                           │
                           ▼
                     15–20 kHz chirp
                           │
                           ▼
                  Smartphone speaker/mic
                           │
                           ▼
                     Acoustic response
                           │
             ┌─────────────┴─────────────┐
             │                           │
             ▼                           ▼
       Handcrafted                    STFT/PSD
       12 features                  427 dimensions
             │                           │
             ▼                           ▼
       Weighted KNN                 Weighted KNN
             │                           │
             ▼                           ▼
          82.50%                      81.50%
             │                           │
             └─────────────┬─────────────┘
                           ▼
                    Research analysis
                           │
                           ▼
                    EXP-013 experiments
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           Position     Distance     Target
          analysis     regression   detection
              │            │            │
              └────────────┼────────────┘
                           ▼
                    Echo / correlation
                           │
                           ▼
                Physical distance estimate
                           │
                           ▼
                  Integrated localization
51. One-Paragraph Project Description

Acoustic Localization is a smartphone-based research prototype that uses controlled 15–20 kHz acoustic chirps, microphone recordings, digital signal processing, and machine learning to investigate spatial localization, target detection, and distance estimation. The current system provides an end-to-end data collection and evaluation platform and implements weighted KNN acoustic fingerprint localization across 10 spatial positions using 200 recordings, achieving 82.5% leave-one-out accuracy with 12 handcrafted acoustic features. A 427-dimensional STFT/PSD representation has also been implemented and evaluated at 81.5%. A separate EXP-013 experiment extends the research toward target presence and distance estimation using 220 recordings, with 185 known-distance target-present samples used for supervised distance regression. The current Extra Trees distance model achieves 6.777 cm LOPO MAE on that dataset. The next research stage is to investigate time-frequency structure, echo/correlation-based propagation delay, physically grounded distance estimation, controlled target detection, and finally integrated target + distance + spatial localization.

52. Final Research Question

The project is moving from:

Can acoustic measurements distinguish spatial positions?

toward:

Can a single smartphone use its own speaker and microphone to detect a nearby target, estimate its distance, and determine where it is located?

The current implementation provides the experimental foundation required to investigate that question systematically.

Project Repository

GitHub:

https://github.com/b23cs1015/acoustic-localization/
Current Checkpoint

Current demonstrated capability:

Acoustic recording
       ↓
Feature extraction
       ↓
Position classification
       +
Supervised distance regression
       ↓
Experimental evaluation

Next major research capability:

Chirp
  ↓
Echo / correlation analysis
  ↓
Propagation-delay estimation
  ↓
Physical distance estimation
  ↓
Target detection
  ↓
Integrated spatial localization


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


