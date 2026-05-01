#!/bin/bash
set -euo pipefail

OUTDIR="/var/cache/mysysinfo"
install -d -m 0755 "$OUTDIR"

find /etc/wireguard -maxdepth 1 -type f -name '*.conf' 2>/dev/null |
  sed 's#.*/##; s/\.conf$//' |
  sort >"$OUTDIR/vpn.list"

if [ ! -f "$OUTDIR/sysinfo.txt" ]; then
  dmidecode -t system | awk '
    /System Information/ {flag=1; next}
    flag {
        if ($0 ~ /^Handle/) exit
        sub(/^[ \t]+/, "")
        print
    }
    ' >"$OUTDIR/sysinfo.txt"
fi
