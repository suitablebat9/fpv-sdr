# Testing

Testing is the **same 3 steps on every OS**:

1. `./setup.sh` — installs the stack + builds the bundled decoder. Should finish with no error.
2. `./tests/smoke_test.sh` — should print `0 fail`.
3. Plug in a radio, power a 5.8 GHz VTX, then `./fpv_scanner.sh --sdr hackrf` → type `scan` —
   should find the channel and show video.

Steps 1–2 prove the **software installs and runs** on that OS (no radio needed). Step 3 proves
**real reception** (needs hardware).

## Getting each OS to test on

| OS | Where to run it |
|----|-----------------|
| **macOS** | your Mac (needs Homebrew). |
| **Linux / DragonOS** | a real Linux box, a VM (UTM / Parallels / VirtualBox), or **Docker** (see below). |
| **Windows** | a Windows 11 PC: install WSL2 (`wsl --install -d Ubuntu`), then run the Linux steps **inside** the Ubuntu shell. |

Supported Linux = Debian/Ubuntu family (apt): **Ubuntu 20.04 / 22.04 / 24.04, Debian 12, Kali,
Raspberry Pi OS, Linux Mint, Pop!_OS, DragonOS**. On DragonOS the decoder is prebuilt, so
`./setup.sh` just confirms it. Non-apt distros (Fedora/Arch) aren't automated — `setup.sh` stops
and prints the packages to install by hand, then you re-run.

## Docker — validate the Linux install from your Mac

One job: run **steps 1–2 for Linux** on your Mac, in a throwaway Ubuntu/Debian container, without
building a VM. It does **not** do step 3 (no radio passthrough) and is **Linux only**.

```bash
./tests/docker_test.sh                 # ubuntu 24.04 + 22.04 + debian 12
./tests/docker_test.sh ubuntu:24.04    # just one (faster)
```

Each container runs `./setup.sh` then `./tests/smoke_test.sh` and the matrix prints `PASS`/`FAIL`
per distro. Your repo is mounted read-only, so nothing on the host changes. Needs Docker Desktop
running. First run pulls images + builds GNU Radio, so allow ~10–20 min per distro.

## What the smoke test checks

One command, no flags. Exit `0` = nothing failed, `1` = something failed. `WARN`/`SKIP` never fail
the run (an optional piece is missing, or a check couldn't run here yet — install and re-run).

| Group | Checks |
|-------|--------|
| 1. Bundled decoder | `vendor/gr-ntsc-rc` present, `VENDORED.md` + GPLv3 `LICENSE` present, converter-bounds fix baked into the source, patch kept in `patches/` |
| 2. No moving deps | `setup.sh` builds `vendor/` — no PR fetch, no `git apply`, no upstream clone |
| 3. Shell syntax | `bash -n` every script; `shellcheck` if installed |
| 4. Python | `fpv_env.sh` resolves a GNU Radio Python; `py_compile` every module |
| 5. Imports | `gnuradio.gr`, `numpy`, `PIL`, `gnuradio.NTSC`, `gnuradio.soapy` |
| 6. SDR drivers | SoapySDR factories, UHD tools, `ffplay`; on WSL2, whether an SDR is in `lsusb` |
| 7. App boots/runs | drives `fpv_scanner.sh` headless (`list` then `quit`) — confirms it boots, resolves Python, runs a command (no radio) |

## Step 3 — on-air hardware tests (need a powered VTX)

Same on every OS (inside WSL2 on Windows). Need an analog 5.8 GHz VTX on a known channel and the
right antenna on the RX port.

1. With **no VTX powered**, run `scan` → expect per-channel dBFS/SNR lines and `No FPV signals`,
   and no window opens.
2. Power a VTX on a known channel (e.g. A8 = 5725), run `scan` → expect `[SIGNAL] A8 found …` and
   the viewer opens on that channel. Sync mode checks the listed channel frequency; legacy localization modes can report offsets.
3. With busy 5 GHz Wi-Fi near the antenna and no VTX, run `scan` → expect it rejects the Wi-Fi
   (`No FPV signals`).
4. Run `sweep` → expect a per-channel RSSI/SNR table, no video.
5. Run `spectrum` (or `spectrum A8`) → expect a peak at the VTX center.
6. Run `set A8` (or `freq 5725`) → expect the viewer to tune and open (an `ffplay` window on macOS/brew).

Knobs if a live TX is missed or noise sneaks through: `margin <dB>`, `gain <dB>` (the detector option `--env-cv` only applies to legacy CV confirmation)
(lower if the floor sits near −10…−20 dBFS = clipping). See the main README **Troubleshooting**.

## Automatic analog-video tests

After sourcing `fpv_env.sh` and calling `resolve_fpv_python`, use the resolved
`$PYTHON` to run `tests/test_video_acquisition.py`, `tests/test_video_tracking.py`,
and `tests/test_auto_viewer.py`. These tests use synthesized signals, not hardware.
They cover NTSC/PAL recognition, normal/inverted FM, amplitude and frequency-offset
changes, rejection of noise/silence/tones, ongoing level tracking, format-change
protection, unsupported hardware AGC, and complete FM-to-picture decoding.
`test_horizontal_sync.py`, `test_vertical_sync.py`, and `test_frame_coherence.py`
cover synchronization and intact displayed fields. Live compatibility with multiple
physical cameras and transports remains a separate validation step.

Scanner regressions: `test_scan_selection.py` reproduces a weaker A1 signal behind
stronger non-video candidates, duplicate frequencies, a failed narrow-peak heuristic,
forced video standards, no-hit results and genuine device errors. `test_scan_probe.py`
checks that each channel confirmation captures fresh samples and reports stream stalls.


## Fork regression suite (offline)

Use Bash 4+ (Homebrew Bash on macOS) from the repository root. Rebuild the bundled decoder
first if upgrading from the original: `FPV_REBUILD_DECODER=1 ./setup.sh`.

```bash
source fpv_env.sh
resolve_fpv_python
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
for test in tests/test_*.py; do
    "$PYTHON" "$test" || break
done
bash tests/test_bands.sh
```

`test_scan_flowgraph.py` exercises real GNU Radio confirmation with synthetic FM;
`test_picture_profiles.py` checks the AKK and auto viewer arguments without hardware;
`test_scanner_errors.py` checks detector exit-status handling. Existing PAL decode,
viewer loopback and sync-tuner tests remain part of the suite. These regressions do not establish on-air quality or fresh-install compatibility.
