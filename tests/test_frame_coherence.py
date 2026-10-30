#!/usr/bin/env python3
"""Changing fields must never be mixed within one displayed raster."""
import numpy as np
from gnuradio import gr, blocks, NTSC

for width, height in [(360, 240), (360, 288)]:
    pixels = width * height
    x = np.tile(np.arange(width, dtype=np.float32), height)
    y = np.repeat(np.arange(height, dtype=np.float32), width)
    fields = 8
    streams = [np.full(pixels * fields, 6, dtype=np.float32),
               np.tile(x, fields), np.tile(y, fields),
               np.repeat(np.array([30, 220] * (fields // 2), dtype=np.float32), pixels)]
    tb = gr.top_block()
    conv = NTSC.video_stream_converter_c(8e6, 1, width, height)
    sources = [blocks.vector_source_f(s.tolist(), False) for s in streams]
    for port, source in enumerate(sources):
        tb.connect(source, (conv, port))
    sink = blocks.vector_sink_s()
    tb.connect(conv, sink)
    tb.run(997)  # Force work calls to cross scanline and field boundaries.
    data = np.asarray(sink.data()).reshape(-1, height, width)
    values = []
    for frame in data:
        interior = frame[3:-2, 3:-2]
        unique = np.unique(interior)
        assert len(unique) == 1, (width, height, unique)
        values.append(int(unique[0]))
    assert 30 in values and 220 in values, values
    print('PASS: %dx%d alternating fields stay whole across work calls' % (width, height))
