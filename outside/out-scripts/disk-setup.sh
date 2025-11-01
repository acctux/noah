# ----------------------------------------------------------------------
# select_device  --  interactive block-device selector
#   $1 : title shown before the menu
#   $2 : optional type filter ("disk", "part" or empty)
#   $3 : name of the variable that will receive the result
#   Example:
#       select_device "Pick USB" "part" USB_PARTITION
#       select_device "Pick disk" "disk" DEVICE
# ----------------------------------------------------------------------
select_device() {
  local title="$1" filter="${2:-}" result_var="$3"
  local -a candidates=() idx=1
  local line dev

  [[ -z "$result_var" ]] && fatal "select_device: result variable name required."

  while true; do
    candidates=()
    idx=1
    info "$title – scanning…"

    while read -r line; do
      eval "$line" # → $NAME $SIZE $FSTYPE $TYPE $MOUNTPOINT $RM

      # type filter
      [[ -n "$filter" && "$TYPE" != "$filter" ]] && continue
      # skip mounted
      [[ -n "$MOUNTPOINT" ]] && continue

      dev="/dev/$NAME"
      candidates+=("$dev")

      printf "%3d) %-12s  Size:%-8s  FS:%-8s  [%s]\n" \
        "$idx" "$dev" "$SIZE" "$FSTYPE" "${TYPE^}"
      ((idx++))
    done < <(lsblk -P -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINT,RM)

    ((${#candidates[@]})) && break
    warning "No devices found. Insert media and press Enter…"
    read -r
  done

  # ----- user picks -----
  while true; do
    read -rp "Select (1-${#candidates[@]}): " choice
    [[ "$choice" =~ ^[0-9]+$ ]] || {
      warning "Not a number."
      continue
    }
    ((choice >= 1 && choice <= ${#candidates[@]})) || {
      warning "Out of range."
      continue
    }

    local selected="${candidates[$((choice - 1))]}"
    [[ -b "$selected" ]] || {
      error "Not a block device: $selected"
      return 1
    }

    printf -v "$result_var" '%s' "$selected"
    success "Selected: $selected"
    return 0
  done
}

#######################################
# Convert size input with IEC suffix (KiB, MiB, GiB, TiB, PiB) to KiB
# Arguments:
#   $1 - size input string (e.g. "512M", "1G", "256MiB")
# Returns:
#   Echoes converted size in KiB (e.g. "524288k")
#   Returns 0 on success, 1 on error
#######################################
sanitize_size_input() {
  local input="$1"
  local value suffix

  # Remove spaces
  input=$(echo "$input" | tr -d ' ')

  # Extract numeric value and suffix
  value=$(echo "$input" | sed -n 's/^\([0-9.]\+\)[A-Za-z]*$/\1/p')
  suffix=$(echo "$input" | sed -n 's/^[0-9.]\+\([A-Za-z]\+\)$/\1/p')

  # Default suffix to none if missing
  suffix=${suffix:-}

  case "${suffix,,}" in
  pib) value=$(printf "%.0f" "$(echo "$value * 1024 * 1024 * 1024 * 1024" | bc -l)") ;;
  tib) value=$(printf "%.0f" "$(echo "$value * 1024 * 1024 * 1024" | bc -l)") ;;
  gib) value=$(printf "%.0f" "$(echo "$value * 1024 * 1024" | bc -l)") ;;
  mib) value=$(printf "%.0f" "$(echo "$value * 1024" | bc -l)") ;;
  kib) value=$(printf "%.0f" "$value") ;; # Already in KiB
  "")
    # If no suffix, ensure it's an integer number (KiB assumed)
    if ! [[ "$value" =~ ^[0-9]+$ ]]; then
      error "No suffix provided and value is not a valid integer."
      return 1
    fi
    ;;
  *)
    error "Only IEC units allowed (KiB, MiB, GiB, TiB, PiB)."
    return 1
    ;;
  esac

  # Final integer check
  if ! [[ "$value" =~ ^[0-9]+$ ]]; then
    error "Invalid numeric value after conversion."
    return 1
  fi

  echo "${value}k"
}

check_user_efi_size() {
  local sanitized

  # Skip if EFI_SIZE is not set
  if [[ -z "$EFI_SIZE" ]]; then
    return 0
  fi

  # Sanitize the input
  sanitized=$(sanitize_size_input "$EFI_SIZE") || sanitized=""

  # Validate sanitized output format: <number>k
  if [[ "$sanitized" =~ ^[0-9]+k$ ]]; then
    EFI_SIZE="$sanitized"
    success "Using user-defined EFI size: $EFI_SIZE"
    return 0
  else
    error "Invalid EFI_SIZE format: '$EFI_SIZE'. Must be a valid size in KiB, MiB, GiB, TiB, or PiB (e.g., 512MiB, 1GiB)."
    return 1
  fi
}

#######################################
# Prompt user for EFI partition size, sanitize input to KiB
#######################################
ask_efi_size() {
  local sanitized input

  while true; do
    read -rp "Enter EFI partition size (default 512MiB, e.g. 1GiB): " input
    if [[ -z "$input" ]]; then
      EFI_SIZE="524288k" # 512 MiB in KiB
      info "Using default EFI size: 512MiB"
      break
    fi

    sanitized=$(sanitize_size_input "$input")
    if [[ $? -eq 0 && "$sanitized" =~ ^[0-9]+k$ ]]; then
      EFI_SIZE="$sanitized"
      success "EFI size set to: $EFI_SIZE"
      break
    else
      warning "Invalid. Please enter a valid size (e.g., 256MiB, 1GiB)."
    fi
  done
}

setup_disk() {
  if ! check_user_efi_size; then
    ask_efi_size
  fi
  select_device "Select device for installation:" "disk" DEVICE
}
