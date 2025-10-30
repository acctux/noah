SCRIPT_D="$(dirname "$(dirname "${BASH_SOURCE[0]}")")"

PKG_D="$SCRIPT_D/pkg"
IN_D="$SCRIPT_D/inside"
OUT_D="$SCRIPT_D/outside"
USER_D="$SCRIPT_D/user"
LOG_FILE="$SCRIPT_D/log"
USER_CONF="$SCRIPT_D/user-config"
SHARED_UTILS="$SCRIPT_D/helper-functions"
#######################################
# Sourcing
#######################################
. "$USER_CONF"

key_check() {
  local need_copy=0

  if [[ -n "${KEY_DIR}" && ${#KEY_FILES[@]} -gt 0 ]]; then
    for key_file in "${KEY_FILES[@]}"; do
      local file_path="/root/$KEY_DIR/$key_file"
      if [[ ! -f "$file_path" ]]; then
        info "Key file missing on root: $file_path"
        need_copy=1
        break
      fi
    done
  fi

  if [[ -n "$WIFI_PASS_DIR" ]]; then
    if [[ ! -d "/root/$WIFI_PASS_DIR" ]]; then
      info "WiFi folder missing on root: /root/$WIFI_PASS_DIR"
      need_copy=1
    fi
  fi

  return $need_copy
}

#######################################
# Copy key files from USB to target directory
# Globals:
#   KEY_FILES - array of filenames to copy
#   USB_MNT - mount point of USB
#   KEY_DIR - relative directory on USB where keys reside
#######################################
copy_missing_keys() {
  if [[ -z "$KEY_DIR" || ${#KEY_FILES[@]} -eq 0 ]]; then
    info "No key directory or key files specified. Skipping key copy."
    return
  fi

  info "Preparing to copy key files from USB..."
  mkdir -p "$HOME/$KEY_DIR"

  for key_file in "${KEY_FILES[@]}"; do
    local src="$USB_MNT/$KEY_DIR/$key_file"
    local dest="$HOME/$KEY_DIR/$key_file"

    if [[ ! -f "$dest" ]]; then
      if cp "$src" "$dest"; then
        success "Copied $key_file to $HOME/$KEY_DIR"
      else
        warning "Failed to copy $key_file from USB."
      fi
    else
      info "$key_file already exists in $HOME/$KEY_DIR, skipping copy."
    fi
  done
}

#######################################
# Copy wifi password files from USB
# Globals:
#   USB_MNT - USB mount point
#   WIFI_PASS_DIR - relative directory on USB for wifi passwords
#######################################
copy_wifi_pass() {
  if [[ -z "$WIFI_PASS_DIR" ]]; then
    info "No WiFi password directory specified. Skipping WiFi password copy."
    return
  fi
  local src="$USB_MNT/$WIFI_PASS_DIR"
  local dest="$HOME/WIFI"

  info "Copying WiFi password files from USB..."
  if [[ ! -d "$src" ]]; then
    error "WiFi password directory $src not found on USB."
    return
  fi
  mkdir -p "$dest" || {
    error "Failed to create $dest"
    return
  }
  find "$src" -type f -name '*.nmconnection' -exec cp -p {} "$dest" \;
  success "WiFi password files copied to $dest."
}

#######################################
# Unmount USB partition and cleanup mount point
# Globals:
#   USB_MNT - mount point to unmount and remove
#######################################
unmount_partition() {
  if mountpoint -q "$USB_MNT"; then
    if umount "$USB_MNT"; then
      success "Unmounted USB from $USB_MNT."
    else
      warning "Failed to unmount USB from $USB_MNT."
    fi
  fi

  rmdir "$USB_MNT" 2>/dev/null || true
}

copy_sensitive_files() {
  if ! usb_files_check; then
    info "Missing keys. Proceeding to mount USB and copy."
    select_device "Select keys and WIFI pass partition." "part" USB_PARTITION
    mkdir -p "$USB_MNT"
    if ! mount "$USB_PARTITION" "$USB_MNT"; then
      fatal "Failed to mount $USB_PARTITION at $USB_MNT."
    fi
    copy_missing_keys
    cp_wifi_pass
    unmount_partition
    success "Keys and WiFi passwords copied successfully."
  else
    info "All secret files already imported. Skipping."
  fi
}
