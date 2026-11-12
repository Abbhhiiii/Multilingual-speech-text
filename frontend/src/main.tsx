import React, {useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {createPlayback, parseWav, streamPcm} from './audio';
import './style.css';
type Metrics = {first_text_ms: number|null; final_latency_ms: number|null; elapsed_ms: number};
function App() {
  const [pcm,setPcm] = useState<Uint8Array>();
  const [filename,setFilename] = useState('No file selected');
  const [language,setLanguage] = useState('auto');
  const [chunk,setChunk] = useState(500);
  const [status,setStatus] = useState('Ready');
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [text,setText] = useState('');
  const [progress,setProgress] = useState(0);
  const [metrics,setMetrics] = useState<Metrics>();
  const socket = useRef<WebSocket|null>(null);
  const abort = useRef<AbortController|null>(null);
  const playback = useRef<ReturnType<typeof createPlayback>|null>(null);
  const fileVersion = useRef(0);
  const [reading,setReading] = useState(false);
  useEffect(()=>()=>{abort.current?.abort(); playback.current?.stop(); socket.current?.close();},[]);
  async function select(file?: File) {
    const version=++fileVersion.current;
    setPcm(undefined); setError(''); setFilename(file?.name??'No file selected'); setReading(true);
    try {
      if (file) {
        if(file.size>10_000_000) throw new Error('Choose a WAV file smaller than 10 MB.');
        const audio=parseWav(await file.arrayBuffer());
        if(version===fileVersion.current) setPcm(audio);
      }
    } catch(e) {if(version===fileVersion.current) setError((e as Error).message);}
    finally {if(version===fileVersion.current) setReading(false);}
  }
  function start() {
    if(!pcm || busy) return;
    let audio: ReturnType<typeof createPlayback>;
    try { audio = createPlayback(pcm); playback.current = audio; }
    catch { setError('Audio playback could not start in this browser. Check your audio settings.'); return; }
    setBusy(true); setError(''); setText(''); setProgress(0); setMetrics(undefined); setStatus('Connecting');
    const controller=new AbortController(); abort.current=controller;
    const ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws/transcribe`);
    socket.current=ws;
    let finished=false, sending=false;
    const fail=(message:string)=>{finished=true; controller.abort(); audio.stop(); setError(message); setStatus('Stopped'); setBusy(false); ws.close();};
    const connectTimeout=setTimeout(()=>fail('Backend did not become ready. Check that it is running.'),15000);
    ws.onopen=()=>ws.send(JSON.stringify({type:'start',sample_rate:16000,channels:1,encoding:'pcm_s16le',chunk_ms:chunk,language}));
    ws.onmessage=(event)=>{
      try {
        const data=JSON.parse(event.data);
        if(data.type==='ready' && !sending) {
          clearTimeout(connectTimeout); sending=true; setStatus('Playing audio and streaming');
          void audio.start().then(() => streamPcm(pcm,chunk,ws,controller.signal,setProgress))
            .then(()=>{if(!finished)setStatus('Finishing transcription');})
            .catch(e=>{if(e.name!=='AbortError')fail(e.message);});
        } else if(data.type==='transcript') {setText(data.text); setMetrics(data.metrics);}
        else if(data.type==='done') {finished=true; controller.abort(); audio.stop(); setText(data.text);setMetrics(data.metrics);setStatus('Complete');setBusy(false);ws.close();}
        else if(data.type==='error') { if(data.code==='cancelled') { finished=true; controller.abort(); audio.stop(); setStatus('Stopped'); setBusy(false); ws.close(); } else fail(data.message); }
      } catch {fail('Invalid response from backend.');}
    };
    ws.onerror=()=>{if(!controller.signal.aborted)fail('Could not connect to the backend.');};
    ws.onclose=()=>{const cancelled=controller.signal.aborted;clearTimeout(connectTimeout);controller.abort();audio.stop();if(!finished && !cancelled)fail('Streaming connection disconnected.');};
  }
  function stop() {
    abort.current?.abort(); playback.current?.stop();
    if(socket.current?.readyState!==WebSocket.OPEN) {socket.current?.close(); setStatus('Stopped'); setBusy(false); return;}
    if(socket.current?.readyState===WebSocket.OPEN) socket.current.send(JSON.stringify({type:'cancel'}));
    else socket.current?.close();
    setStatus('Stopping');
  }
  const duration=pcm?pcm.length/32000:0;
  const ms=(value?:number|null)=>value==null?'—':`${(value/1000).toFixed(2)} s`;
  return <main>
    <header><span className="eyebrow">TETHERFI / ENGINEERING PROTOTYPE</span><h1>Speech, as it arrives.</h1><p>Multilingual transcription · Qwen3-ASR 0.6B · Local CPU</p></header>
    <section className="controls" aria-label="Audio input">
      <label className="file">Choose WAV recording<input type="file" accept=".wav,audio/wav" disabled={busy} onChange={e=>void select(e.target.files?.[0])}/></label>
      <div className="fileinfo"><strong>{filename}</strong><span>{duration?`${duration.toFixed(1)} seconds · `:''}16 kHz · Mono · PCM16 · Up to 5 minutes</span></div>
      <div className="options"><label>Language<select value={language} disabled={busy} onChange={e=>setLanguage(e.target.value)}><option value="auto">Auto detect</option><option value="en">English</option><option value="zh">Mandarin Chinese</option><option value="id">Bahasa Indonesia</option></select></label>
      <label>Audio chunks<select value={chunk} disabled={busy} onChange={e=>setChunk(Number(e.target.value))}><option value={250}>250 ms · experiment</option><option value={500}>500 ms · baseline</option><option value={1000}>1,000 ms · experiment</option></select></label></div>
      <div className="actions"><button disabled={!pcm||busy||reading} onClick={start}>Start streaming</button><button className="secondary" disabled={!busy} onClick={stop}>Stop</button></div>
      {error&&<p role="alert" className="error">{error}</p>}
    </section>
    <section className="transcript"><div className="sectionhead"><h2>Live transcription</h2><span className="status">{status}</span></div><progress value={progress} max={1} aria-label="Audio sent"/><div className="text" aria-live="polite">{text||<span className="placeholder">Recognized speech will appear here as one continuous transcript.</span>}</div></section>
    <section className="metrics"><div><span>First text</span><strong>{ms(metrics?.first_text_ms)}</strong><small>From first audio received</small></div><div><span>Final latency</span><strong>{status==='Complete'?ms(metrics?.final_latency_ms):'—'}</strong><small>After end of audio received</small></div><div><span>Audio sent</span><strong>{Math.round(progress*100)}%</strong><small>Real-time paced transmission</small></div></section>
    <footer>The selected recording plays aloud while it streams. Keep this tab active during streaming. The engine commits text at its own cadence; a 500 ms audio chunk does not imply a 500 ms text update.</footer>
  </main>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
