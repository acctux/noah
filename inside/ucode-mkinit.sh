install_ucode() {
  if [[ "$CPU_VENDOR" == "amd" ]]; then
    pacman -S --noconfirm amd-ucode
  elif [[ "$CPU_VENDOR" == "intel" ]]; then
    pacman -S --noconfirm intel-ucode
  fi
}

set_mkinitcpio() {
  mkinit_conf=/etc/mkinitcpio.conf

  sed -i 's/^HOOKS=.*/HOOKS=(base systemd autodetect microcode modconf kms sd-vconsole block filesystems)/' \
    "${mkinit_conf}"

  if [[ "$CPU_VENDOR" == "amd" ]]; then
    sed -i 's/^MODULES=.*/MODULES=(amdgpu)/' "${mkinit_conf}"
  elif [[ "$CPU_VENDOR" == "intel" ]]; then
    sed -i 's/^MODULES=.*/MODULES=(i915)/' "${mkinit_conf}"
  fi

  mkinitcpio -P
}
generate_intramfs() {
  install_ucode
  set_mkinitcpio
}
