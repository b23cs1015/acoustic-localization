# Acoustic Localization

Prototype for the B.Tech project:

> Audio-Based Indoor Localization Using Acoustic Signatures

## Architecture

The system consists of:

- React + Vite frontend
- Python + FastAPI backend
- Browser microphone
- Browser-generated acoustic chirp
- Server-side signal processing
- Acoustic feature extraction
- ML prediction

## Flow

Browser:

1. Request microphone permission.
2. Start recording.
3. Play a 1-second 15–20 kHz chirp.
4. Record the microphone response.
5. Encode the recording as WAV.
6. Send WAV to the backend.

Server:

1. Receive WAV.
2. Load audio.
3. Resample to 48 kHz.
4. Extract acoustic features.
5. Run ML prediction.
6. Return prediction and features.

## Development

### Frontend

```bash
cd frontend
npm install
npm run dev