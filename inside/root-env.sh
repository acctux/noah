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
USER_D="$SCRIPT_D/user"
LOG_FILE="$SCRIPT_D/log"
USER_CONF="$SCRIPT_D/user-config"
SHARED_UTILS="$SCRIPT_D/helper-functions"
TMP_CONF="$SCRIPT_D/tmp_conf"

#######################################
# Sourcing
#######################################
. "$USER_CONF"
. "$SCRIPT_D/helper-functions"
. "$IN_D/sys-settings.sh"
. "$IN_D/ucode-mkinit.sh"
. "$IN_D/bootloaders.sh"
. "$IN_D/hardware.sh"
. "$IN_D/groups-and-user.sh"

if [[ -z "${USER_NAME}" ]]; then
  error "USER_NAME not defined in $USER_CONF."
  exit 1
fi
USER_HOME="/home/$USER_NAME"
. "$TMP_CONF"

#######################################
# Functions
#######################################

install_icons() {
  local usr_icons
  usr_icons="/usr/share/icons"
  ti_dir="/tmp/whitesur-icons"

  git clone https://github.com/vinceliuice/WhiteSur-icon-theme.git "$ti_dir"
  cd "$ti_dir"
  ./install.sh -t grey -d "$usr_icons"
  cd ~
  rm -rf "$ti_dir" "${usr_icons}/WhiteSur-grey-light" "${usr_icons}/capitaine-cursors"
  rm -f "${usr_icons}/WhiteSur-grey/apps/scalable/preferences-system.svg"

  local old_color="#dedede"
  local new_color="#d3dae3"
  local -a files
  mapfile -t files < <(
    fd --type f --extension svg --exclude '*/scalable/*' . "$usr_icons/WhiteSur-grey-dark"
  )
  local -a matches=()
  info "Changing icon colors"

  for f in "${files[@]}"; do
    rg --quiet "$old_color" "$f" && matches+=("$f")
  done
  parallel --jobs 4 "sd '$old_color' '$new_color' {}" ::: "${matches[@]}"
}

#######################################
# Main
#######################################
bigger_boat() {
  pkg_install "${PKG_D}/essentials.txt"
  config_sys_locality

  generate_intramfs

  config_hardware

  create_user
  pkg_install "${PKG_D}/desktop.txt"
  install_icons
  enable_sysd_units SYSD_ENABLE
  disable_services SYSD_DISABLE

  pass_files_to_user
  create_autostart

  # disable root
  passwd -l root
}

bigger_boat

trap 'error_trap ${LINENO} "$BASH_COMMAND"' ERR
