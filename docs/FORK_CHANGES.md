# Fork changes and operating guide

This fork preserves the history and attribution of [lukeswitz/fpv-sdr](https://github.com/lukeswitz/fpv-sdr).
The first fork update is based on upstream commit `43826de` (`docs: install path organization`).
The changes below were developed for an Apple Silicon Mac and an AD9361-based PlutoSDR
receiver with an AKK analog NTSC camera. They aim to improve compatibility with common
analog cameras; they are not a claim of universal hardware compatibility.

## What was already in the original

The interactive scanner, channel tables, spectrum/RSSI survey, multi-radio abstraction,
manual NTSC/PAL decoding, grayscale display/recording, setup scripts, and vendored decoder
were already present. This fork extends those features. It does not introduce color decoding.
The root MIT license and the vendored decoder's separate GPLv3 license are retained.

## Receiver discovery and macOS reliability

- `fpv_sdr.py` loads the optional UHD backend before GNU Radio blocks on macOS to avoid
  the observed Boost.Asio symbol collision during UHD discovery. Missing optional UHD
  bindings do not prevent using a Soapy receiver.
- When Python's SoapySDR module is missing, discovery falls back to `SoapySDRUtil --find`.
  GNU Radio's C++ Soapy backend can still be usable in that configuration.
- `fpv_env.sh` includes existing modules under `~/.local/pluto/lib/SoapySDR/modules*`
  in `SOAPY_SDR_PLUGIN_PATH`, alongside other installed plugins.
- The scanner checks that its GNU Radio backend imports before launching reception.
  Viewer failures report the real exit status and clear the active-channel display.

The earlier missing `libuhd.4.10.0.dylib` was an installed GNU Radio/UHD version mismatch.
Repairing that installation was a local environment change, not a library bundled in this
repository. Reinstall/rebuild compatible GNU Radio and UHD packages if it recurs; the
import-order fix does not repair missing libraries.

## Automatic analog-video acquisition

New `fpv_video.py` analyzes demodulated sync pulses using NumPy. It estimates NTSC/PAL
from line timing and, when available, field timing, tests normal and inverted polarity,
and estimates a scale/offset for the decoder's grayscale input. It rejects inputs without
reliable periodic sync, including the tested noise, silence and tone cases.

New `fpv_autovideo.py` integrates that estimator with GNU Radio:

- Initial acquisition captures a short sample before opening the viewer.
- Automatic level tracking smooths accepted updates and ignores invalid estimates.
- A changed video standard requires closing and retuning; it is not switched mid-frame.
- Receiver hardware AGC is used when requested and supported; unsupported hardware
  keeps fixed gain. HackRF retains its existing software gain controller.
- A fresh-sample probe supports scan confirmation and reports capture stalls as errors.

The viewer/scanner default standard is now `auto`. Explicit `ntsc` or `pal` remains available.
`--manual-video`, an explicit `--sync-mid`, or `--video-offset` opts out of automatic picture
normalization. Automatic standard detection can still be used with manual picture levels.

## Scanning that checks actual video

The previous default could inspect only three strong candidates, including aliases at the
same frequency, and reject a working camera using envelope variation. The observed example
was a working A1 signal at 5865 MHz hidden behind stronger readings near 5880 MHz.

The new default (`--confirm auto`, equivalent to `sync`) now:

1. Ranks candidates above the RF SNR margin and deduplicates identical frequencies.
2. Checks every remaining candidate until one has valid NTSC/PAL sync.
3. Confirms at the actual channel frequency used by the viewer, rather than moving to a
   nearby stronger peak. It does not impose the narrow-peak or envelope-CV gate in sync mode.
4. Captures fresh samples after retuning and temporarily enables supported receiver AGC
   for confirmation, restoring fixed survey gain afterward.
5. Honors a forced video standard and reports the detected standard and sync confidence.

Legacy `cv`, `ntsc`, and `snr` confirmation modes remain available for diagnostics.
`--confirm ntsc` with automatic standard selection uses the new NTSC/PAL confirmation.
A completed scan with no valid video returns success with no hit; device failures remain
errors. Scan, sweep and loop commands preserve those failures rather than printing a
misleading 'No FPV signals found'. Survey and spectrum operation do not acquire video.
More candidates can mean a longer scan in a crowded band. Adjacent channels can both
contain decodable video; this is not a precision transmitter-center estimator.

## Decoder stability and display delay

Changes in `vendor/gr-ntsc-rc/lib/`:

- Preserve the previous sample across scheduler calls instead of reading `input[-1]`.
- Require a sustained low interval for vertical sync, rejecting short glitches.
- Qualify horizontal sync by pulse width and line age before aligning the next line.
- Separate capture, completed-field and display buffers so an output raster does not
  mix pieces of different incoming fields.
- Keep converter integer decimation at least one.

`fpv_viewer.py` derives the output raster rate from the sample rate and converter decimation.
`fpv_display.py` passes that rate to ffplay and enables frame dropping, avoiding a fixed
30 fps playback rate that could accumulate delay. The output rate can include repeated
fields; it is not the camera's unique image frame rate.

These C++ changes require rebuilding and installing the bundled decoder. Updating Python
files alone is insufficient. An older PAL-capable installation would otherwise be skipped
by setup. To force the current source to be built:

```bash
FPV_REBUILD_DECODER=1 ./setup.sh
```

Setup also checks/installs the project's dependencies. Existing platform requirements still
apply. The force option does not prove that every supported OS has been retested.

## Picture profiles and easy startup

Automatic normalization uses scene levels and can change contrast/noise appearance. Hardware
AGC also changes receiver gain. The AKK camera looked worse after enabling those features,
so the known working settings are available independently of automatic scanning.

| Command | Behavior |
| --- | --- |
| `picture akk` | Fixed receiver gain 15, AGC off, contrast 1.35, manual sync midpoint -0.015 |
| `picture auto` | Automatic picture calibration, receiver AGC on, contrast 1.35; retains the current requested gain as fallback |
| `standard auto` | Detect NTSC/PAL without forcing automatic picture normalization |
| `standard ntsc` / `standard pal` | Force a video standard |

Profiles apply on the next tune, or reopen the last channel when one is selected. They do
not change the radio, transport, sample rate or scan-confirmation policy. Startup accepts
`--picture auto|akk` and `FPV_PICTURE`. CLI options are applied in order; options following a
profile can override its values. `FPV_VIEW_EXTRA` is passed after profile viewer arguments,
so explicit manual level overrides there remain active even after `picture auto`.

For USB with automatic discovery:

```bash
./fpv_scanner.sh --sdr pluto --picture akk
# At the prompt:
# scan
# set A1
# picture auto
```

New macOS launchers:

- `start-pluto.command`: Pluto Ethernet, `uri=ip:pluto.local.`, 8 MS/s, AKK picture profile,
  automatic NTSC/PAL detection and the new scanner.
- `start-pluto-manual.command`: previous fixed NTSC setup, gain 15, AGC off and sync
  midpoint -0.015, retained as a fallback.

They expect Apple Silicon Homebrew Bash at `/opt/homebrew/bin/bash`. Adjust the path for
another installation. Double-click a launcher or run it in Terminal. The user's Desktop
shortcut points to `start-pluto.command`; the Desktop shortcut itself is not part of Git.
For another Ethernet address, pass `--dev-args 'uri=ip:YOUR_ADDRESS'`. For USB, use the
scanner command above rather than the Ethernet launcher. Gain 15 is a camera/setup preset,
not a universal optimum or a comparable gain across all SDR models.

## Validation and limits

On 2026-10-30, all 14 `tests/test_*.py` scripts and `tests/test_bands.sh` passed on
the development Mac using the installed GNU Radio stack and rebuilt decoder. Shell
syntax and Git whitespace checks also passed. No live radio was opened for this validation.

Offline regression coverage is listed in [tests/README.md](../tests/README.md). It includes
synthetic NTSC/PAL and inverted FM, picture-level changes, noise rejection, full FM decode,
horizontal/vertical sync, coherent fields, fresh scan captures, candidate selection, error
reporting and picture-profile arguments. Tests involving GNU Radio require an installed
stack and the rebuilt decoder; they do not open a radio.

The user reported working direct reception and, after the scanning fix, successful scanning.
The latest fixed-picture profile was checked offline; its restored live quality still needs
confirmation. Broad camera/SDR compatibility and Linux/Windows regression runs have not been
established by these local tests.

Remaining limits:

- Grayscale analog NTSC/PAL only; no color, SECAM or digital DJI/Walksnail/HDZero decoding.
- Automatic acquisition is heuristic. Unusual/nonstandard sync and poor reception can fail.
- Auto calibration may produce a worse-looking image for some scenes/cameras; manual
  picture levels remain useful.
- RF bandwidth/sample rate, antenna, center frequency and adequate transport throughput
  remain the operator's responsibility. Automatic video setup does not tune those away.
- The Pluto plugin/driver build installed on the development Mac is not bundled here.
  A clean installation still needs compatible libiio, libad9361-iio and SoapyPlutoSDR.
- Local binaries, build caches, recordings, scan logs and machine-specific Desktop files
  are not distributed in the fork.

## Follow-up: intermittent viewer acquisition

A scan could confirm NTSC and then the newly opened viewer could reject its first short
capture, even though a second attempt worked. Viewer acquisition now keeps one receiver
stream running and checks up to three fresh capture windows, within a five-second capture
budget. This allows additional tuner/AGC settling without restarting the source for each
attempt. It still rejects persistent no-sync input and reports stream stalls as errors.
The log alone does not establish that settling was the cause of the reported failure.
`test_acquisition_startup.py` exercises delayed synthetic NTSC/PAL and persistent no-sync;
physical-camera verification remains outstanding.

If a session reports `hardware AGC` and `auto-video`, it is using automatic picture control.
For the fixed AKK settings on USB, restart the scanner, enter `picture akk`, then `set A1`.
Nearby B8 (5866 MHz) may also decode an A1 (5865 MHz) transmission; the scanner accepts the
first sync-valid channel by RF ranking and does not identify the transmitter's configured
channel label.
