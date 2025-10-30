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
. "$SHARED_UTILS"
. "$OUT_D/cp-sensitive.sh"
. "$OUT_D/gather-necessary.sh"
. "$OUT_D/disk-setup.sh"
. "$OUT_D/disk-format.sh"
. "$OUT_D/pass-info.sh"

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
TMP_CONF="/tmp/tmp_conf"

#######################################
# Main
#######################################
outside_env() {
  umount -A --recursive /mnt || info "No mount or failed to unmount."

  copy_sensitive_files

  get_necessary_info
  ask_password SWORDPAS
  setup_disk
  format_disk

  update_reflector
  pacstrap /mnt base base-devel btrfs-progs linux linux-firmware
  genfstab -U /mnt >"/mnt/etc/fstab" || fatal "Failed to generate fstab."
  pass_files_to_sys
}
outside_env
trap 'error_trap ${LINENO} "$BASH_COMMAND"' ERR
