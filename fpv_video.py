"""Signal-based analog video acquisition, independent of the radio backend."""
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class VideoEstimate:
    standard: str
    scale: float
    offset: float
    confidence: float
    line_us: float
    field_ms: float | None


def estimate_video(samples, rate):
    """Find periodic sync pulses before trusting levels or a video standard.

    Returns None for unrecognized/noisy input. Both FM polarities are tried.
    Standard comes from field cadence when present, otherwise line cadence.
    """
    x = np.asarray(samples, dtype=np.float64)
    if len(x) < rate * .04 or not np.all(np.isfinite(x)):
        return None
    best = None
    for polarity in (1, -1):
        y = polarity * x
        qs = np.percentile(y, [2, 12, 20, 30])
        if qs[-1] - qs[0] < 1e-7:
            continue
        for upper in qs[1:]:
            threshold = (qs[0] + upper) / 2
            low = y < threshold
            edges = np.diff(low.astype(np.int8))
            starts = np.flatnonzero(edges == 1) + 1
            ends = np.flatnonzero(edges == -1) + 1
            if len(starts) == 0 or len(ends) == 0:
                continue
            ends = ends[ends > starts[0]]
            starts = starts[:len(ends)]
            ends = ends[:len(starts)]
            widths = (ends - starts) / rate
            keep = (widths >= 2.5e-6) & (widths <= 7.5e-6)
            hs = ends[keep]
            begins = starts[keep]
            if len(hs) < 40:
                continue
            # Interpolate threshold crossings to avoid 1-us quantization in
            # the 1 MS/s analysis stream masking NTSC/PAL's line difference.
            positions = hs - 1 + (threshold-y[hs-1]) / np.maximum(y[hs]-y[hs-1], 1e-15)
            dt = np.diff(positions) / rate
            regular = (dt > 61e-6) & (dt < 66e-6)
            fraction = float(np.mean(regular))
            coverage = int(np.sum(regular)) / (len(x) / rate / 64e-6)
            confidence = min(fraction, coverage)
            if confidence < .60:
                continue
            line_us = float(np.median(dt[regular]) * 1e6)
            if not 62.9 < line_us < 64.5:
                continue
            broad = starts[(widths > 15e-6) & (widths < 35e-6)]
            field_ms = None
            if len(broad) > 1:
                groups = broad[np.r_[True, np.diff(broad) > rate * .003]]
                gaps = np.diff(groups) / rate
                gaps = gaps[(gaps > .014) & (gaps < .023)]
                if len(gaps) >= 2:
                    field_ms = float(np.median(gaps) * 1000)
            standard = ('pal' if field_ms > 18.3 else 'ntsc') if field_ms else ('pal' if line_us > 63.78 else 'ntsc')
            valid = hs + int(rate * 2e-6) < len(y)
            hs, begins = hs[valid], begins[valid]
            tips = y[(begins + hs) // 2]
            porch = y[hs + max(1, int(rate * 1.5e-6))]
            tip, blank = float(np.median(tips)), float(np.median(porch))
            if blank - tip < 1e-7:
                continue
            # Preserve the threshold whose pulse train was validated. Some
            # transmitters have pedestal/burst distortion, making a textbook
            # tip/porch mapping place dark picture content below sync level.
            white = float(np.percentile(y, 98))
            if white - threshold < 1e-7:
                continue
            gain = .08 / (white - threshold)
            if (threshold - tip) * gain < .003:
                continue
            result = VideoEstimate(standard, polarity * gain, -.020 - gain * threshold,
                                   confidence, line_us, field_ms)
            if best is None or confidence > best.confidence:
                best = result
    return best
