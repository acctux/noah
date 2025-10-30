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
# Variables
#######################################
SCRIPT_D="$(dirname "$(dirname "${BASH_SOURCE[0]}")")"
PKG_D="$SCRIPT_D/pkg"
IN_SCRIPTS="$SCRIPT_D/inside/in-scripts"
LOG_FILE="$SCRIPT_D/log"

#######################################
# Variable Sourcing
#######################################
. "$SCRIPT_D/user-config"
. "$SCRIPT_D/tmp_conf"

#######################################
# Script Sourcing
#######################################
. "$SCRIPT_D/utils"
. "$IN_SCRIPTS/sys-settings.sh"
. "$IN_SCRIPTS/ucode-mkinit.sh"
. "$IN_SCRIPTS/bootloaders.sh"
. "$IN_SCRIPTS/hardware.sh"
. "$IN_SCRIPTS/groups-and-user.sh"
. "$IN_SCRIPTS/sys-services.sh"
. "$IN_SCRIPTS/post-reboot-setup.sh"

if [[ -z "${USER_NAME}" ]]; then
  error "USER_NAME not defined in $USER_CONF."
  exit 1
fi
USER_HOME="/home/$USER_NAME"
POST_SCRIPT="$USER_HOME/$INSTALL_SCRIPT/user/user-env.sh"

#######################################
# Main
#######################################
bigger_boat() {
  pkg_install "${PKG_D}/dependencies.list"

  locality_and_pacman

  generate_intramfs
  configure_bootloader

  config_hardware

  user_create

  pkg_list_multiple_install "${PKG_LISTS[@]}"

  handle_system_services

  userfiles_and_autostart

  # disable root
  passwd -l root
}

bigger_boat

trap 'error_trap ${LINENO} "$BASH_COMMAND"' ERR
