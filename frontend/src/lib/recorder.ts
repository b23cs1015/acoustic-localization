export interface RecordingResult {
  audioBuffer: AudioBuffer;
  stream: MediaStream;
}

export async function recordMicrophone(
  durationMs: number
): Promise<RecordingResult> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false
    }
  });

  const audioContext = new AudioContext({
    sampleRate: 48000
  });

  const source = audioContext.createMediaStreamSource(stream);

  const recorder = new AudioWorkletRecorder(
    audioContext,
    source
  );

  await recorder.start();

  await new Promise<void>((resolve) => {
    window.setTimeout(resolve, durationMs);
  });

  const audioBuffer = await recorder.stop();

  stream.getTracks().forEach((track) => {
    track.stop();
  });

  await audioContext.close();

  return {
    audioBuffer,
    stream
  };
}

class AudioWorkletRecorder {
  private context: AudioContext;
  private source: MediaStreamAudioSourceNode;
  private processor: ScriptProcessorNode;

  private chunks: Float32Array[] = [];

  constructor(
    context: AudioContext,
    source: MediaStreamAudioSourceNode
  ) {
    this.context = context;
    this.source = source;

    this.processor = context.createScriptProcessor(
      4096,
      1,
      1
    );

    this.processor.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0);

      this.chunks.push(new Float32Array(input));
    };
  }

  async start(): Promise<void> {
    this.source.connect(this.processor);

    this.processor.connect(
      this.context.destination
    );

    await this.context.resume();
  }

  async stop(): Promise<AudioBuffer> {
    this.source.disconnect();
    this.processor.disconnect();

    const totalLength = this.chunks.reduce(
      (sum, chunk) => sum + chunk.length,
      0
    );

    const samples = new Float32Array(totalLength);

    let offset = 0;

    for (const chunk of this.chunks) {
      samples.set(chunk, offset);
      offset += chunk.length;
    }

    const buffer = this.context.createBuffer(
      1,
      samples.length,
      this.context.sampleRate
    );

    buffer.copyToChannel(samples, 0);

    return buffer;
  }
}