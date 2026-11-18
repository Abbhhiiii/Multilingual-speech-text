import {useEffect, useRef} from 'react';
import type {RefObject} from 'react';
import type {WaveformSource} from './audio';

const BAR_COUNT = 48;

/** Draws samples from the file playback or live microphone. */
export function Waveform({playback, active}: {playback: RefObject<WaveformSource|null>; active: boolean}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext('2d');
    if (!context) return;

    const heights = new Float32Array(BAR_COUNT);
    let frame = 0;
    let width = 0;
    let height = 0;

    const resize = () => {
      const bounds = canvas.getBoundingClientRect();
      const scale = Math.min(window.devicePixelRatio || 1, 2);
      width = bounds.width;
      height = bounds.height;
      canvas.width = Math.round(width * scale);
      canvas.height = Math.round(height * scale);
      context.setTransform(scale, 0, 0, scale, 0, 0);
      draw();
    };

    const draw = () => {
      if (!width || !height) return;
      context.clearRect(0, 0, width, height);
      const samples = active ? playback.current?.sampleWaveform() : null;
      const gap = 3;
      const barWidth = Math.max(2, (width - gap * (BAR_COUNT - 1)) / BAR_COUNT);
      for (let i = 0; i < BAR_COUNT; i++) {
        const x = i * (barWidth + gap);
        let level = 0.075;
        if (samples) {
          let peak = 0;
          const start = Math.floor(i * samples.length / BAR_COUNT);
          const end = Math.floor((i + 1) * samples.length / BAR_COUNT);
          for (let j = start; j < end; j++) peak = Math.max(peak, Math.abs(samples[j] - 128) / 128);
          level = Math.min(1, 0.075 + peak * 4.5);
        }
        heights[i] += (level - heights[i]) * (samples ? 0.42 : 0.18);
        const barHeight = Math.max(5, heights[i] * (height - 8));
        context.fillStyle = samples ? '#8ce4bd' : '#477b76';
        context.fillRect(x, (height - barHeight) / 2, barWidth, barHeight);
      }
    };

    const animate = () => {
      draw();
      frame = requestAnimationFrame(animate);
    };

    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(resize);
    observer?.observe(canvas);
    window.addEventListener('resize', resize);
    resize();
    if (active) frame = requestAnimationFrame(animate);
    return () => { cancelAnimationFrame(frame); observer?.disconnect(); window.removeEventListener('resize', resize); };
  }, [active, playback]);

  return <canvas ref={canvasRef} className="waveform-canvas" role="img" aria-label="Audio waveform reacting to sound"/>;
}
