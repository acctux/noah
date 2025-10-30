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
SECRET_CONF="/root/secret_conf"

. "$SECRET_CONF"
. "$USER_CONF"
. "$CURRENT_D/shared-utils"
. "$IN_D/sys-settings.sh"
. "$IN_D/ucode-mkinit.sh"
. "$IN_D/bootloaders.sh"
. "$IN_D/disk-setup.sh"

if [[ -z "${USER_NAME}" ]]; then
  show_error "USER_NAME not defined in $USER_CONF."
  exit 1
fi
USER_HOME="/home/$USER_NAME"

#######################################
# Functions
#######################################
#######################################
# Create User and Assign Groups
# Description: Creates groups if missing, then creates new user
# Globals: USER_NAME, SWORDPAS
# Arguments: $@ = list of groups to add the user to
#######################################
create_user() {
  for group in "${USER_GROUPS[@]}"; do
    if ! getent group "$group" >/dev/null; then
      info "Creating missing group: ${group}"
      groupadd "$group"
    fi
  done

  info "Creating user ${USER_NAME}."

  useradd -m -s /bin/zsh -G "$(
    IFS=,
    echo "${USER_GROUPS[*]}"
  )" "${USER_NAME}"

  echo "${USER_NAME}:${SWORDPAS}" | chpasswd

  cat >"/etc/sudoers.d/${USER_NAME}" <<EOF
${USER_NAME} ALL=(ALL:ALL) ALL
Defaults timestamp_timeout=-1
Defaults passwd_tries=10
Defaults env_keep += "EDITOR VISUAL SYSTEMD_EDITOR"
EOF

  chmod 440 "/etc/sudoers.d/${USER_NAME}"
  success "User ${USER_NAME} created and added to groups: ${USER_GROUPS[*]}"
}

chaotic_repo() {
  chaotic_key_id="3056513887B78AEB"
  key_serv="keyserver.ubuntu.com"

  pacman-key --init
  pacman-key --recv-key "$chaotic_key_id" --keyserver $key_serv
  pacman-key --lsign-key "$chaotic_key_id"

  pacman -U --noconfirm --needed \
    https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst
  pacman -U --noconfirm --needed \
    https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst

  sudo tee -a /etc/pacman.conf >/dev/null <<'EOF'

[chaotic-aur]
Include = /etc/pacman.d/chaotic-mirrorlist
EOF
}

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

pass_files_to_user() {
  rsync -a "$HOME/$INSTALL_SCRIPT/" "$USER_HOME/$INSTALL_SCRIPT/"
  rsync -a "$HOME/$KEY_DIR/" "$USER_HOME/$KEY_DIR/"

  chmod 600 "$USER_HOME/$KEY_DIR/$SSH_KEYFILE"
  chmod 600 "$USER_HOME/$KEY_DIR/$GPG_KEYFILE"
  chown -R "$USER_NAME:$USER_NAME" "$USER_HOME/$INSTALL_SCRIPT" "$USER_HOME/$KEY_DIR"
}

create_autostart() {
  local autostart_dir="$USER_HOME/.config/autostart"
  local desktop_file="$autostart_dir/post.desktop"
  local post_script="$USER_HOME/$INSTALL_SCRIPT/no_moah"
  local exec_command="alacritty -e \"$post_script\""

  mkdir -p "$autostart_dir"
  chmod +x "$post_script"

  cat >"$desktop_file" <<EOF
[Desktop Entry]
Type=Application
Name=Final touches
Exec=sh -c 'sleep 5 && $exec_command'
Terminal=false
NoDisplay=true
EOF

  success "Created: $desktop_file"
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
  chaotic_repo
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
