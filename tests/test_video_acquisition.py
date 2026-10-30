#!/usr/bin/env python3
"""Acquisition across standards, polarity, FM deviation and carrier offsets."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from fpv_video import estimate_video

rng = np.random.default_rng(7)
rate = 1e6

def composite(standard, duration=.24):
    field = 1 / (59.94 if standard == 'ntsc' else 50)
    line = 1 / (15734.264 if standard == 'ntsc' else 15625)
    t = np.arange(round(duration*rate))/rate
    phase = np.mod(t, line)
    x = np.where(phase < 4.7e-6, -.04, np.where(phase < 10e-6, -.015, .02 + .03*np.sin(t*700)))
    # Broad vertical pulses over ~1.5 lines at each field boundary.
    vert = np.mod(t, field) < 3*line/2
    x[vert] = np.where(np.mod(t[vert], line/2) < 27e-6, -.04, -.015)
    return x

def run():
    for standard in ('ntsc', 'pal'):
        for gain in (.15, .5, 1, 3):
            for offset in (-.12, 0, .17):
                for polarity in (1, -1):
                    signal = polarity * composite(standard) * gain + offset
                    signal += rng.normal(0, .0005*gain, len(signal))
                    got = estimate_video(signal, rate)
                    assert got and got.standard == standard, (standard, gain, offset, polarity, got)
                    assert np.sign(got.scale) == polarity
                    tip = (polarity*(-.04)*gain+offset)*got.scale+got.offset
                    blank = (polarity*(-.015)*gain+offset)*got.scale+got.offset
                    assert tip < -.023 and blank > -.020, (got, tip, blank)
    for x in (np.zeros(240000), rng.normal(0,.1,240000), np.sin(np.arange(240000)*.07), np.full(240000,np.nan)):
        assert estimate_video(x,rate) is None
    print('PASS: 48 standard/level/offset/polarity cases; noise, tone, silence and NaN rejected')

if __name__ == '__main__':
    run()
