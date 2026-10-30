"""GNU Radio adapters for video acquisition and cautious level tracking."""
import sys
import time
import numpy as np
from gnuradio import gr, blocks, analog, filter
from gnuradio.filter import firdes
from gnuradio.fft import window
from fpv_sdr import quad_demod_gain, UHD_ALIASES
from fpv_video import estimate_video


def receiver_agc(source, sdr):
    """Enable supported hardware AGC; unsupported radios keep manual gain."""
    if sdr.lower() == 'hackrf':
        return False  # viewer implements its separate LNA/VGA controller
    try:
        if sdr.lower() in UHD_ALIASES:
            source.set_rx_agc(True, 0)
        else:
            source.set_gain_mode(0, True)
        return True
    except (AttributeError, RuntimeError, ValueError, TypeError):
        return False


def acquire_video(source, rate, contrast=1., dcblock=False, if_offset=0.):
    """Bounded acquisition; re-use the source after detaching this graph."""
    tb = gr.top_block('Analog video acquisition')
    chain = [source]
    if dcblock:
        chain.append(filter.dc_blocker_cc(32, False))
    if if_offset:
        osc = analog.sig_source_c(rate, analog.GR_COS_WAVE, if_offset, 1., 0.)
        mix = blocks.multiply_cc(1)
        tb.connect(osc, (mix, 1))
        chain.append(mix)
    chain.append(analog.quadrature_demod_cf(quad_demod_gain(rate)*contrast))
    decimation = max(1, int(rate/1e6))
    analysis_rate = rate/decimation
    chain.append(filter.fir_filter_fff(decimation, firdes.low_pass(
        1., rate, min(350e3, analysis_rate*.35), min(100e3, analysis_rate*.1), window.WIN_HAMMING)))
    probe = video_probe(analysis_rate)
    chain.append(probe)
    tb.connect(*chain)
    deadline = time.monotonic() + 5
    try:
        tb.start()
        for attempt in range(3):
            # Keep the receiver streaming so tuner/AGC settling is not restarted.
            estimate = probe.capture(timeout=max(.001, deadline-time.monotonic()))
            if estimate is not None:
                return estimate
            if attempt < 2:
                sys.stderr.write('[video] Sync not stable yet; checking fresh samples (%d/3)...\n' %
                                 (attempt+2))
        return None
    finally:
        tb.stop()
        tb.wait()
        tb.disconnect_all()


class adaptive_video(gr.sync_block):
    """Map validated sync thresholds and picture range without chasing noise."""
    def __init__(self, rate, initial):
        gr.sync_block.__init__(self, name='Adaptive analog video levels',
                               in_sig=[np.float32], out_sig=[np.float32])
        self.scale, self.offset = initial.scale, initial.offset
        self.standard = initial.standard
        self.estimate = initial
        self.enabled = True
        self.step = max(1, int(rate/1e6))
        self.rate = rate/self.step
        self.phase = 0
        self.buffer = np.empty(int(self.rate*.20), dtype=np.float32)
        self.fill = 0
        self.until_update = 0
        self.warned_standard = False

    def work(self, inputs, outputs):
        x = inputs[0]
        n = len(x)
        outputs[0][:n] = x*self.scale + self.offset
        if not self.enabled:
            return n
        start = (-self.phase) % self.step
        small = x[start::self.step]
        self.phase = (self.phase+n) % self.step
        if self.until_update > 0:
            self.until_update -= len(small)
            return n
        take = min(len(small), len(self.buffer)-self.fill)
        self.buffer[self.fill:self.fill+take] = small[:take]
        self.fill += take
        if self.fill == len(self.buffer):
            estimate = estimate_video(self.buffer, self.rate)
            self.fill = 0
            self.until_update = int(self.rate*.8)
            if estimate is not None and estimate.standard == self.standard:
                # Do not flip polarity or make a large gain jump mid-field.
                ratio = estimate.scale/self.scale
                if .5 < ratio < 2:
                    self.scale = .8*self.scale + .2*estimate.scale
                    self.offset = .8*self.offset + .2*estimate.offset
                    self.estimate = estimate
            elif estimate is not None and not self.warned_standard:
                sys.stderr.write('[video] Different video standard detected; re-tune to reacquire.\n')
                self.warned_standard = True
        return n


class video_probe(gr.sync_block):
    """Capture only fresh samples on request from an already running graph."""
    def __init__(self, rate):
        import threading
        gr.sync_block.__init__(self, name='Video sync confirmation',
                               in_sig=[np.float32], out_sig=[])
        self.rate = rate
        self.buffer = np.empty(int(rate*.35), dtype=np.float32)
        self.fill = 0
        self.collecting = False
        self.mutex = threading.Lock()
        self.ready = threading.Event()

    def work(self, inputs, outputs):
        x = inputs[0]
        with self.mutex:
            if self.collecting:
                take = min(len(x), len(self.buffer)-self.fill)
                self.buffer[self.fill:self.fill+take] = x[:take]
                self.fill += take
                if self.fill == len(self.buffer):
                    self.collecting = False
                    self.ready.set()
        return len(x)

    def capture(self, timeout=5):
        with self.mutex:
            self.ready.clear()
            self.fill = 0
            self.collecting = True
        if not self.ready.wait(timeout):
            with self.mutex:
                self.collecting = False
            raise RuntimeError('radio stopped delivering samples during video confirmation')
        with self.mutex:
            data = self.buffer.copy()
        return estimate_video(data[int(.08*self.rate):], self.rate)
