#!/usr/bin/env python3
"""Check viewer arguments for both picture profiles without opening a radio."""
import pathlib
import subprocess
import shutil

root = pathlib.Path(__file__).resolve().parents[1]
source = (root / 'fpv_scanner.sh').read_text().rsplit('\nmain\n', 1)[0]
script = source + '''
check_radio_backend() { return 0; }
release_sdr() { :; }
mock_python() { printf '%s\\n' "$@"; }
PYTHON=mock_python
PROJECT_DIR="$PWD"
SDR=pluto
SAMP_RATE=8e6
VIEW_EXTRA="--rotate 90"
apply_picture_profile akk
set_frequency 5865 A1
printf 'PROFILE_SEPARATOR\\n'
apply_picture_profile auto
set_frequency 5865 A1
'''
r = subprocess.run([shutil.which('bash'), '-c', script], cwd=root,
                   capture_output=True, text=True, check=True)
akk, auto = r.stdout.split('PROFILE_SEPARATOR\n')
for output in (akk, auto):
    assert '--standard\nauto\n' in output, output
    assert '--freq\n5865e6\n' in output, output
    assert '--rotate\n90\n' in output, output
assert '--gain\n15\n' in akk and '--contrast\n1.35\n' in akk
assert '--sync-mid\n-0.015\n' in akk and '--manual-video\n' in akk
assert '--agc\n' not in akk
assert '--sync-mid\n' not in auto and '--manual-video\n' not in auto
assert '--agc\n' in auto
print('PASS: AKK settings restored, auto calibration selectable, format and user overrides preserved')
