"""Disassembly windows for explicit review of code/data and dispatch inventory."""
import argparse,collections,json,subprocess
from pathlib import Path
from audit_binary import LINE
p=argparse.ArgumentParser();p.add_argument('--groups',required=True,type=Path);p.add_argument('--binary',required=True,type=Path);p.add_argument('--dumpbin',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args();groups=json.loads(a.groups.read_text(encoding='utf-8'))['groups'];targets=sorted((int(g['start'],16),g) for g in groups if not g['origin'].startswith('msvcprt:'));history=collections.deque(maxlen=18);index=0;active=[];reports=[]
process=subprocess.Popen([a.dumpbin,'/DISASM:NOBYTES',str(a.binary)],stdout=subprocess.PIPE,text=True,errors='replace')
for line in process.stdout:
 m=LINE.match(line)
 if not m:continue
 address=int(m[1],16)
 while index<len(targets) and address>=targets[index][0]:
  report={'group':targets[index][1],'context':list(history),'remaining':24};active.append(report);reports.append(report);index+=1
 for report in active:report['context'].append(line.strip());report['remaining']-=1
 active=[r for r in active if r['remaining']>0];history.append(line.strip())
 if index==len(targets) and not active:process.stdout.close();process.terminate();break
process.wait()
for report in reports:report.pop('remaining',None)
a.output.write_text(json.dumps(reports,indent=2)+'\n',encoding='utf-8');print('Disassembly review windows:',len(reports))