"""Reject elevated ISA flags in generated build commands; not a binary proof."""
import argparse, json, re, subprocess
from pathlib import Path
FORBIDDEN = re.compile(r"(?i)(?:/arch:(?:AVX\w*|SSE4\w*)|-m(?:sse4[^\s;]*|ssse3|avx[^\s;]*|f16c|fma|bmi2?)|-march=(?:native|x86-64-v[234])|(?:__SSE4_[12]__|__AVX2?__))")
def audit(paths):
    failures=[]; count=0
    for directory in paths:
        for build in Path(directory).rglob('build.ninja'):
            result=subprocess.run(['ninja','-C',str(build.parent),'-t','commands'],capture_output=True,text=True,check=True)
            for line in result.stdout.splitlines():
                count+=1
                match=FORBIDDEN.search(line)
                if match: failures.append({'build':str(build),'flag':match.group(),'command':line})
    report={'status':'failed' if failures else 'ok','commandsChecked':count,'failures':failures,'binaryAuditComplete':False}
    print(json.dumps(report,indent=2)); return report
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('paths',nargs='+'); a=p.parse_args()
    report=audit(a.paths)
    raise SystemExit(1 if report['failures'] or not report['commandsChecked'] else 0)
