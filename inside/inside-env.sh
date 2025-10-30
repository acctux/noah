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
IN_SCRIPTS="$SCRIPT_D/inside/in-scripts"
LOG_FILE="$SCRIPT_D/log"
USER_CONF="$SCRIPT_D/user-config"
SHARED_UTILS="$SCRIPT_D/helper-functions"
TMP_CONF="$SCRIPT_D/tmp_conf"

#######################################
# Sourcing
#######################################
. "$USER_CONF"
. "$SCRIPT_D/helper-functions"
. "$IN_SCRIPTS/sys-settings.sh"
. "$IN_SCRIPTS/ucode-mkinit.sh"
. "$IN_SCRIPTS/bootloaders.sh"
. "$IN_SCRIPTS/hardware.sh"
. "$IN_SCRIPTS/groups-and-user.sh"
. "$IN_SCRIPTS/pacman-setup.sh"
. "$IN_SCRIPTS/unbound-setup.sh"
. "$IN_SCRIPTS/post-reboot-setup.sh"

if [[ -z "${USER_NAME}" ]]; then
  error "USER_NAME not defined in $USER_CONF."
  exit 1
fi
USER_HOME="/home/$USER_NAME"
. "$TMP_CONF"

#######################################
# Main
#######################################
bigger_boat() {
  # pkg_install "${PKG_D}/essentials.txt"
  # config_sys_locality
  #
  # generate_intramfs
  #
  # config_hardware
  #
  # create_user
  # pacman_setup
  # pkg_install "${PKG_D}/desktop.txt"
  setup_unbound
  enable_sysd_units SYSD_ENABLE
  disable_sysd_units SYSD_DISABLE

  pass_files_to_user
  create_autostart

  # disable root
  passwd -l root
}

bigger_boat

trap 'error_trap ${LINENO} "$BASH_COMMAND"' ERR
