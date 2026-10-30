#!/usr/bin/env python3
"""A startup transient must not end acquisition before video becomes stable."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import fpv_sdr  # macOS UHD import ordering
from gnuradio import gr, blocks
from fpv_autovideo import acquire_video
from test_video_acquisition import composite

rate = 1e6
class Source(gr.hier_block2):
    def __init__(self, data):
        gr.hier_block2.__init__(self, 'paced synthetic receiver',
                               gr.io_signature(0, 0, 0),
                               gr.io_signature(1, 1, gr.sizeof_gr_complex))
        self.samples = blocks.vector_source_c(data.tolist(), True)
        self.pace = blocks.throttle(gr.sizeof_gr_complex, rate, True)
        self.connect(self.samples, self.pace, self)

for standard in ('ntsc', 'pal'):
    # First 350 ms capture has no video; subsequent windows have valid sync.
    demod = np.concatenate([np.zeros(450000), composite(standard, 1.5)*.05])
    iq = np.exp(1j*np.cumsum(demod)/fpv_sdr.quad_demod_gain(rate)).astype(np.complex64)
    result = acquire_video(Source(iq), rate)
    assert result and result.standard == standard, result
    print('PASS: %s recovered after startup transient without restarting source' % standard)
assert acquire_video(Source(np.ones(100000, dtype=np.complex64)), rate) is None
print('PASS: persistent no-sync signal still rejected after bounded retries')
