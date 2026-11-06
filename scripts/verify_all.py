"""Run the local milestone checks and preserve actual outcomes without provider calls."""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'submission'


def main():
    OUT.mkdir(exist_ok=True)
    logdir=ROOT/'artifacts/verification';logdir.mkdir(parents=True,exist_ok=True)
    npm='npm.cmd' if sys.platform=='win32' else 'npm'
    commands=[('frontend',[npm,'run','build','--prefix','frontend']),
              ('submission',[sys.executable,'scripts/build_submission.py']),
              ('source_package',[sys.executable,'scripts/package_source.py']),
              ('backend',[sys.executable,'-m','pytest','-q']),
              ('core_browser',[sys.executable,'tests/browser_core_check.py']),
              ('onboarding_browser',[sys.executable,'tests/browser_onboarding_check.py']),
              ('operations_browser',[sys.executable,'tests/browser_operations_check.py']),
              ('conversation_security_browser',[sys.executable,'tests/browser_conversation_security_check.py']),
              ('design_browser',[sys.executable,'tests/browser_design_check.py'])]
    results=[]
    for name,command in commands:
        start=time.monotonic();print(f'Checking {name}...',flush=True)
        try:
            run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240)
            output=run.stdout+'\n'+run.stderr
            status='passed' if run.returncode==0 else 'failed'
        except subprocess.TimeoutExpired:
            output='Check exceeded its 240-second local deadline.';status='timeout'
        (logdir/(name+'.log')).write_text(output,encoding='utf-8')
        result={'check':name,'status':status,'seconds':round(time.monotonic()-start,2)}
        if name=='backend':
            passed=re.search(r'(\d+) passed',output)
            if passed:result['tests_passed']=int(passed[1])
        if name.endswith('_browser') and status=='passed':
            payload=json.loads(output[:output.rfind('}')+1])
            result['scenario_groups']=len(payload['checks'])
        results.append(result)
        report={'checks':results,'all_passed':all(r['status']=='passed' for r in results) and len(results)==len(commands),
                'provider_calls':'Controlled SDK/browser fixtures only; no live quality claim',
                'pending_external_checks':['live image extraction and microphone/language quality','Docker image/runtime','hosted CI','live WhatsApp/provider setup'],
                'scope':'Local synthetic-data prototype. No real payment, provisioning, public deployment or submission performed.'}
        (OUT/'verification-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(f'{name}: {status}',flush=True)
        if status!='passed':print(f'Inspect artifacts/verification/{name}.log',flush=True);return 1
    print('All configured local checks passed; submission/verification-report.json records the actual counts.',flush=True)
    return 0


if __name__=='__main__':sys.exit(main())
