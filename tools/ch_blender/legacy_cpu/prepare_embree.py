"""Pinned, isolated Embree 4.3.2-blender experiment; never replaces Legacy."""
import hashlib,json,sys,urllib.request,zipfile
from pathlib import Path
URL='https://github.com/embree/embree/archive/v4.3.2-blender.zip'
MD5='91bd65e59c6cf4d9ff0e4d628aa28d6a'
def main(root):
 root=Path(root);archive=root/'deps/downloads/embree-v4.3.2-blender.zip';archive.parent.mkdir(parents=True,exist_ok=True)
 if not archive.exists():
  partial=archive.with_suffix('.partial');urllib.request.urlretrieve(URL,partial)
  if hashlib.md5(partial.read_bytes()).hexdigest()!=MD5:raise RuntimeError('Embree source hash mismatch')
  partial.rename(archive)
 if hashlib.md5(archive.read_bytes()).hexdigest()!=MD5:raise RuntimeError('Embree source hash mismatch')
 destination=root/'embree-source'
 if not (destination/'embree-4.3.2-blender/CMakeLists.txt').exists():
  with zipfile.ZipFile(archive) as z:
   for name in z.namelist():
    if not (destination/name).resolve().is_relative_to(destination.resolve()):raise RuntimeError('Unsafe ZIP entry')
   z.extractall(destination)
 print(json.dumps({'source':str(destination/'embree-4.3.2-blender'),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}))
if __name__=='__main__':main(sys.argv[1])