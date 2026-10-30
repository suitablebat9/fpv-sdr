#!/usr/bin/env python3
"""End-to-end FM acquisition/decoding without hardware or a display window."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import time
import numpy as np
import fpv_viewer as V
from gnuradio import blocks
from PIL import Image

rate = 8e6
for standard, polarity in [('ntsc',1), ('pal',-1)]:
    duration = .24
    t = np.arange(int(duration*rate))/rate
    line = 1/(15734.264 if standard == 'ntsc' else 15625)
    field = 1/(59.94 if standard == 'ntsc' else 50)
    phase = np.mod(t, line)
    video = -.01 + .065*np.mod(t,field)/field
    composite = np.where(phase < 4.7e-6, -.04, np.where(phase < 10e-6, -.015, video))
    vertical = np.mod(t,field) < line*1.5
    composite[vertical] = np.where(np.mod(t[vertical],line/2)<27e-6,-.04,-.015)
    demod = polarity*.35*composite + .004
    iq = np.exp(1j*np.cumsum(demod)/V.quad_demod_gain(rate)).astype(np.complex64)
    source = blocks.vector_source_c(iq.tolist(), True)
    old = V.build_source
    V.build_source = lambda *a, **k: (source, lambda f: None)
    try:
        tb = V.viewer('pluto', rate, 5800e6, 15, '', None,
                      standard='auto', auto_video=True, dcblock=False,
                      live=False, frame_out='/tmp/fpv-auto-%s.png'%standard)
    finally:
        V.build_source = old
    assert tb.standard == standard, tb.standard
    assert np.sign(tb.auto_video.scale) == polarity
    tb.start()
    time.sleep(1.5)
    tb.stop(); tb.wait()
    image = np.asarray(Image.open('/tmp/fpv-auto-%s.png'%standard))
    assert image.shape == (240 if standard=='ntsc' else 288, 360), image.shape
    assert np.ptp(image[5:-5,5:-5].astype(float).mean(axis=1)) > 80
    assert tb.frame_sink_0.frame_count > 30
    print('PASS: %s %s FM acquired, normalized and decoded (%d frames)' %
          (standard, 'normal' if polarity>0 else 'inverted',tb.frame_sink_0.frame_count))
