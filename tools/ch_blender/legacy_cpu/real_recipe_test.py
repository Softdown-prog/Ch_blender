"""Established color-mask smoke recipe, frozen studio, actual CH worker, four views."""
import argparse,json,math,sys,time
from pathlib import Path
from PIL import Image
HERE=Path(__file__).resolve().parent; REPO=HERE.parents[2]
sys.path.insert(0,str(REPO/'tools/ch_blender'))
from agent_worker import run_job,validate_job

def main():
    a=argparse.ArgumentParser(); a.add_argument('--blender',required=True); o=a.parse_args()
    rel='out/ch_blender_agent/legacy_cpu_smoke_'+str(time.time_ns()); out=REPO/rel; out.mkdir(parents=True)
    asset='test_color_mask_v1'
    names=[f'{asset}_{d}_{p}_source.png' for d in ('south','east','west','north') for p in ('color','shadow','mask')]
    job={'contract':'CH_BLENDER_AGENT_JOB_V1','jobId':out.name,'operation':'blender_script','script':'tools/tycoon_photo_studio/build_scene.py','args':['--asset-config','tools/tycoon_photo_studio/assets/tests/color_mask_smoke.asset.json','--studio-preset','tools/tycoon_photo_studio/studio_presets/ch_tycoon_studio_v1.json','--source-resolution','64x64','--final-resolution','64x64','--output',rel],'outputDir':rel,'expectedOutputs':[rel+'/'+x for x in names]+[rel+'/studio_metadata.json']}
    path=out/'smoke.job.json'; path.write_text(json.dumps(job,indent=2)+'\n'); validate_job(path)
    report=run_job(path,Path(o.blender).resolve())
    assert report['blender']['backend']=='legacy_cpu_4_2_3'
    meta=json.loads((out/'studio_metadata.json').read_text())
    preset=json.loads((REPO/'tools/tycoon_photo_studio/studio_presets/ch_tycoon_studio_v1.json').read_text())
    recipe=json.loads((REPO/'tools/tycoon_photo_studio/assets/tests/color_mask_smoke.asset.json').read_text())
    assert preset['visualContract']=='CH_STYLIZED_PRERENDER_V1'
    assert meta['samples']==preset['render']['samples']
    assert meta['sourceSummary']['materialCount']==len(recipe['materials'])
    assert meta['sourceSummary']['partCount']==len(recipe['parts'])
    assert meta['lighting']['lightNames']==[light['name'] for light in preset['lights']]
    assert meta['blenderVersion']=='4.2.3' and meta['cameraContract']=='CH_CAMERA_V1'
    assert meta['studioPreset']=='CH_TYCOON_STUDIO_V1' and meta['renderEngine']=='CYCLES'
    assert meta['footprint']=={'widthTiles':1,'depthTiles':1}
    assert meta['directionOrder']==['south','east','west','north']
    assert meta['lighting']['fixedAcrossDirections'] and not meta['rotationPolicy']['cameraRotates']
    origins=[direction['groundOriginSourcePx'] for direction in meta['directions']]
    assert all(all(abs(a-b)<1e-5 for a,b in zip(origin,origins[0])) for origin in origins)
    assert all(0<=value<=64 for value in origins[0])
    for direction in meta['directions']:
        assert all(math.isfinite(v) for v in direction['groundOriginSourcePx'])
    for name in names:
        with Image.open(out/name) as image:
            image.load(); assert image.format=='PNG' and image.mode=='RGBA' and image.size==(64,64)
            if '_color_' in name:
                lo,hi=image.getchannel('A').getextrema(); assert lo==0 and hi>0
    report['legacyChecks']={'fourDirections':True,'rgba':True,'camera':True,'footprint':True,'anchorFinite':True,'anchorFixedAcrossDirections':True,'materials':True,'styleContract':True,'fixedLighting':True,'visualEquivalenceApproved':False}
    (out/'worker.report.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps({'status':'ok','output':str(out),'checks':report['legacyChecks']},indent=2))
if __name__=='__main__': main()
