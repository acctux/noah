#######################################
# Check if Systemd Unit Exists
# Description:
#   Verifies if a systemd unit exists.
# Arguments:
#   $1 = unit name
#   $2 = mode ("--user" or empty)
# Returns:
#   0 if exists, 1 otherwise
#######################################
sysd_unit_exists() {
  local unit="$1"
  for existing in "${system_units[@]}"; do
    if [[ "$unit" == "$existing" ]]; then
      return 0
    fi
  done
  return 1
}

#######################################
# Enable Systemd Units
# Description:
#   Enables an array of systemd units.
# Arguments:
#   $1 = name of array containing unit names
#   $2 = optional mode ("--user")
#######################################
enable_sysd_units() {
  local array_name="$1"
  local units
  eval "units=(\"\${${array_name}[@]}\")"

  for unit in "${units[@]}"; do
    if sysd_unit_exists "$unit"; then
      info "Enabling $unit"
      systemctl enable "$unit"
    else
      error "Unit $unit not found."
    fi
  done
}

#######################################
# Disable Systemd Units
# Description:
#   Disables an array of systemd units.
# Arguments:
#   $1 = name of array containing unit names
#   $2 = optional mode ("--user")
#######################################
disable_sysd_units() {
  local array_name="$1"
  local units
  eval "units=(\"\${${array_name}[@]}\")"

  for unit in "${units[@]}"; do
    if sysd_unit_exists "$unit"; then
      info "Disabling $unit"
      systemctl disable "$unit"
    else
      error "Unit $unit not found."
    fi
  done
}

handle_system_services() {
  mapfile -t system_units < <(
    systemctl list-unit-files --type=service,timer,socket --no-legend |
      awk '{print $1}'
  )
  enable_sysd_units SYSD_ENABLE
  disable_sysd_units SYSD_DISABLE
}
