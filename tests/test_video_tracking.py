#!/usr/bin/env python3
"""Track gradual level changes but freeze calibration on noise/wrong format."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from test_video_acquisition import composite, rate
from fpv_video import estimate_video
from fpv_autovideo import adaptive_video, receiver_agc

base = composite('ntsc').astype(np.float32)
initial = estimate_video(base, rate)
tracker = adaptive_video(rate, initial)
changed = base*.7 + .03
expected = estimate_video(changed, rate)
def feed(signal, seconds):
    stream = np.tile(signal, int(np.ceil(seconds*rate/len(signal))))
    for start in range(0, len(stream), 8192):
        chunk = stream[start:start+8192]
        output = np.empty_like(chunk)
        assert tracker.work([chunk], [output]) == len(chunk)
        assert np.all(np.isfinite(output))
feed(changed, 14)
assert abs(tracker.scale/expected.scale-1) < .03, (tracker.scale,expected.scale)
assert abs(tracker.offset-expected.offset)<.003
before = (tracker.scale,tracker.offset)
feed(np.random.default_rng(4).normal(0,.1,len(base)).astype(np.float32), 3)
assert before == (tracker.scale,tracker.offset)
feed(composite('pal').astype(np.float32), 3)
assert before == (tracker.scale,tracker.offset)
class Unsupported:
    def set_gain_mode(self,*args): raise RuntimeError('unsupported')
assert not receiver_agc(Unsupported(), 'pluto')
assert not receiver_agc(object(), 'uhd')
print('PASS: level drift tracked; noise and different standard cannot change calibration; unsupported AGC falls back')
