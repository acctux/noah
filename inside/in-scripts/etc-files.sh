#######################################
# Configure system settings: fstab, timezone, locale, hostname, keymap
# Globals:
#   TIMEZONE, LOCALE, HOST_NAME
#######################################
sys_locality() {
  info "Configuring system..."

  info "Setting timezone, locale, and hostname..."
  ln -sf "/usr/share/zoneinfo/${TIMEZONE}" /etc/localtime
  hwclock --systohc
  echo "${LOCALE} UTF-8" >>/etc/locale.gen
  locale-gen
  echo "LANG=${LOCALE}" >/etc/locale.conf
  echo "KEYMAP=us" >/etc/vconsole.conf
  echo "${HOST_NAME}" >"/etc/hostname"

  success "System configuration completed successfully."
}

reflector_regdom_conf() {
  info "Writing reflector configuration."

  cat >/etc/xdg/reflector/reflector.conf <<EOF
--country "${ISO}" \
--protocol https \
--completion-percent 100 \
--age 18 \
--fastest 15 \
--sort rate \
--threads 8 \
--download-timeout 4 \
--save /etc/pacman.d/mirrorlist
EOF

  success "Reflector configuration updated successfully"

  local regdom_cfg
  regdom_cfg=/etc/modprobe.d/cfg80211.conf
  echo "options cfg80211 ieee80211_regdom=$ISO" >"$regdom_cfg"
  success "Wireless regulatory domain set to ${ISO}"
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

s_pac_ed() {
  local pac_conf="/etc/pacman.conf"
  sed -i '/^\s*#\s*Color\s*$/s/^#\s*//' $pac_conf
  sed -i '/^\s*Color\s*$/a ILoveCandy' $pac_conf
  sed -i '/^\s*#\s*\[multilib\]/s/^#\s*//' $pac_conf
  sed -i '/^\[multilib\]/,/^$/{ /^\s*#\s*Include\s*=.*/s/^#\s*// }' $pac_conf
  sed -i '/ParallelDownloads/c\ParallelDownloads = 10' $pac_conf
}

enable_sudo_insults() {
  if ! sudo grep -q "^Defaults\s\+insults" /etc/sudoers; then
    info "Enabling sudo insults."
    sudo sh -c \
      'sed -e "/^# Defaults!REBOOT !log_output$/a Defaults insults" /etc/sudoers |
       EDITOR="tee -p" visudo > /dev/null'
  else
    info "Insults already enabled, you masochist."
  fi
}

etc_files_config() {
  sys_locality
  reflector_regdom_conf
  chaotic_repo
  s_pac_ed
  pacman -Sy
  enable_sudo_insults
}
