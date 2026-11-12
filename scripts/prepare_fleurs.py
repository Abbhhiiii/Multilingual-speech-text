"""Extract a deterministic 20-clip/language FLEURS test set from Google archives."""
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import wave

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'benchmark_audio'
CONFIGS = {'en': 'en_us', 'zh': 'cmn_hans_cn', 'id': 'id_id'}
REVISION = '70bb2e84b976b7e960aa89f1c648e09c59f894dd'

def download_text(url):
    return subprocess.check_output(['curl','-fsSL','--retry','3',url]).decode('utf-8')

def prepare(lang):
    config=CONFIGS[lang]
    base=f'https://huggingface.co/datasets/google/fleurs/resolve/{REVISION}/data/{config}'
    tsv=download_text(base+'/test.tsv')
    rows={row[1]:row for row in csv.reader(io.StringIO(tsv),delimiter='\t') if len(row)>=6}
    archive_url=base+'/audio/test.tar.gz'
    output=OUT/lang;output.mkdir(parents=True,exist_ok=True)
    selected=[];counts={'MALE':0,'FEMALE':0}
    genders={row[-1].upper() for row in rows.values()}
    quota={'MALE':10,'FEMALE':10} if {'MALE','FEMALE'}<=genders else {next(iter(genders)):20}
    proc=subprocess.Popen(['curl','-fsSL','--retry','3',archive_url],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    try:
        with tarfile.open(fileobj=proc.stdout,mode='r|gz') as archive:
            for member in archive:
                name=Path(member.name).name
                row=rows.get(name)
                if not member.isfile() or row is None:continue
                frames=int(row[-2]);gender=row[-1].upper()
                if gender not in quota or counts[gender]>=quota[gender] or not 4*16000<=frames<=16*16000:continue
                raw=output/(name+'.original.wav')
                raw.write_bytes(archive.extractfile(member).read())
                target=output/name
                subprocess.run(['afconvert','-f','WAVE','-d','LEI16@16000','-c','1',str(raw),str(target)],check=True,stdout=subprocess.DEVNULL)
                raw.unlink()
                with wave.open(str(target)) as w:
                    assert (w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getcomptype())==(16000,1,2,'NONE')
                    assert abs(w.getnframes()-frames)<16000
                selected.append({'id':f'{lang}-{Path(name).stem}','wav':str(target.relative_to(ROOT)),
                    'language':lang,'reference':row[2],'gender':gender,
                    'source_audio_name':name,'source_config':config,'source_split':'test',
                    'source_audio_frames':frames,'sha256_pcm16_wav':hashlib.sha256(target.read_bytes()).hexdigest()})
                counts[gender]+=1
                print(lang,len(selected),gender,name,round(frames/16000,2),flush=True)
                if len(selected)==20:break
    finally:
        proc.kill();proc.wait()
    if len(selected)!=20:raise RuntimeError(f'{lang}: only {len(selected)} eligible clips')
    return selected

if __name__=='__main__':
    import sys
    OUT.mkdir(exist_ok=True)
    metadata_path=OUT/'source.json'
    if not metadata_path.exists():
        metadata_path.write_text(json.dumps({'dataset':'google/fleurs','revision':REVISION,
            'license':'cc-by-4.0','selection':'first 10 male and 10 female WAV files if both genders exist; otherwise first 20 available. Duration 4-16 seconds, test split, archive order.',
            'conversion':'afconvert -f WAVE -d LEI16@16000 -c 1'},indent=2)+'\n')
    all_rows=[]
    for lang in sys.argv[1:] or ('en','zh','id'):
        old=OUT/f'manifest-{lang}.json'
        cached=json.loads(old.read_text()) if old.exists() else []
        rows=cached if len(cached)==20 and all((ROOT/row['wav']).exists() for row in cached) else prepare(lang)
        old.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
        all_rows.extend(rows)
    if len(all_rows)==60:
        (OUT/'manifest-60.json').write_text(json.dumps(all_rows,ensure_ascii=False,indent=2)+'\n')
