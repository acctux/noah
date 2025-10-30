#!/usr/bin/env bash

#######################################
# Copy configuration and key files to the target system
# Globals:
#   INSTALL_SCRIPT, KEY_DIR
#######################################
rsync_files_sys() {
  info "Passing configuration files to target system..."

  rsync -a /etc/pacman.d/mirrorlist /mnt/etc/pacman.d/
  rsync -a /etc/pacman.conf /mnt/etc/
  rsync -a "$HOME/${INSTALL_SCRIPT}/" "/mnt/root/${INSTALL_SCRIPT}/"
  rsync -a "$HOME/${KEY_DIR}/" "/mnt/root/${KEY_DIR}/"

  success "Configuration files transferred successfully."
}

#######################################
# Append all globals to sensitive_conf
#######################################
write_secret_conf() {
  if [[ "$BOOTLOADER" == "systemd-boot" ]]; then
    ROOT_UUID=$(blkid -s UUID -o value "$ROOT_PARTITION")
  fi
  cat >"/mnt${TMP_CONF}" <<EOF
SWORDPAS=${SWORDPAS}
CPU_VENDOR=${CPU_VENDOR}
GPU_VENDOR=${GPU_VENDOR}
ISO=${ISO}
ROOT_UUID=${ROOT_UUID}
TMP_CONF="${TMP_CONF}"
EOF
}

pass_files_to_sys() {
  rsync_files_sys
  write_secret_conf
}
