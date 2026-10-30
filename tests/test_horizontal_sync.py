#!/usr/bin/env python3
"""Line timing should follow qualified sync pulses, not a free-running timer."""
from gnuradio import gr, blocks, NTSC

for rate in (4e6, 8e6, 20e6):
    signal = []
    markers = []
    for line in range(150):
        signal += [-.04] * round(4.7e-6 * rate)
        signal += [-.015] * round(4.7e-6 * rate)
        markers.append(len(signal) + round(20e-6 * rate))
        active = [.02] * round(52.6e-6 * rate)
        # Short interference spike within the picture must not rephase a line.
        at = round(10e-6 * rate)
        active[at:at + round(.5e-6 * rate)] = [-.04] * round(.5e-6 * rate)
        signal += active
        signal += [-.015] * round((1.55 + (.5 if line % 2 else -.5)) * 1e-6 * rate)
    tb = gr.top_block()
    source = blocks.vector_source_f(signal, False)
    decoder = NTSC.decoder_c(rate, 0)
    sinks = [blocks.vector_sink_f() for _ in range(4)]
    tb.connect(source, decoder)
    for i, sink in enumerate(sinks):
        tb.connect((decoder, i), sink)
    tb.run(97)
    xs = [sinks[1].data()[m] for m in markers[2:]]
    ys = [sinks[2].data()[m] for m in markers[2:]]
    assert max(xs) - min(xs) <= 2, (rate, min(xs), max(xs))
    assert all(b - a == 1 for a, b in zip(ys, ys[1:])), (rate, ys)
    assert all(sinks[0].data()[m] == 6 for m in markers[2:])
    print('PASS: %.0f MS/s line jitter tracks within two pixels; no lost/duplicated rows' % (rate/1e6))
