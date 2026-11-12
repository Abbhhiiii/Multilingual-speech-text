import sys,time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.runtime import Settings
FAKE=str(Path(__file__).with_name('fake_runtime.py'))
START=dict(type='start',sample_rate=16000,channels=1,encoding='pcm_s16le',chunk_ms=500,language='en')
def client(mode=None,**settings):
 return TestClient(create_app(Settings(**settings),lambda lang:[sys.executable,FAKE,mode or lang]))
def begin(ws,**overrides):
 ws.send_json(START|overrides); assert ws.receive_json()['type']=='ready'
def terminal(ws):
 while True:
  e=ws.receive_json()
  if e['type'] in ('done','error'): return e
@pytest.mark.parametrize('lang,expected',[('en','hello '),('zh','你好'),('id','selamat ')])
def test_incremental_utf8(lang,expected):
 with client() as c,c.websocket_connect('/ws/transcribe') as ws:
  begin(ws,language=lang); ws.send_bytes(b'\0'*16000)
  assert ws.receive_json()['type']=='transcript' # Before sending EOF.
  ws.send_json({'type':'end'}); final=terminal(ws)
  assert final['type']=='done'; assert final['text']==expected+'done'
  assert final['metrics']['first_text_ms']>=0
  assert final['metrics']['audio_received_seconds']==.5
@pytest.mark.parametrize('data',[b'',b'a',b'\0'*16002])
def test_bad_audio(data):
 with client() as c,c.websocket_connect('/ws/transcribe') as ws:
  begin(ws); ws.send_bytes(data); assert terminal(ws)['code']=='audio'
def test_metadata():
 with client() as c,c.websocket_connect('/ws/transcribe') as ws:
  ws.send_json(START|{'sample_rate':8000}); assert terminal(ws)['code']=='metadata'
@pytest.mark.parametrize('mode',['fail','early'])
def test_runtime_failure(mode):
 with client(mode) as c,c.websocket_connect('/ws/transcribe') as ws:
  begin(ws); assert terminal(ws)['code']=='runtime'
def test_stderr_drained():
 with client('stderr') as c,c.websocket_connect('/ws/transcribe') as ws:
  begin(ws); ws.send_bytes(b'\0'*16000); ws.send_json({'type':'end'}); assert terminal(ws)['type']=='done'
def test_finish_timeout():
 with client('hang',finish_timeout=.1) as c,c.websocket_connect('/ws/transcribe') as ws:
  begin(ws); ws.send_bytes(b'\0'*16000); ws.send_json({'type':'end'}); assert terminal(ws)['code']=='timeout'
def test_capacity_and_cancel():
 with client() as c:
  with c.websocket_connect('/ws/transcribe') as ws:
   begin(ws)
   with c.websocket_connect('/ws/transcribe') as other: assert terminal(other)['code']=='capacity'
   ws.send_json({'type':'cancel'}); assert terminal(ws)['code']=='cancelled'
  for _ in range(100):
   if not c.app.state.active: break
   time.sleep(.01)
  assert not c.app.state.active

def test_isolation():
 with client(max_sessions=2) as c:
  with c.websocket_connect('/ws/transcribe') as a,c.websocket_connect('/ws/transcribe') as b:
   begin(a,language='zh'); begin(b,language='id')
   for ws in (a,b): ws.send_bytes(b'\0'*16000); ws.send_json({'type':'end'})
   fa,fb=terminal(a),terminal(b)
   assert fa['text']=='你好done'; assert fb['text']=='selamat done'
   assert fa['session_id']!=fb['session_id']
def test_disconnect():
 with client('hang') as c:
  with c.websocket_connect('/ws/transcribe') as ws: begin(ws)
  for _ in range(100):
   if not c.app.state.active: break
   time.sleep(.01)
  assert not c.app.state.active
@pytest.mark.parametrize('control,code',[({'type':'end'},'audio'),({'type':'what'},'protocol')])
def test_control(control,code):
 with client() as c,c.websocket_connect('/ws/transcribe') as ws:
  begin(ws); ws.send_json(control); assert terminal(ws)['code']==code
def test_missing_binary():
 with TestClient(create_app(Settings(binary='/not/a/binary'))) as c,c.websocket_connect('/ws/transcribe') as ws:
  ws.send_json(START); assert terminal(ws)['code']=='runtime'

def test_finalization_is_not_an_idle_input_timeout():
 with client('slow_final',idle_timeout=.1,finish_timeout=2) as c,c.websocket_connect('/ws/transcribe') as ws:
  begin(ws);ws.send_bytes(b'\0'*16000);ws.send_json({'type':'end'})
  assert terminal(ws)['type']=='done'

def test_unpaced_upload_rejected():
 with client('hang') as c,c.websocket_connect('/ws/transcribe') as ws:
  begin(ws)
  for _ in range(5):ws.send_bytes(b'\0'*16000)
  assert terminal(ws)['code']=='pacing'

def test_audio_after_short_tail_rejected():
 with client('hang') as c,c.websocket_connect('/ws/transcribe') as ws:
  begin(ws);ws.send_bytes(b'\0'*100);ws.send_bytes(b'\0'*100)
  assert terminal(ws)['code']=='protocol'


def test_hypothesis_replaces_previous_text():
 with TestClient(create_app(Settings(),lambda lang:[sys.executable,FAKE,'hypothesis','--hypotheses'])) as c,c.websocket_connect('/ws/transcribe') as ws:
  begin(ws)
  ws.send_bytes(b'\0'*16000)
  first=ws.receive_json()
  assert first['type']=='transcript' and first['text']=='This is.'
  ws.send_bytes(b'\0'*16000)
  revised=ws.receive_json()
  assert revised['type']=='transcript' and revised['text']=='This is better.'
  assert revised['sequence']>first['sequence']
  ws.send_json({'type':'end'})
  assert terminal(ws)['text']=='This is better.'
