#!/bin/sh

acpi -b | grep "Battery 1" | awk -F'[,:%]' '{print $2, $3}' | {
  read -r status capacity

  if [ "$status" = "Discharging" ] && [ "$capacity" -lt 5 ]; then
    logger "Critical battery threshold"
    systemctl hibernate
  else
    echo "$capacity"
  fi
}
