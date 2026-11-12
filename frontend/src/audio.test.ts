import {afterEach,describe,expect,it,vi} from 'vitest';
import {parseWav,streamPcm} from './audio';
function wav(samples=16000,junk=false){
 const extra=junk?10:0,b=new ArrayBuffer(44+extra+samples*2),v=new DataView(b);
 const tag=(p:number,s:string)=>[...s].forEach((c,i)=>v.setUint8(p+i,c.charCodeAt(0)));
 tag(0,'RIFF');v.setUint32(4,b.byteLength-8,true);tag(8,'WAVE');
 if(junk){tag(12,'JUNK');v.setUint32(16,1,true);}
 const p=12+extra;tag(p,'fmt ');v.setUint32(p+4,16,true);v.setUint16(p+8,1,true);v.setUint16(p+10,1,true);v.setUint32(p+12,16000,true);v.setUint32(p+16,32000,true);v.setUint16(p+20,2,true);v.setUint16(p+22,16,true);tag(p+24,'data');v.setUint32(p+28,samples*2,true);return b;
}
afterEach(()=>{vi.useRealTimers();vi.unstubAllGlobals();});
describe('WAV validation',()=>{
 it('extracts PCM and respects odd-sized metadata padding',()=>{expect(parseWav(wav(80,true)).length).toBe(160);});
 it('rejects truncated data',()=>{expect(()=>parseWav(wav().slice(0,-2))).toThrow();});
 it('rejects stereo and float',()=>{for(const [offset,value] of [[22,2],[20,3]]){const b=wav();new DataView(b).setUint16(offset,value,true);expect(()=>parseWav(b)).toThrow();}});
 it('rejects wrong sample rate',()=>{const b=wav();new DataView(b).setUint32(24,8000,true);expect(()=>parseWav(b)).toThrow();});
 it('rejects empty audio',()=>expect(()=>parseWav(wav(0))).toThrow());
});
describe('pacing',()=>{
 it('sends at 500ms boundaries, then a short tail before end',async()=>{
  vi.useFakeTimers();vi.stubGlobal('WebSocket',{OPEN:1});
  const send=vi.fn(),progress=vi.fn();
  const ws={readyState:1,bufferedAmount:0,send} as unknown as WebSocket;
  const task=streamPcm(new Uint8Array(40000),500,ws,new AbortController().signal,progress);
  await vi.advanceTimersByTimeAsync(499);expect(send).not.toHaveBeenCalled();
  await vi.advanceTimersByTimeAsync(1);expect(send.mock.calls[0][0].length).toBe(16000);
  await vi.advanceTimersByTimeAsync(500);expect(send).toHaveBeenCalledTimes(2);
  await vi.advanceTimersByTimeAsync(250);await task;
  expect(send.mock.calls[2][0].length).toBe(8000);expect(send.mock.calls[3][0]).toBe('{"type":"end"}');
 });
 it('cancellation stops pending audio',async()=>{
  vi.useFakeTimers();vi.stubGlobal('WebSocket',{OPEN:1});
  const controller=new AbortController(),send=vi.fn();
  const task=streamPcm(new Uint8Array(16000),500,{readyState:1,bufferedAmount:0,send} as unknown as WebSocket,controller.signal,()=>{});
  const assertion=expect(task).rejects.toMatchObject({name:'AbortError'});controller.abort();await assertion;expect(send).not.toHaveBeenCalled();
 });
});
