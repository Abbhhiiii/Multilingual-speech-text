import os, sys, time
mode=sys.argv[1]
if mode=='fail': sys.stderr.write('deliberate failure'); sys.exit(7)
if mode=='early': sys.exit(0)
if mode=='hang': time.sleep(60)
if mode=='stderr': sys.stderr.write('diagnostic\n'*20000); sys.stderr.flush()
if mode=='hypothesis':
 import json
 os.read(0,16000)
 print(json.dumps({'text':'This is.'}),flush=True)
 os.read(0,16000)
 print(json.dumps({'text':'This is better.'}),flush=True)
 while os.read(0,16000): pass
 print(json.dumps({'text':'This is better.'}),flush=True)
 sys.exit(0)
while data:=os.read(0,16000):
 for byte in ('你好' if mode=='zh' else 'selamat ' if mode=='id' else 'hello ').encode():
  os.write(1,bytes([byte])); time.sleep(.001)
if mode=='slow_final': time.sleep(.15)
print('done',flush=True)
