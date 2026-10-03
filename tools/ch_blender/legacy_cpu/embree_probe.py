"""Actual Phenom execution of isolated Embree SSE2 triangle intersection."""
import ctypes as c,json,os,sys
from pathlib import Path
root=Path(sys.argv[1]);handles=[os.add_dll_directory(str(folder)) for folder in [root/'deps/embree-sse2/bin']+list((root/'deps/output').glob('*/bin'))+list((root/'deps/output').glob('*/lib'))];tbb=c.WinDLL(str(root/'deps/output/tbb/bin/tbb.dll'));dll=c.CDLL(str(root/'deps/embree-sse2/bin/embree4.dll'))
def bind(name,restype,*args):
 fn=getattr(dll,name);fn.restype=restype;fn.argtypes=list(args);return fn
P=c.c_void_p;U=c.c_uint;Z=c.c_size_t
newdevice=bind('rtcNewDevice',P,c.c_char_p);error=bind('rtcGetDeviceError',c.c_int,P);newscene=bind('rtcNewScene',P,P);newgeo=bind('rtcNewGeometry',P,P,c.c_int);buffer=bind('rtcSetNewGeometryBuffer',P,P,c.c_int,U,c.c_int,Z,Z);commitgeo=bind('rtcCommitGeometry',None,P);attach=bind('rtcAttachGeometry',U,P,P);commitscene=bind('rtcCommitScene',None,P);intersect=bind('rtcIntersect1',None,P,P,P)
class Ray(c.Structure):_fields_=[(name,c.c_float) for name in ('org_x','org_y','org_z','tnear','dir_x','dir_y','dir_z','time','tfar')]+[(name,U) for name in ('mask','id','flags')]
class Hit(c.Structure):_fields_=[(name,c.c_float) for name in ('Ng_x','Ng_y','Ng_z','u','v')]+[(name,U) for name in ('primID','geomID','instID','instPrimID')]+[('padding',U*3)]
class RayHit(c.Structure):_fields_=[('ray',Ray),('hit',Hit)]
device=newdevice(b'threads=2');assert device and error(device)==0
scene=newscene(device);geometry=newgeo(device,0);assert scene and geometry
vertices=buffer(geometry,1,0,0x9003,12,3);indices=buffer(geometry,0,0,0x5003,12,1);assert vertices and indices
(c.c_float*9).from_address(vertices)[:]=[0,0,0,1,0,0,0,1,0];(U*3).from_address(indices)[:]=[0,1,2];commitgeo(geometry);geometry_id=attach(scene,geometry);commitscene(scene);assert error(device)==0
storage=c.create_string_buffer(c.sizeof(RayHit)+16);offset=(-c.addressof(storage))%16;rayhit=RayHit.from_buffer(storage,offset);rayhit.ray.org_x=.25;rayhit.ray.org_y=.25;rayhit.ray.org_z=-1;rayhit.ray.dir_z=1;rayhit.ray.tfar=100;rayhit.ray.mask=0xffffffff;rayhit.hit.geomID=0xffffffff;rayhit.hit.instID=0xffffffff
intersect(scene,c.byref(rayhit),None);assert error(device)==0;assert rayhit.hit.geomID==geometry_id and abs(rayhit.ray.tfar-1)<1e-6
bind('rtcReleaseGeometry',None,P)(geometry);bind('rtcReleaseScene',None,P)(scene);bind('rtcReleaseDevice',None,P)(device)
report={'status':'ok','library':'Embree 4.3.2-blender','maxISA':'SSE2','deviceCreated':True,'triangleIntersection':True,'hitDistance':rayhit.ray.tfar,'blenderIntegrationValidated':False};(root/'validation/embree-probe.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))