export interface ChirpConfig {
  duration: number;
  startFrequency: number;
  endFrequency: number;
  amplitude: number;
}

export const DEFAULT_CHIRP_CONFIG: ChirpConfig = {
  duration: 1.0,
  startFrequency: 15000,
  endFrequency: 20000,
  amplitude: 0.5
};

export async function playChirp(
  audioContext: AudioContext,
  config: ChirpConfig = DEFAULT_CHIRP_CONFIG
): Promise<void> {
  const oscillator = audioContext.createOscillator();
  const gainNode = audioContext.createGain();

  oscillator.type = "sine";

  oscillator.frequency.setValueAtTime(
    config.startFrequency,
    audioContext.currentTime
  );

  oscillator.frequency.exponentialRampToValueAtTime(
    config.endFrequency,
    audioContext.currentTime + config.duration
  );

  gainNode.gain.setValueAtTime(
    0,
    audioContext.currentTime
  );

  gainNode.gain.linearRampToValueAtTime(
    config.amplitude,
    audioContext.currentTime + 0.01
  );

  gainNode.gain.setValueAtTime(
    config.amplitude,
    audioContext.currentTime + config.duration - 0.01
  );

  gainNode.gain.linearRampToValueAtTime(
    0,
    audioContext.currentTime + config.duration
  );

  oscillator.connect(gainNode);
  gainNode.connect(audioContext.destination);

  oscillator.start();

  oscillator.stop(
    audioContext.currentTime + config.duration
  );

  await new Promise<void>((resolve) => {
    oscillator.addEventListener("ended", () => {
      resolve();
    });
  });
}