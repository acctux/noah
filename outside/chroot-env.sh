#!/usr/bin/env bash

# --------------------------------------------------------------------------------------
# ███╗   ██╗  ██████╗   █████╗  ██╗  ██╗  ██████╗     █████╗  ██████╗   ██████╗ ██╗  ██╗
# ████╗  ██║ ██╔═══██╗ ██╔══██╗ ██║  ██║ ██╔════╝    ██╔══██╗ ██╔══██╗ ██╔════╝ ██║  ██║
# ██╔██╗ ██║ ██║   ██║ ███████║ ███████║ ╚█████╗     ███████║ ██████╔╝ ██║      ███████║
# ██║╚██╗██║ ██║   ██║ ██╔══██║ ██╔══██║  ╚═══██╗    ██╔══██║ ██╔══██╗ ██║      ██╔══██║
# ██║ ╚████║ ╚██████╔╝ ██║  ██║ ██║  ██║ ██████╔╝    ██║  ██║ ██║  ██║ ╚██████╗ ██║  ██║
# ╚═╝  ╚═══╝  ╚═════╝  ╚═╝  ╚═╝ ╚═╝  ╚═╝ ╚═════╝     ╚═╝  ╚═╝ ╚═╝  ╚═╝  ╚═════╝ ╚═╝  ╚═╝
# --------------------------------------------------------------------------------------
# The one-opinion opinionated automated Arch Linux Installer
# --------------------------------------------------------------------------------------
set -euo pipefail

#######################################
# Sourcing
#######################################
. "$USER_CONF"
. "$SHARED_UTILS"
. "$OUT_D/cp-sensitive.sh"
. "$OUT_D/gather-necessary.sh"
. "$OUT_D/disk-setup.sh"
. "$OUT_D/disk-format.sh"

#######################################
# Declare globals
#######################################
DEVICE=""
CHOICE=""
ROOT_PARTITION=""
ROOT_UUID=""
SWORDPAS=""
CPU_VENDOR=""
GPU_VENDOR=""
ISO=""
USB_MNT="/mnt/usb"
EFI_SIZE="${DEFAULT_EFI_SIZE:-512MiB}"

#######################################
# Copy configuration and key files to the target system
# Globals:
#   INSTALL_SCRIPT, KEY_DIR
#######################################
pass_files_to_sys() {
  info "Passing configuration files to target system..."

  rsync -a /etc/pacman.d/mirrorlist /mnt/etc/pacman.d/
  rsync -a /etc/pacman.conf /mnt/etc/
  rsync -a "$HOME/${INSTALL_SCRIPT}/etc/" /mnt/etc/

  rsync -a "$HOME/${INSTALL_SCRIPT}/" "/mnt/root/${INSTALL_SCRIPT}/"
  rsync -a "$HOME/${KEY_DIR}/" "/mnt/root/${KEY_DIR}/"

  success "Configuration files transferred successfully."
}

#######################################
# Append all globals to sensitive_conf
#######################################
write_secret_conf() {
  tmp_conf="/mnt/tmp/temp_conf"
  if [[ "$BOOTLOADER" == "systemd-boot" ]]; then
    ROOT_UUID=$(blkid -s UUID -o value "$ROOT_PARTITION")
  fi
  cat >"$tmp_conf" <<EOF
SWORDPAS=${SWORDPAS}
CPU_VENDOR=${CPU_VENDOR}
GPU_VENDOR=${GPU_VENDOR}
ISO=${ISO}
ROOT_UUID=${ROOT_UUID}
EOF

  echo "Sensitive globals written to $SECRET_CONF"
}

#######################################
# Main
#######################################
chroot_env() {
  umount -A --recursive /mnt || info "No mount or failed to unmount."

  copy_sensitive_files

  get_necessary_info
  ask_password SWORDPAS
  setup_disk
  format_disk

  update_reflector
  pacstrap /mnt base base-devel linux linux-firmware
  arch-chroot /mnt bash -c "pkg_install '${PKG_D}/essentials.txt'"
  genfstab -U /mnt >"/mnt/etc/fstab" || fatal "Failed to generate fstab."

  pass_files_to_sys
  write_secret_conf
}
chroot_env
trap 'error_trap ${LINENO} "$BASH_COMMAND"' ERR
