"""Record the actual local build without claiming runtime or ISA validation."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('install',type=Path);a=p.parse_args()
 build=a.root/'build-legacy';source=a.root/'blender-4.2.3-source'
 info=json.loads((HERE/'build-manifest.json').read_text(encoding='utf-8'))
 cache={}
 for line in (build/'CMakeCache.txt').read_text(encoding='utf-8').splitlines():
  if line and not line.startswith(('#','//')) and '=' in line:
   key,value=line.split('=',1);cache[key.split(':',1)[0]]=value
 for key in ('WITH_CPU_CHECK','WITH_CPU_SIMD','WITH_OPENIMAGEDENOISE','WITH_CYCLES_EMBREE','WITH_CYCLES_PATH_GUIDING'):
  if cache.get(key)!='OFF':raise RuntimeError('Unsafe effective option: '+key)
 compiler_files=list((build/'CMakeFiles').glob('*/CMakeCXXCompiler.cmake'))
 compiler=compiler_files[0].read_text(encoding='utf-8')
 version=re.search(r'set\(CMAKE_CXX_COMPILER_VERSION "([^"]+)"\)',compiler).group(1)
 info['compiler']='MSVC '+version+' x64'
 info['cpu']=json.loads((a.root/'cpu.json').read_text(encoding='utf-8-sig'))
 info['installPath']=str(a.install.resolve())
 info['effectiveOptions']={key:value for key,value in sorted(cache.items()) if key.startswith('WITH_')}
 info['effectiveCompilerFlags']={key:value for key,value in cache.items() if key.startswith(('CMAKE_C_FLAGS','CMAKE_CXX_FLAGS'))}
 info['patches']=[{'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()} for file in sorted((HERE/'patches').glob('*.patch'))]
 info['binaries']=[{'file':file.relative_to(a.install).as_posix(),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()} for file in sorted(a.install.rglob('*')) if file.suffix.lower() in ('.exe','.dll','.pyd')]
 info['status']='built_unvalidated'
 (a.install/'ch-legacy-build.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'status':info['status'],'compiler':info['compiler'],'binaries':len(info['binaries'])}))
if __name__=='__main__':main()
