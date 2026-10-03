"""Conservative executable-section ISA inventory; review dispatch hits explicitly."""
import argparse,collections,hashlib,json,re,struct,subprocess
from pathlib import Path
SSE4=set("blendpd blendps blendvpd blendvps dppd dpps extractps insertps movntdqa mpsadbw packusdw pblendvb pblendw pcmpeqq pextrb pextrd pextrq phminposuw pinsrb pinsrd pinsrq pmaxsb pmaxsd pmaxud pmaxuw pminsb pminsd pminud pminuw pmovsxbd pmovsxbq pmovsxbw pmovsxdq pmovsxwd pmovsxwq pmovzxbd pmovzxbq pmovzxbw pmovzxdq pmovzxwd pmovzxwq pmuldq pmulld ptest roundpd roundps roundsd roundss crc32 pcmpestri pcmpestrm pcmpistri pcmpistrm pcmpgtq".split())
SSSE3=set("pshufb palignr pmaddubsw pmulhrsw pabsb pabsw pabsd phaddw phaddd phaddsw phsubw phsubd phsubsw psignb psignw psignd".split())
OTHER=set("pclmulqdq aesenc aesenclast aesdec aesdeclast aesimc aeskeygenassist andn bextr blsi blsmsk blsr bzhi mulx pdep pext rorx sarx shlx shrx".split())
LINE=re.compile(r'^\s*([0-9A-Fa-f]+):\s+([a-z][a-z0-9]*)\b')
def has_executable_sections(file):
    with file.open('rb') as stream:
        if stream.read(2)!=b'MZ':raise RuntimeError('Not a PE binary: '+str(file))
        stream.seek(0x3c);pe=struct.unpack('<I',stream.read(4))[0];stream.seek(pe)
        if stream.read(4)!=b'PE\0\0':raise RuntimeError('Bad PE signature')
        header=stream.read(20);sections=struct.unpack_from('<H',header,2)[0];optional=struct.unpack_from('<H',header,16)[0]
        stream.seek(pe+24+optional)
        return any(struct.unpack_from('<I',stream.read(40),36)[0]&0x20000000 for _ in range(sections))

def scan(file,dumpbin):
    process=subprocess.Popen([str(dumpbin),'/DISASM:NOBYTES',str(file)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
    counts=collections.Counter(); examples=[];total=0
    for line in process.stdout:
        match=LINE.match(line)
        if not match:continue
        total+=1;op=match[2].lower()
        if op in SSE4 or op in SSSE3 or op in OTHER or (op.startswith('v') and op not in {'verr','verw'}):
            counts[op]+=1
            if len(examples)<15:examples.append(line.strip())
    executable=has_executable_sections(file)
    if process.wait()!=0 or (total==0 and executable):raise RuntimeError('Unable to disassemble '+str(file))
    return {'path':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'instructionsDecoded':total,'executableSections':executable,'elevatedISA':dict(counts),'examples':examples}
def main():
    a=argparse.ArgumentParser();a.add_argument('--dumpbin',required=True,type=Path);a.add_argument('--output',required=True,type=Path);a.add_argument('--review',type=Path);a.add_argument('paths',nargs='+',type=Path);o=a.parse_args()
    files=[]
    for path in o.paths:
        if path.is_file():files.append(path)
        else:files.extend(p for p in path.rglob('*') if p.suffix.lower() in {'.dll','.pyd','.exe'})
    reports=[scan(file,o.dumpbin) for file in sorted(set(files))]
    report={'status':'review_required' if any(r['elevatedISA'] for r in reports) else 'no_elevated_isa_decoded','files':reports,'scope':'Conservative linear disassembly; dispatch and code/data ambiguity require review; pair with real Phenom execution tests.'}
    if o.review:
        review=json.loads(o.review.read_text(encoding='utf-8'))
        if review.get('status')!='approved_for_tested_pipeline' or len(o.paths)!=1 or not o.paths[0].is_dir():
            raise RuntimeError('Review requires one installation root and an explicit approved scope')
        current={Path(r['path']).relative_to(o.paths[0]).as_posix().lower():(r['sha256'],r['elevatedISA']) for r in reports}
        expected={r['file'].lower():(r['sha256'],r['elevatedISA']) for r in review['files']}
        if current!=expected:
            report['reviewError']='Artifact hashes or ISA inventory changed; fresh review required'
        else:
            report['status']='approved_for_tested_pipeline';report['reviewScope']=review['scope'];report['reviewSha256']=hashlib.sha256(o.review.read_bytes()).hexdigest()
    o.output.parent.mkdir(parents=True,exist_ok=True);o.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'files':len(reports),'report':str(o.output)},indent=2))
    return 1 if report['status']=='review_required' or report.get('reviewError') else 0
if __name__=='__main__':raise SystemExit(main())
