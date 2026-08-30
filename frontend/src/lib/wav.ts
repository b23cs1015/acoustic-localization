export function audioBufferToWav(
  audioBuffer: AudioBuffer
): Blob {
  const numberOfChannels = audioBuffer.numberOfChannels;
  const sampleRate = audioBuffer.sampleRate;
  const format = 1;
  const bitDepth = 16;

  const channelData: Float32Array[] = [];

  for (let channel = 0; channel < numberOfChannels; channel++) {
    channelData.push(
      audioBuffer.getChannelData(channel)
    );
  }

  const interleaved = interleave(
    channelData,
    audioBuffer.length
  );

  const bytesPerSample = bitDepth / 8;
  const dataLength =
    interleaved.length * bytesPerSample;

  const buffer = new ArrayBuffer(
    44 + dataLength
  );

  const view = new DataView(buffer);

  writeString(view, 0, "RIFF");
  view.setUint32(
    4,
    36 + dataLength,
    true
  );

  writeString(view, 8, "WAVE");
  writeString(view, 12, "fmt ");

  view.setUint32(16, 16, true);
  view.setUint16(20, format, true);
  view.setUint16(
    22,
    numberOfChannels,
    true
  );

  view.setUint32(
    24,
    sampleRate,
    true
  );

  view.setUint32(
    28,
    sampleRate *
      numberOfChannels *
      bytesPerSample,
    true
  );

  view.setUint16(
    32,
    numberOfChannels * bytesPerSample,
    true
  );

  view.setUint16(
    34,
    bitDepth,
    true
  );

  writeString(view, 36, "data");

  view.setUint32(
    40,
    dataLength,
    true
  );

  floatTo16BitPCM(
    view,
    44,
    interleaved
  );

  return new Blob(
    [view],
    { type: "audio/wav" }
  );
}

function interleave(
  channels: Float32Array[],
  length: number
): Float32Array {
  const numberOfChannels = channels.length;

  const result = new Float32Array(
    length * numberOfChannels
  );

  let index = 0;

  for (let sample = 0; sample < length; sample++) {
    for (
      let channel = 0;
      channel < numberOfChannels;
      channel++
    ) {
      result[index++] =
        channels[channel][sample];
    }
  }

  return result;
}

function floatTo16BitPCM(
  view: DataView,
  offset: number,
  input: Float32Array
): void {
  for (let i = 0; i < input.length; i++) {
    const sample = Math.max(
      -1,
      Math.min(1, input[i])
    );

    const value =
      sample < 0
        ? sample * 0x8000
        : sample * 0x7fff;

    view.setInt16(
      offset + i * 2,
      value,
      true
    );
  }
}

function writeString(
  view: DataView,
  offset: number,
  value: string
): void {
  for (let i = 0; i < value.length; i++) {
    view.setUint8(
      offset + i,
      value.charCodeAt(i)
    );
  }
}