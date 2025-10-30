mapfile -t system_units < <(
  systemctl --user list-unit-files \
    --type=service,timer,socket \
    --no-legend | awk '{print $1}'
)

unit_exists() {
  local unit="$1"
  for existing in "${system_units[@]}"; do
    if [[ "$unit" == "$existing" ]]; then
      return 0
    fi
  done
  return 1
}

enable_user_services() {
  echo "Enabling user units..."
  for unit in "${USER_SERV_ENABLE[@]}"; do
    if unit_exists "$unit"; then
      systemctl --user enable "$unit"
    else
      echo "Unit $unit not found"
    fi
  done
}
