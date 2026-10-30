#!/usr/bin/env python3
"""A weaker valid channel must survive stronger invalid candidates/aliases."""
import sys, io, math
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fpv_detect as D

rows = [('R7',5880e6,-15.8),('F8',5880e6,-15.8),('D6',5878e6,-15.8),
        ('E5',5885e6,-21.3),('E6',5905e6,-26.9),('A1',5865e6,-34.8)]
class FakeDetector:
    fft_norm_db = 0
    last = None
    result = 'ntsc'
    failure = False
    def __init__(self,*args,**kwargs):
        self.checked=[]; self.stopped=False; FakeDetector.last=self
    def start(self): pass
    def stop(self): self.stopped=True
    def wait(self): pass
    def survey(self,*args):
        # No narrow peak at A1; valid analog signals need not pass that gate.
        return {f:(10**(db/10),1,10**(db/10),1) for _,f,db in rows},10**(-63.3/10)
    def confirm_video(self,freq,settle):
        self.checked.append(freq)
        if self.failure: raise RuntimeError('device disconnected')
        if freq == 5865e6 and self.result:
            return SimpleNamespace(standard=self.result,confidence=.92)
        return None

def run(extra=()):
    out,err=io.StringIO(),io.StringIO()
    argv=['fpv_detect.py','--sdr','pluto',*extra,*['%s:%.0f'%(n,f) for n,f,_ in rows]]
    with patch.object(D,'detector',FakeDetector),patch.object(sys,'argv',argv),redirect_stdout(out),redirect_stderr(err):
        rc=D.main()
    return rc,out.getvalue(),err.getvalue()

rc,out,err=run()
assert rc==0 and 'HIT A1 5865000000' in out,(rc,out,err)
assert FakeDetector.last.checked==[5880e6,5878e6,5885e6,5905e6,5865e6]
assert FakeDetector.last.stopped
FakeDetector.result=None
rc,out,err=run()
assert rc==0 and 'HIT ' not in out
FakeDetector.result='ntsc'
rc,out,err=run(['--standard','pal'])
assert rc==0 and 'HIT ' not in out and 'does not match forced PAL' in err
rc,out,err=run(['--survey-only'])
assert rc==0 and not FakeDetector.last.checked
FakeDetector.failure=True
try: run()
except RuntimeError as e: assert 'disconnected' in str(e)
else: raise AssertionError('device failure was hidden')
assert FakeDetector.last.stopped
print('PASS: A1 found beyond top three; aliases deduplicated; broad signal accepted only on sync; empty/error/forced-standard/survey paths verified')
