#!/bin/bash

install -d -m 0755 /run/wireguard

ls /etc/wireguard/*.conf 2>/dev/null |
  xargs -n1 basename |
  sed 's/\.conf$//' |
  sort \
    >/run/wireguard/connections.list
