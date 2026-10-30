#!/bin/sh
# Working Pluto Ethernet / NTSC camera settings.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "$(dirname "$0")" || exit 1
export FPV_AGC=off
export FPV_VIEW_EXTRA="--sync-mid -0.015${FPV_VIEW_EXTRA:+ $FPV_VIEW_EXTRA}"
exec /opt/homebrew/bin/bash ./fpv_scanner.sh \
  --sdr pluto --dev-args "uri=ip:pluto.local." \
  --standard ntsc --gain 15 --samp-rate 8e6 "$@"
