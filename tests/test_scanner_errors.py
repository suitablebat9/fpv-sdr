#!/usr/bin/env python3
"""Detector failures must never be presented as successful empty scans."""
import pathlib
import shutil
import subprocess

source = pathlib.Path(__file__).resolve().parents[1].joinpath('fpv_scanner.sh').read_text()
functions = source[source.index('scan_channels() {'):source.index('show_spectrum() {')]
setup = '''
check_radio_backend() { return 0; }
release_sdr() { :; }
pkill() { :; }
cleanup() { :; }
mock_python() { return "$MOCK_STATUS"; }
PYTHON=mock_python
SDR=pluto
SCAN_ORDER=(R1)
declare -A CHANNELS=([R1]=5658)
'''
bash = shutil.which('bash')
for command in ('scan_channels', 'sweep_channels', 'scan_loop'):
    for status in (1, 139):
        script = setup + functions + f'\nMOCK_STATUS={status}\n{command}\n'
        result = subprocess.run([bash, '-c', script], text=True, capture_output=True)
        assert result.returncode == status, (command, result)
        assert '[ERROR]' in result.stderr, (command, result)
        assert 'No FPV signals found' not in result.stdout
        assert 'no valid signal' not in result.stdout
result = subprocess.run([bash, '-c', setup + functions + '\nMOCK_STATUS=0\nscan_channels\n'],
                        text=True, capture_output=True)
assert result.returncode == 0 and 'No FPV signals found' in result.stdout, result
print('PASS: scan, sweep and loop preserve detector failures; clean empty scan still succeeds')
