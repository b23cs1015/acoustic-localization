export interface RoomMappingRecorderConfig {

  startFrequency: number;

  endFrequency: number;

  chirpDuration: number;

  amplitude: number;

  sampleRate: number;

}


export const DEFAULT_ROOM_MAPPING_CONFIG:
  RoomMappingRecorderConfig = {

  startFrequency: 15000,

  endFrequency: 20000,

  chirpDuration: 1.0,

  amplitude: 0.5,

  sampleRate: 48000,

};


export interface RoomMappingRecordingResult {

  audioBuffer: AudioBuffer;

  durationSeconds: number;

  sampleRate: number;

}


/**
 * Records the microphone while continuously
 * looping a 1-second 15–20 kHz chirp through
 * the device speaker.
 *
 * Recording continues until the user presses Stop.
 */
export class RoomMappingRecorder {

  private readonly config:
    RoomMappingRecorderConfig;


  private context:
    AudioContext | null = null;


  private stream:
    MediaStream | null = null;


  private source:
    MediaStreamAudioSourceNode | null = null;


  private processor:
    ScriptProcessorNode | null = null;


  private silentGain:
    GainNode | null = null;


  private chirpSource:
    AudioBufferSourceNode | null = null;


  private chirpGain:
    GainNode | null = null;


  private chunks:
    Float32Array[] = [];


  private startedAt = 0;


  private running = false;


  constructor(
    config:
      RoomMappingRecorderConfig =
        DEFAULT_ROOM_MAPPING_CONFIG
  ) {

    this.config =
      config;

  }


  get isRunning(): boolean {

    return this.running;

  }


  get elapsedSeconds(): number {

    if (
      !this.running ||
      this.startedAt === 0
    ) {

      return 0;

    }


    return (
      performance.now() -
      this.startedAt
    ) / 1000;

  }


  async start(): Promise<void> {

    if (this.running) {

      throw new Error(
        "Room mapping recording is already running."
      );

    }


    if (
      !navigator.mediaDevices?.getUserMedia
    ) {

      throw new Error(
        "Microphone access is not available in this browser. Use HTTPS or localhost."
      );

    }


    this.stream =
      await navigator.mediaDevices.getUserMedia({

        audio: {

          channelCount: 1,

          echoCancellation: false,

          noiseSuppression: false,

          autoGainControl: false,

        },

      });


    try {

      this.context =
        new AudioContext({

          sampleRate:
            this.config.sampleRate,

        });


      await this.context.resume();


      this.source =
        this.context.createMediaStreamSource(
          this.stream
        );


      this.processor =
        this.context.createScriptProcessor(
          4096,
          1,
          1
        );


      this.silentGain =
        this.context.createGain();


      this.silentGain.gain.value =
        0;


      this.processor.onaudioprocess =
        (event) => {

          const input =
            event.inputBuffer.getChannelData(
              0
            );


          this.chunks.push(
            new Float32Array(input)
          );

        };


      this.source.connect(
        this.processor
      );


      this.processor.connect(
        this.silentGain
      );


      this.silentGain.connect(
        this.context.destination
      );


      this.startContinuousChirp();


      this.startedAt =
        performance.now();


      this.running =
        true;

    } catch (error) {

      this.cleanup();

      throw error;

    }

  }


  async stop():
    Promise<RoomMappingRecordingResult> {

    if (
      !this.running ||
      !this.context
    ) {

      throw new Error(
        "No room mapping recording is currently running."
      );

    }


    const context =
      this.context;


    this.stopContinuousChirp();


    if (
      this.source &&
      this.processor
    ) {

      try {

        this.source.disconnect(
          this.processor
        );

      } catch {
        // Already disconnected.
      }

    }


    if (
      this.processor &&
      this.silentGain
    ) {

      try {

        this.processor.disconnect(
          this.silentGain
        );

      } catch {
        // Already disconnected.
      }

    }


    if (this.silentGain) {

      try {

        this.silentGain.disconnect();

      } catch {
        // Already disconnected.
      }

    }


    const totalLength =
      this.chunks.reduce(
        (
          sum,
          chunk
        ) =>
          sum + chunk.length,
        0
      );


    const samples =
      new Float32Array(
        totalLength
      );


    let offset = 0;


    for (
      const chunk of this.chunks
    ) {

      samples.set(
        chunk,
        offset
      );

      offset +=
        chunk.length;

    }


    const sampleRate =
      context.sampleRate;


    const audioBuffer =
      context.createBuffer(
        1,
        samples.length,
        sampleRate
      );


    audioBuffer.copyToChannel(
      samples,
      0
    );


    const durationSeconds =
      samples.length /
      sampleRate;


    this.running =
      false;


    this.stopStreamTracks();


    try {

      await context.close();

    } catch {
      // Ignore already-closed context.
    }


    this.context = null;

    this.source = null;

    this.processor = null;

    this.silentGain = null;

    this.chirpSource = null;

    this.chirpGain = null;

    this.chunks = [];

    this.startedAt = 0;


    return {

      audioBuffer,

      durationSeconds,

      sampleRate,

    };

  }


  async cancel(): Promise<void> {

    this.stopContinuousChirp();

    this.running = false;

    this.cleanup();

  }


  private startContinuousChirp(): void {

    if (!this.context) {

      throw new Error(
        "Audio context is not initialized."
      );

    }


    const buffer =
      this.createChirpBuffer(
        this.context
      );


    const source =
      this.context.createBufferSource();


    source.buffer =
      buffer;


    source.loop =
      true;


    source.loopStart =
      0;


    source.loopEnd =
      buffer.duration;


    const gain =
      this.context.createGain();


    gain.gain.value =
      1;


    source.connect(
      gain
    );


    gain.connect(
      this.context.destination
    );


    source.start();


    this.chirpSource =
      source;


    this.chirpGain =
      gain;

  }


  private stopContinuousChirp(): void {

    if (this.chirpSource) {

      try {

        this.chirpSource.stop();

      } catch {
        // Already stopped.
      }


      try {

        this.chirpSource.disconnect();

      } catch {
        // Already disconnected.
      }

    }


    if (this.chirpGain) {

      try {

        this.chirpGain.disconnect();

      } catch {
        // Already disconnected.
      }

    }


    this.chirpSource =
      null;

    this.chirpGain =
      null;

  }


  private createChirpBuffer(
    context: AudioContext
  ): AudioBuffer {

    const sampleRate =
      context.sampleRate;


    const length =
      Math.max(
        1,
        Math.floor(
          this.config.chirpDuration *
          sampleRate
        )
      );


    const buffer =
      context.createBuffer(
        1,
        length,
        sampleRate
      );


    const samples =
      buffer.getChannelData(
        0
      );


    const startFrequency =
      this.config.startFrequency;


    const endFrequency =
      this.config.endFrequency;


    const duration =
      this.config.chirpDuration;


    const amplitude =
      this.config.amplitude;


    let phase = 0;


    for (
      let i = 0;
      i < length;
      i++
    ) {

      const t =
        i / sampleRate;


      const normalizedTime =
        Math.min(
          1,
          t / duration
        );


      const frequency =
        startFrequency *
        Math.pow(
          endFrequency /
            startFrequency,
          normalizedTime
        );


      phase +=
        (
          2 *
          Math.PI *
          frequency
        ) /
        sampleRate;


      const edge =
        Math.min(
          1,

          t / 0.01,

          (duration - t) /
            0.01
        );


      const envelope =
        Math.max(
          0,
          edge
        );


      samples[i] =
        Math.sin(
          phase
        ) *
        amplitude *
        envelope;

    }


    return buffer;

  }


  private stopStreamTracks(): void {

    if (!this.stream) {
      return;
    }


    this.stream
      .getTracks()
      .forEach(
        track =>
          track.stop()
      );


    this.stream =
      null;

  }


  private cleanup(): void {

    this.stopContinuousChirp();


    if (this.source) {

      try {

        this.source.disconnect();

      } catch {
        // Ignore cleanup errors.
      }

    }


    if (this.processor) {

      try {

        this.processor.disconnect();

      } catch {
        // Ignore cleanup errors.
      }

    }


    if (this.silentGain) {

      try {

        this.silentGain.disconnect();

      } catch {
        // Ignore cleanup errors.
      }

    }


    this.stopStreamTracks();


    if (this.context) {

      void this.context
        .close()
        .catch(
          () => undefined
        );

    }


    this.context = null;

    this.source = null;

    this.processor = null;

    this.silentGain = null;

    this.chunks = [];

    this.startedAt = 0;

  }

}