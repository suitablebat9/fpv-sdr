#!/usr/bin/env python3
"""Exercise the running scanner's real FM-to-sync confirmation branch."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import fpv_detect as D
from gnuradio import blocks
from test_video_acquisition import composite

for standard in ('ntsc','pal'):
    rate=8e6
    video=np.repeat(composite(standard),8)*.35+.004
    iq=np.exp(1j*np.cumsum(video)/D.quad_demod_gain(rate)).astype(np.complex64)
    source=blocks.vector_source_c(iq.tolist(),True)
    original=D.build_source
    D.build_source=lambda *args,**kwargs:(source,lambda f:None)
    try:
        tb=D.detector('pluto',rate,15,5865e6,'',None,want_lock=False,want_video=True)
    finally: D.build_source=original
    try:
        tb.start()
        estimate=tb.confirm_video(5865e6,0)
        assert estimate is not None and estimate.standard==standard,estimate
    finally:
        tb.stop();tb.wait()
    print('PASS: scanner flowgraph confirms %s sync on exact tuned channel'%standard)
