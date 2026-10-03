"""Pinned upstream checkout with ordered, hashed patches and a resumable state."""
import argparse,hashlib,json,subprocess
from pathlib import Path
COMMIT='0e22e4fcea037eeec1531fdbfc32d3acb88b4bd5'
def git(source,*args):
    return subprocess.run(['git','-C',str(source),*args],check=True,capture_output=True).stdout

def untracked_hash(source):
    names=git(source,"ls-files","--others","--exclude-standard","-z").decode().split("\0")
    values=[(name,hashlib.sha256((source/name).read_bytes()).hexdigest()) for name in sorted(filter(None,names))]
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()

def prepare(build_root):
    source=build_root/'blender-4.2.3-source'; here=Path(__file__).resolve().parent
    if not (source/'.git').exists():
        subprocess.run(['git','clone','--depth','1','--branch','v4.2.3','https://github.com/blender/blender.git',str(source)],check=True)
    if git(source,'rev-parse','HEAD').decode().strip()!=COMMIT: raise RuntimeError('Wrong Blender commit')
    state_file=build_root/'legacy-source-state.json'
    diff=git(source,'diff','--binary'); state=json.loads(state_file.read_text()) if state_file.exists() else {'patches':[],'diffSha256':hashlib.sha256(b'').hexdigest()}
    if hashlib.sha256(diff).hexdigest()!=state['diffSha256']: raise RuntimeError('Unrecorded upstream edits: preserve and inspect them before applying patches')
    patches=[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted((here/'patches').glob('*.patch'))]
    if 'untrackedSha256' not in state and state['patches']:
        from verify_patch_series import verify
        verify(source,here/'patches')
    elif 'untrackedSha256' in state and state['untrackedSha256']!=untracked_hash(source):
        raise RuntimeError('Unrecorded added upstream files')
    state['untrackedSha256']=untracked_hash(source)
    state_file.write_text(json.dumps(state,indent=2)+'\n')
    old=state['patches']
    if patches[:len(old)]!=old: raise RuntimeError('Applied patch changed; use a separate fresh BuildRoot')
    for entry in patches[len(old):]:
        patch=here/'patches'/entry['file']; git(source,'apply','--check',str(patch)); git(source,'apply',str(patch))
        old.append(entry); state={'upstreamCommit':COMMIT,'patches':old,'diffSha256':hashlib.sha256(git(source,'diff','--binary')).hexdigest(),'untrackedSha256':untracked_hash(source)}
        state_file.write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps({'source':str(source),'upstreamCommit':COMMIT,'patches':len(patches)},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('build_root',type=Path);a=p.parse_args();prepare(a.build_root)
