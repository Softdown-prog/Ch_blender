"""Controlled AB/BA benchmark of existing real recipe; no asset promotion."""
import argparse,json,subprocess,sys,time,math,statistics
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--baseline',required=True,type=Path);p.add_argument('--embree',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);runs=[]
for index,name in enumerate(('baseline','embree','embree','baseline')):
 exe=getattr(a,name);started=time.perf_counter();result=subprocess.run([sys.executable,str(HERE/'real_recipe_test.py'),'--blender',str(exe)],capture_output=True,text=True,errors='replace',timeout=600);elapsed=time.perf_counter()-started;(a.output/f'{index}-{name}.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
 if result.returncode!=0:raise RuntimeError(f'{name} failed: {result.returncode}')
 summary=json.loads(result.stdout[result.stdout.rfind('\n{')+1:]);runs.append({'backend':name,'seconds':elapsed,'output':summary['output'],'checks':summary['checks']});print(name,round(elapsed,3),flush=True)
base=Path(next(r['output'] for r in runs if r['backend']=='baseline'));experimental=Path(next(r['output'] for r in runs if r['backend']=='embree'));bm=json.loads((base/'studio_metadata.json').read_text());em=json.loads((experimental/'studio_metadata.json').read_text());keys=('cameraContract','studioPreset','studioFingerprint','footprint','directionOrder','rotationPolicy','lighting','sourceSummary','renderResolution','finalResolution','orthoScaleCalibrated','directions','samples')
for key in keys:assert bm[key]==em[key],key
images=[]
for file in sorted(base.glob('*.png')):
 with Image.open(file) as before,Image.open(experimental/file.name) as after:
  before.load();after.load();assert before.mode==after.mode and before.size==after.size
  diff=ImageChops.difference(before,after);stats=ImageStat.Stat(diff);images.append({'file':file.name,'bitExact':all(high==0 for low,high in diff.getextrema()),'rmsRGBA':stats.rms,'maxChannelDifference':max(high for low,high in diff.getextrema())})
assert all(max(i['rmsRGBA'])<8 for i in images),'Unexpected image difference'
means={name:statistics.mean(r['seconds'] for r in runs if r['backend']==name) for name in ('baseline','embree')}
report={'status':'ok','runs':runs,'meanSeconds':means,'embreeSpeedup':means['baseline']/means['embree'],'contractsMatch':True,'images':images,'officialReferenceAvailable':False,'visualEquivalenceHumanApproved':False};(a.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'status':'ok','means':means,'speedup':report['embreeSpeedup'],'bitExactImages':sum(i['bitExact'] for i in images),'images':len(images)},indent=2))