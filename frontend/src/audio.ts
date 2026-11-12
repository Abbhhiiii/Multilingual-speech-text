export function parseWav(buffer: ArrayBuffer): Uint8Array {
  const v = new DataView(buffer);
  const tag = (offset: number) => String.fromCharCode(...new Uint8Array(buffer, offset, 4));
  if (v.byteLength < 12 || tag(0) !== 'RIFF' || tag(8) !== 'WAVE') throw new Error('Select a RIFF WAV file.');
  const limit = v.getUint32(4, true) + 8;
  if (limit !== v.byteLength) throw new Error('WAV size does not match its header.');
  let validFormat = false;
  let pcm: Uint8Array | undefined;
  for (let p = 12; p < limit;) {
    if (p + 8 > limit) throw new Error('Truncated WAV chunk header.');
    const name = tag(p), size = v.getUint32(p + 4, true), start = p + 8;
    if (start + size + (size % 2) > limit) throw new Error('Truncated WAV data.');
    if (name === 'fmt ') {
      if (validFormat || size < 16 || v.getUint16(start, true) !== 1 || v.getUint16(start+2, true) !== 1 ||
          v.getUint32(start+4, true) !== 16000 || v.getUint32(start+8, true) !== 32000 ||
          v.getUint16(start+12, true) !== 2 || v.getUint16(start+14, true) !== 16)
        throw new Error('Use 16 kHz, mono, uncompressed PCM16 WAV audio.');
      validFormat = true;
    } else if (name === 'data') {
      if (pcm) throw new Error('Multiple WAV data sections are not supported.');
      pcm = new Uint8Array(buffer, start, size);
    }
    p = start + size + size % 2;
  }
  if (!validFormat || !pcm?.length || pcm.length % 2) throw new Error('WAV is missing valid format or audio data.');
  if (pcm.length > 300 * 32000) throw new Error('Choose a recording of five minutes or less.');
  return pcm;
}

export async function streamPcm(pcm: Uint8Array, chunkMs: number, ws: WebSocket, signal: AbortSignal,
                                progress: (fraction: number) => void) {
  const start = performance.now();
  for (let offset = 0; offset < pcm.length; offset += chunkMs * 32) {
    const end = Math.min(offset + chunkMs * 32, pcm.length);
    // Send after the chunk's audio interval has elapsed, including a short final chunk.
    const due = start + end / 32;
    await new Promise<void>((resolve, reject) => {
      if (signal.aborted) { reject(new DOMException('Cancelled', 'AbortError')); return; }
      const cancel = () => { clearTimeout(timer); reject(new DOMException('Cancelled', 'AbortError')); };
      const timer = setTimeout(() => {signal.removeEventListener('abort', cancel); resolve();}, Math.max(0, due-performance.now()));
      signal.addEventListener('abort', cancel, {once:true});
    });
    if (signal.aborted) throw new DOMException('Cancelled', 'AbortError');
    if (performance.now() - due > 1500) throw new Error('Audio scheduling paused. Keep this tab active and restart.');
    if (ws.readyState !== WebSocket.OPEN) throw new Error('Streaming connection closed.');
    if (ws.bufferedAmount > 64000) throw new Error('Network cannot keep up with audio. Restart the stream.');
    ws.send(pcm.subarray(offset, end));
    progress(end / pcm.length);
  }
  ws.send(JSON.stringify({type:'end'}));
}

/** One playback clock and one PCM source for the same samples sent to the backend. */
export function createPlayback(pcm: Uint8Array) {
  const context = new AudioContext();
  // Resume while handling the user's Start click, so browser audio permission is available
  // even though the WebSocket ready event arrives later.
  const resumed = context.resume().catch(() => {});
  const frameCount = pcm.byteLength / 2;
  const buffer = context.createBuffer(1, frameCount, 16000);
  const channel = buffer.getChannelData(0);
  const samples = new DataView(pcm.buffer, pcm.byteOffset, pcm.byteLength);
  for (let i = 0; i < frameCount; i++) channel[i] = samples.getInt16(i * 2, true) / 32768;
  const source = context.createBufferSource();
  source.buffer = buffer;
  source.connect(context.destination);
  let started = false;
  let closed = false;
  return {
    async start() {
      await resumed;
      if (closed) throw new DOMException('Cancelled', 'AbortError');
      if (context.state !== 'running') throw new Error('Audio playback is blocked. Allow sound in this browser and restart.');
      source.start();
      started = true;
      // The audio clock and streaming timer start together, after the backend is ready.
    },
    stop() {
      if (closed) return;
      closed = true;
      if (started) { try { source.stop(); } catch { /* Playback already ended. */ } }
      void context.close().catch(() => {});
    }
  };
}
