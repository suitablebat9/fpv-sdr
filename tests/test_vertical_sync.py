#!/usr/bin/env python3
"""Short glitches in active video must not reset the field counter."""
from gnuradio import gr, blocks, NTSC

for rate in (4e6, 8e6, 20e6):
    def samples(level, seconds):
        return [level] * round(seconds * rate)
    signal = samples(-.015, 5e-6) + samples(-.04, 4.7e-6)
    signal += samples(-.015, 5e-6) + samples(.02, 20e-6)
    glitch = len(signal)
    signal += samples(-.04, 1e-6) + samples(.02, 35e-6)
    broad = len(signal)
    signal += samples(-.04, 25e-6) + samples(-.015, 20e-6)
    tb = gr.top_block()
    source = blocks.vector_source_f(signal, False)
    decoder = NTSC.decoder_c(rate, 0)
    sink = blocks.vector_sink_f()
    tb.connect(source, decoder)
    tb.connect((decoder, 0), sink)
    nulls = [blocks.null_sink(gr.sizeof_float) for _ in range(3)]
    for i, null in enumerate(nulls, 1):
        tb.connect((decoder, i), null)
    tb.run(37)
    states = sink.data()
    assert 7 not in states[glitch:broad], 'short glitch triggered vertical sync'
    assert 7 in states[broad:broad + round(25e-6 * rate)], 'broad sync missed'
    print('PASS: short glitch rejected and broad sync detected at %.0f MS/s' % (rate / 1e6))
