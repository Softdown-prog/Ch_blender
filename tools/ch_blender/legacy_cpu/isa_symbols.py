"""Attribute elevated ISA inventory to MSVC map symbols; no automatic approval."""
import argparse,bisect,collections,hashlib,json,re,subprocess
from pathlib import Path
from audit_binary import LINE,SSE4,SSSE3,OTHER
p=argparse.ArgumentParser();p.add_argument('--map',required=True,type=Path);p.add_argument('--binary',required=True,type=Path);p.add_argument('--dumpbin',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
pattern=re.compile(r'^\s*0001:[0-9a-fA-F]+\s+(\S+)\s+([0-9a-fA-F]{16})\s+(.+)$')
symbols=[]
for line in a.map.read_text(encoding='utf-8',errors='replace').splitlines():
 m=pattern.match(line)
 if m:symbols.append((int(m[2],16),m[1],m[3].split()[-1]))
HIGH=SSE4|SSSE3|OTHER
symbols.sort();addresses=[x[0] for x in symbols];groups={}
process=subprocess.Popen([a.dumpbin,'/DISASM:NOBYTES',str(a.binary)],stdout=subprocess.PIPE,text=True,errors='replace')
for line in process.stdout:
 m=LINE.match(line)
 if not m:continue
 op=m[2].lower()
 if op not in HIGH and not(op.startswith('v') and op not in {'verr','verw'}):continue
 index=bisect.bisect_right(addresses,int(m[1],16))-1
 symbol=symbols[index] if index>=0 else (0,'UNKNOWN','UNKNOWN')
 key=symbol[2]+'|'+symbol[1]
 group=groups.setdefault(key,{'symbol':symbol[1],'origin':symbol[2],'start':hex(symbol[0]),'instructions':collections.Counter(),'examples':[]})
 group['instructions'][op]+=1
 if len(group['examples'])<4:group['examples'].append(line.strip())
if process.wait()!=0:raise RuntimeError('dumpbin failed')
a.output.write_text(json.dumps({'binarySha256':hashlib.sha256(a.binary.read_bytes()).hexdigest(),'mapSha256':hashlib.sha256(a.map.read_bytes()).hexdigest(),'status':'review_required','symbols':len(symbols),'groups':list(groups.values())},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'groups':len(groups),'origins':dict(collections.Counter(g['origin'] for g in groups.values()))},indent=2))