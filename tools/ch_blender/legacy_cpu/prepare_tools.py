"""Pinned portable Perl needed to rebuild OpenSSL from source."""
import hashlib,sys,urllib.request,zipfile
from pathlib import Path
URL='https://github.com/StrawberryPerl/Perl-Dist-Strawberry/releases/download/SP_5380_5361/strawberry-perl-5.38.0.1-64bit-portable.zip'
SHA256='ca6402a466939d5d658cc0d09a20dc59635ae68f6903a92a747a802539e40908'
def prepare(root):
    downloads=Path(root)/'deps/downloads'; downloads.mkdir(parents=True,exist_ok=True)
    archive=downloads/'strawberry-perl-5.38.0.1-64bit-portable.zip'
    if not archive.exists():
        partial=archive.with_suffix('.partial'); urllib.request.urlretrieve(URL,partial)
        if hashlib.sha256(partial.read_bytes()).hexdigest()!=SHA256: raise RuntimeError('Perl SHA256 mismatch')
        partial.rename(archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA256: raise RuntimeError('Perl SHA256 mismatch')
    destination=downloads/'perl'
    if not (destination/'perl/bin/perl.exe').is_file():
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                resolved=(destination/name).resolve()
                if not resolved.is_relative_to(destination.resolve()): raise RuntimeError('Unsafe archive path')
            z.extractall(destination)
    print('Portable Perl ready; build-only dependency.')
if __name__=='__main__':prepare(sys.argv[1])
