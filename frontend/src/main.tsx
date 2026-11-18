import React, {useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {createMicrophoneCapture, createPlayback, parseWav, streamPcm} from './audio';
import type {WaveformSource} from './audio';
import {Waveform} from './Waveform';
import './style.css';
type Metrics = {first_text_ms: number|null; final_latency_ms: number|null; elapsed_ms: number};
const CHUNK_MS = 500;
type Microphone = Awaited<ReturnType<typeof createMicrophoneCapture>>;
function App() {
  const [mode,setMode] = useState<'file'|'microphone'>('file');
  const [pcm,setPcm] = useState<Uint8Array>();
  const [filename,setFilename] = useState('No file selected');
  const [status,setStatus] = useState('Ready');
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [text,setText] = useState('');
  const [progress,setProgress] = useState(0);
  const [micSeconds,setMicSeconds] = useState(0);
  const [finishing,setFinishing] = useState(false);
  const [metrics,setMetrics] = useState<Metrics>();
  const socket = useRef<WebSocket|null>(null);
  const abort = useRef<AbortController|null>(null);
  const playback = useRef<ReturnType<typeof createPlayback>|null>(null);
  const microphone = useRef<Microphone|null>(null);
  const visualizer = useRef<WaveformSource|null>(null);
  const micTimer = useRef<ReturnType<typeof setTimeout>|null>(null);
  const fileVersion = useRef(0);
  const [reading,setReading] = useState(false);
  const [dragging,setDragging] = useState(false);
  useEffect(()=>()=>{abort.current?.abort(); playback.current?.stop(); microphone.current?.stop(); socket.current?.close(); if(micTimer.current)clearTimeout(micTimer.current);},[]);
  function switchMode(next: 'file'|'microphone') {
    if (busy || mode === next) return;
    setMode(next); setError(''); setText(''); setMetrics(undefined); setProgress(0); setMicSeconds(0); setStatus('Ready');
  }
  async function select(file?: File) {
    const version=++fileVersion.current;
    setPcm(undefined); setError(''); setFilename(file?.name??'No file selected'); setReading(true);
    setText(''); setMetrics(undefined); setProgress(0); setStatus('Ready');
    try {
      if (file) {
        if(file.size>10_000_000) throw new Error('Choose a WAV file smaller than 10 MB.');
        const audio=parseWav(await file.arrayBuffer());
        if(version===fileVersion.current) setPcm(audio);
      }
    } catch(e) {if(version===fileVersion.current) setError((e as Error).message);}
    finally {if(version===fileVersion.current) setReading(false);}
  }
  async function start() {
    if((mode==='file' && !pcm) || busy) return;
    setBusy(true); setFinishing(false); setError(''); setText(''); setProgress(0); setMicSeconds(0); setMetrics(undefined);
    setStatus(mode==='microphone'?'Waiting for microphone':'Connecting');
    const controller=new AbortController(); abort.current=controller;
    let ws: WebSocket|null=null;
    let finished=false, sending=false, micEnding=false;
    const clearMicTimer=()=>{if(micTimer.current){clearTimeout(micTimer.current);micTimer.current=null;}};
    const fail=(message:string)=>{if(finished)return; finished=true; controller.abort(); clearMicTimer(); playback.current?.stop(); microphone.current?.stop(); visualizer.current=null; setError(message); setStatus('Stopped'); setBusy(false); setFinishing(false); ws?.close();};
    const sendMicChunk=(chunk:Uint8Array)=>{
      if(finished || controller.signal.aborted)return;
      if(!ws || ws.readyState!==WebSocket.OPEN) {fail('Streaming connection closed.');return;}
      if(ws.bufferedAmount>64000) {fail('Network cannot keep up with microphone audio.');return;}
      try {ws.send(chunk);setMicSeconds(seconds=>seconds+chunk.length/32000);}
      catch {fail('Could not send microphone audio.');}
    };
    try {
      if(mode==='file') {const audio=createPlayback(pcm!);playback.current=audio;visualizer.current=audio;}
      else {const capture=await createMicrophoneCapture(sendMicChunk);if(controller.signal.aborted){capture.stop();return;}microphone.current=capture;visualizer.current=capture;}
    } catch(error) {if(!controller.signal.aborted)fail((error as Error).message||'Could not start audio.');return;}
    if(controller.signal.aborted)return;
    setStatus('Connecting');
    ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws/transcribe`);
    socket.current=ws;
    const connectTimeout=setTimeout(()=>fail('Backend did not become ready. Check that it is running.'),15000);
    ws.onopen=()=>ws?.send(JSON.stringify({type:'start',sample_rate:16000,channels:1,encoding:'pcm_s16le',chunk_ms:CHUNK_MS,language:'auto'}));
    ws.onmessage=(event)=>{
      try {
        const data=JSON.parse(event.data);
        if(data.type==='ready' && !sending) {
          clearTimeout(connectTimeout); sending=true;
          if(mode==='microphone') {
            microphone.current?.start(); setStatus('Recording from microphone');
            micTimer.current=setTimeout(()=>finishMicrophone(),300000);
          } else {
            setStatus('Playing audio and streaming');
            void playback.current!.start().then(() => streamPcm(pcm!,CHUNK_MS,ws!,controller.signal,setProgress))
              .then(()=>{if(!finished)setStatus('Finishing transcription');})
              .catch(e=>{if(e.name!=='AbortError')fail(e.message);});
          }
        } else if(data.type==='transcript') {setText(data.text); setMetrics(data.metrics);}
        else if(data.type==='done') {finished=true; controller.abort(); clearMicTimer(); playback.current?.stop(); microphone.current?.stop(); visualizer.current=null; setText(data.text);setMetrics(data.metrics);setStatus('Complete');setBusy(false);setFinishing(false);ws?.close();}
        else if(data.type==='error') { if(data.code==='cancelled') { finished=true; controller.abort(); clearMicTimer(); playback.current?.stop(); microphone.current?.stop(); visualizer.current=null; setStatus('Stopped'); setBusy(false); ws?.close(); } else fail(data.message); }
      } catch {fail('Invalid response from backend.');}
    };
    ws.onerror=()=>{if(!controller.signal.aborted)fail('Could not connect to the backend.');};
    ws.onclose=()=>{const cancelled=controller.signal.aborted;clearTimeout(connectTimeout);if(!finished && !cancelled)fail('Streaming connection disconnected.');};
    function finishMicrophone() {
      if(finished || micEnding || controller.signal.aborted || !sending || !ws || ws.readyState!==WebSocket.OPEN)return;
      micEnding=true;
      clearMicTimer();
      const tail=microphone.current?.stop();
      if(tail?.length)sendMicChunk(tail);
      if(finished)return;
      ws.send(JSON.stringify({type:'end'}));setFinishing(true);setStatus('Finishing transcription');
    }
    finishMic.current=finishMicrophone;
  }
  const finishMic=useRef<()=>void>(()=>{});
  function stop() {
    if(mode==='microphone' && microphone.current && socket.current?.readyState===WebSocket.OPEN && !finishing) {finishMic.current();return;}
    abort.current?.abort(); playback.current?.stop(); microphone.current?.stop(); visualizer.current=null;
    if(micTimer.current){clearTimeout(micTimer.current);micTimer.current=null;}
    if(socket.current?.readyState===WebSocket.OPEN) socket.current.send(JSON.stringify({type:'cancel'}));
    socket.current?.close();
    setStatus('Stopped');setBusy(false);setFinishing(false);
  }
  const duration=pcm?pcm.length/32000:0;
  const ms=(value?:number|null)=>value==null?'—':`${(value/1000).toFixed(2)} s`;
  const clock=(seconds:number)=>`${Math.floor(seconds/60).toString().padStart(2,'0')}:${Math.floor(seconds%60).toString().padStart(2,'0')}`;
  return <main className="app-shell">
    <header className="page-header"><h1>Speech, as it arrives.</h1></header>
    <div className="workspace">
      <section className="panel input-panel" aria-label="Audio input">
        <div className="panel-heading"><h2>Audio</h2></div>
        <div className="source-switch" role="group" aria-label="Audio source">
          <button type="button" className={mode==='file'?'selected':''} aria-pressed={mode==='file'} disabled={busy} onClick={()=>switchMode('file')}>WAV file</button>
          <button type="button" className={mode==='microphone'?'selected':''} aria-pressed={mode==='microphone'} disabled={busy} onClick={()=>switchMode('microphone')}>Microphone</button>
        </div>
        {mode==='file'?<label className={`dropzone${dragging?' dragging':''}${busy?' disabled':''}`}
          onDragOver={e=>{e.preventDefault(); if(!busy)setDragging(true);}}
          onDragLeave={e=>{e.preventDefault(); setDragging(false);}}
          onDrop={e=>{e.preventDefault(); setDragging(false); if(!busy)void select(e.dataTransfer.files[0]);}}>
          <input type="file" accept=".wav,audio/wav" disabled={busy} onChange={e=>{void select(e.target.files?.[0]); e.currentTarget.value='';}}/>
          <span className="upload-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5"/><path d="M4 15.5v2.8A1.7 1.7 0 0 0 5.7 20h12.6a1.7 1.7 0 0 0 1.7-1.7v-2.8"/></svg></span>
          <strong>{pcm?filename:'Drop your WAV file here'}</strong>
          <span className="drop-hint">{pcm?`${duration.toFixed(1)} seconds · Ready to stream`:'or click to browse files'}</span>
        </label>:<div className="dropzone mic-card">
          <span className="upload-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="3" width="6" height="12" rx="3"/><path d="M6 11a6 6 0 0 0 12 0M12 17v4m-4 0h8"/></svg></span>
          <strong>Speak into your microphone</strong>
          <span className="drop-hint">Finish recording to complete the transcript.</span>
        </div>}
        <div className="audio-visual">
          <Waveform playback={visualizer} active={busy&&!finishing}/>
          <div className="visual-timeline"><span>{clock(mode==='file'?progress*duration:micSeconds)}</span><span>{mode==='file'?clock(duration):status==='Complete'?'Done':status==='Recording from microphone'?'LIVE':'MIC'}</span></div>
        </div>

        <div className="actions"><button disabled={(mode==='file'&&!pcm)||busy||reading} onClick={()=>void start()}>{mode==='file'?'Start streaming':'Start microphone'} <span aria-hidden="true">→</span></button><button className="secondary" disabled={!busy||finishing} onClick={stop}>{mode==='microphone'&&status==='Recording from microphone'?'Finish recording':'Stop'}</button></div>
        {error&&<p role="alert" className="error">{error}</p>}
      </section>

      <section className="panel transcript-panel" aria-label="Transcript">
        <div className="panel-heading"><h2>Transcription</h2></div>
        <div className="transcript-body" aria-live="polite">{text||<span className="placeholder">Your transcript will appear here as the audio plays.</span>}</div>
      </section>
    </div>
    <section className="metrics" aria-label="Latency metrics"><div><span>First text</span><strong>{ms(metrics?.first_text_ms)}</strong><small>From first audio received</small></div><div><span>Final latency</span><strong>{status==='Complete'?ms(metrics?.final_latency_ms):'—'}</strong><small>After end of audio received</small></div><div><span>{mode==='file'?'Audio sent':'Recorded'}</span><strong>{mode==='file'?`${Math.round(progress*100)}%`:`${micSeconds.toFixed(1)} s`}</strong><small>{mode==='file'?'Real-time paced transmission':'Live microphone audio sent'}</small></div></section>
  </main>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
