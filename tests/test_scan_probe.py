#!/usr/bin/env python3
"""Each confirmation must use fresh samples after the channel changes."""
import sys, threading, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from fpv_autovideo import video_probe
from test_video_acquisition import composite
probe=video_probe(1e6)
for standard in ('ntsc','pal'):
    # Feed old/noise data while disarmed; it must not be part of acquisition.
    probe.work([np.zeros(350000,dtype=np.float32)],[])
    results=[]
    thread=threading.Thread(target=lambda: results.append(probe.capture(timeout=2)))
    thread.start()
    deadline=time.monotonic()+1
    while not probe.collecting and time.monotonic()<deadline: time.sleep(.001)
    assert probe.collecting
    data=np.tile(composite(standard).astype(np.float32),2)
    for i in range(0,len(data),8192): probe.work([data[i:i+8192]],[])
    thread.join(2)
    assert not thread.is_alive() and results[0].standard==standard,results
try: probe.capture(timeout=.01)
except RuntimeError: pass
else: raise AssertionError('stalled stream should fail')
assert not probe.collecting
print('PASS: fresh NTSC/PAL captures and stalled-stream error')
