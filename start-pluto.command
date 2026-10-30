#!/bin/sh
# AKK picture levels with automatic scanning and NTSC/PAL detection.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "$(dirname "$0")" || exit 1
exec /opt/homebrew/bin/bash ./fpv_scanner.sh \
  --sdr pluto --dev-args "uri=ip:pluto.local." \
  --picture akk --standard auto --gain 15 --samp-rate 8e6 "$@"
