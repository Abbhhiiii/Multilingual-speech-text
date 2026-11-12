import os, sys, time
mode=sys.argv[1]
if mode=='fail': sys.stderr.write('deliberate failure'); sys.exit(7)
if mode=='early': sys.exit(0)
if mode=='hang': time.sleep(60)
if mode=='stderr': sys.stderr.write('diagnostic\n'*20000); sys.stderr.flush()
while data:=os.read(0,16000):
 for byte in ('你好' if mode=='zh' else 'selamat ' if mode=='id' else 'hello ').encode():
  os.write(1,bytes([byte])); time.sleep(.001)
if mode=='slow_final': time.sleep(.15)
print('done',flush=True)
