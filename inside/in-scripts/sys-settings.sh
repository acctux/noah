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

config_sys_locality() {
  reflector_regdom_conf
  sys_locality
}
