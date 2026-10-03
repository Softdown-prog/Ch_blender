"""Exact version, bpy, blend round-trip, headless Cycles CPU and RGBA gates."""
import argparse,json,subprocess,sys
from pathlib import Path
from PIL import Image
HERE=Path(__file__).resolve().parent

def run(command,out,name):
    p=subprocess.run([str(x) for x in command],capture_output=True,text=True,errors='replace',timeout=600)
    (out/(name+'.log')).write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
    if p.returncode != 0: raise RuntimeError(f'{name}: exit {p.returncode}; see {out/(name+".log")}')
    return p.stdout

def main():
    a=argparse.ArgumentParser(); a.add_argument('--blender',required=True); a.add_argument('--output',required=True); o=a.parse_args()
    exe=Path(o.blender).resolve(); out=Path(o.output).resolve(); out.mkdir(parents=True,exist_ok=True)
    try:
        version=run([exe,'--version'],out,'version').splitlines()[0].strip()
        assert version=='Blender 4.2.3', version
        bpy=run([exe,'--background','--factory-startup','--python-exit-code','1','--python-expr','import bpy; print(bpy.app.version_string); assert bpy.app.version == (4,2,3)'],out,'bpy')
        assert '4.2.3' in bpy.splitlines(), bpy
        run([exe,'--background','--factory-startup','--python-exit-code','1','--python',HERE/'cycles_probe.py','--',out],out,'cycles')
        with Image.open(out/'cycles.png') as image:
            image.load(); assert image.format=='PNG' and image.mode=='RGBA' and image.size==(64,64)
            lo,hi=image.getchannel('A').getextrema(); assert lo==0 and hi>0
        report={'status':'ok','executable':str(exe),'versionLine':version,'bpy':True,'cycles':json.loads((out/'cycles-report.json').read_text()),'isaAuditComplete':False}
    except Exception as exc:
        report={'status':'failed','executable':str(exe),'error':str(exc)}
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2))
    return 0 if report['status']=='ok' else 1
if __name__=='__main__': raise SystemExit(main())
