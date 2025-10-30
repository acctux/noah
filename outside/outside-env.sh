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
# Variable
#######################################
SCRIPT_D="$(dirname "$(dirname "${BASH_SOURCE[0]}")")"
OUT_SCRIPTS="$SCRIPT_D/outside/out-scripts"
LOG_FILE="$SCRIPT_D/log"
TMP_CONF="${SCRIPT_D}/tmp_conf"

#######################################
# Variable Sourcing
#######################################
. "$SCRIPT_D/user-config"

#######################################
# Script Sourcing
#######################################
. "$SCRIPT_D/utils"
. "$OUT_SCRIPTS/cp-sensitive.sh"
. "$OUT_SCRIPTS/gather-necessary.sh"
. "$OUT_SCRIPTS/disk-setup.sh"
. "$OUT_SCRIPTS/disk-format.sh"
. "$OUT_SCRIPTS/pass-info.sh"

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
