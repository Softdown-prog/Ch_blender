"""Run inside the exact Blender 4.2.3 Legacy executable."""
import bpy, json, sys, _cycles
import ssl, zlib, ctypes, numpy, addon_utils
from pathlib import Path
from mathutils import Vector
out=Path(sys.argv[sys.argv.index('--')+1]); out.mkdir(parents=True,exist_ok=True)
assert bpy.app.version == (4,2,3), bpy.app.version
assert bpy.app.background
marker=json.loads((Path(bpy.app.binary_path).parent/'ch-legacy-build.json').read_text(encoding='utf-8'))
assert bool(_cycles.with_embree)==bool(marker.get('experimentalEmbreeSSE2',False))
assert not _cycles.with_openimagedenoise and not _cycles.with_path_guiding and not _cycles.with_osl
build_options={name:getattr(bpy.app.build_options,name) for name in dir(bpy.app.build_options) if not name.startswith('_') and isinstance(getattr(bpy.app.build_options,name),bool)}
for option in ('cycles','compositor_cpu','opensubdiv','opencolorio','image_openexr'):
    assert build_options[option],option
for option in ('cycles_osl','audaspace','openvdb','fluid','usd','xr_openxr'):
    assert not build_options[option],option
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(size=2)
cube=bpy.context.object
bevel=cube.modifiers.new('SmokeBevel','BEVEL'); bevel.width=0.12; bevel.segments=2
subsurf=cube.modifiers.new('SmokeSubdivision','SUBSURF'); subsurf.levels=1
bpy.context.view_layer.update()
evaluated=cube.evaluated_get(bpy.context.evaluated_depsgraph_get())
assert len(evaluated.data.vertices)>8, 'Required modifiers did not evaluate'
assert numpy.isfinite(numpy.array([1.,2.])).all()
assert zlib.decompress(zlib.compress(b'legacy'))==b'legacy'
assert ctypes.sizeof(ctypes.c_void_p)==8

material=bpy.data.materials.new('SmokeMaterial'); material.use_nodes=True
material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(0.6,0.18,0.05,1)
texture=bpy.data.images.new('SmokeTexture',width=2,height=2,alpha=True)
texture.pixels=[0.6,0.18,0.05,1., 0.2,0.4,0.8,1., 0.2,0.4,0.8,1., 0.6,0.18,0.05,1.]
texture.file_format='PNG'; texture.filepath_raw=str(out/'input-texture.png');texture.save()
texture=bpy.data.images.load(str(out/'input-texture.png'),check_existing=False)
node=material.node_tree.nodes.new('ShaderNodeTexImage');node.image=texture
material.node_tree.links.new(node.outputs['Color'],material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
cube.data.materials.append(material)
camera=bpy.data.cameras.new('SmokeCamera'); camera.type='ORTHO'; camera.ortho_scale=5
obj=bpy.data.objects.new('SmokeCamera',camera); bpy.context.collection.objects.link(obj)
obj.location=(4,-6,4); obj.rotation_euler=(-obj.location).to_track_quat('-Z','Y').to_euler()
scene=bpy.context.scene; scene.camera=obj
light=bpy.data.lights.new('SmokeArea','AREA'); light.energy=1000; light.size=4
obj=bpy.data.objects.new('SmokeArea',light); bpy.context.collection.objects.link(obj); obj.location=(2,-3,5)
obj.rotation_euler=(-obj.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=4
scene.cycles.use_denoising=False
scene.render.resolution_x=64; scene.render.resolution_y=64; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGBA'; scene.render.film_transparent=True
for addon in ('io_scene_fbx','io_scene_gltf2'):
    addon_utils.enable(addon,default_set=False,persistent=False)
    assert addon_utils.check(addon)[1], addon
bpy.ops.object.select_all(action='DESELECT'); cube.select_set(True); bpy.context.view_layer.objects.active=cube
fbx=out/'smoke.fbx'; glb=out/'smoke.glb'
assert 'FINISHED' in bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True)
assert 'FINISHED' in bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True)
for operator,path in ((bpy.ops.import_scene.fbx,fbx),(bpy.ops.import_scene.gltf,glb)):
    existing=set(bpy.data.objects)
    assert 'FINISHED' in operator(filepath=str(path))
    imported=set(bpy.data.objects)-existing
    assert any(obj.type=='MESH' for obj in imported)
    for imported_object in imported:
        bpy.data.objects.remove(imported_object,do_unlink=True)
blend=out/'smoke.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(blend)); bpy.ops.wm.open_mainfile(filepath=str(blend))
scene=bpy.context.scene; scene.render.filepath=str(out/'cycles.png'); bpy.ops.render.render(write_still=True)
image=bpy.data.images.load(str(out/'cycles.png'),check_existing=False)
assert tuple(image.size)==(64,64) and image.channels==4
exr=out/'smoke.exr'; image.file_format='OPEN_EXR'; image.filepath_raw=str(exr); image.save()
loaded=bpy.data.images.load(str(exr),check_existing=False); assert tuple(loaded.size)==(64,64)
alpha=list(image.pixels)[3::4]; assert max(alpha)>0.9 and min(alpha)==0
report={'status':'ok','version':bpy.app.version_string,'background':bpy.app.background,'engine':scene.render.engine,'device':scene.cycles.device,'denoising':scene.cycles.use_denoising,'rgba':True,'size':list(image.size),'blendRoundTrip':True,'python':sys.version,'buildOptions':build_options,'pythonModules':['ssl','zlib','ctypes','numpy'],'openssl':ssl.OPENSSL_VERSION,'modifiers':['BEVEL','SUBSURF'],'fbxRoundTrip':True,'gltfRoundTrip':True,'openexrRoundTrip':True,'cyclesImageTexture':True,'embreeCompiled':bool(_cycles.with_embree),'openImageDenoiseCompiled':bool(_cycles.with_openimagedenoise),'pathGuidingCompiled':bool(_cycles.with_path_guiding)}
(out/'cycles-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('CH_LEGACY_CYCLES_SMOKE_OK')
