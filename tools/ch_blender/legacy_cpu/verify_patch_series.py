"""Replay every upstream patch in a temporary tree and compare patched files."""
import argparse, subprocess, tempfile
from pathlib import Path

def verify(source, patches):
    patches = sorted(Path(patches).glob('*.patch'))
    touched=set()
    originals=set()
    for patch in patches:
        for line in patch.read_text().splitlines():
            if line.startswith('--- a/'):
                originals.add(line[6:].split('\t')[0])
            elif line.startswith('+++ b/'):
                touched.add(line[6:].split('\t')[0])
    with tempfile.TemporaryDirectory(prefix='ch-legacy-patches-') as temp:
        root=Path(temp)
        for relative in originals:
            result=subprocess.run(['git','-C',str(source),'show','HEAD:'+relative],capture_output=True)
            if result.returncode==0:
                target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(result.stdout)
        for patch in patches:
            subprocess.run(['git','apply','--check',str(patch.resolve())],cwd=root,check=True,capture_output=True)
            subprocess.run(['git','apply',str(patch.resolve())],cwd=root,check=True,capture_output=True)
        for relative in touched:
            if (root/relative).read_text()!= (Path(source)/relative).read_text():
                raise RuntimeError('Upstream file differs from recorded patches: '+relative)
    print('Patch replay verified:',len(patches),'patches;',len(touched),'files')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('patches',type=Path);args=parser.parse_args();verify(args.source,args.patches)
