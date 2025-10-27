install_grub() {
  grub-install --target=x86_64-efi \
    --efi-directory=/boot \
    --bootloader-id=GRUB ||
    fatal "GRUB install failed."
  grub-mkconfig -o /boot/grub/grub.cfg
}

install_gummiboot() {
  local arch_conf="/boot/loader/entries/arch.conf"
  local root_uuid
  root_uuid=$(blkid -s UUID -o value "$ROOT_PARTITION") ||
    fatal "Failed to get root UUID."

  bootctl --path=/boot install
  systemctl enable systemd-boot-update

  cat >"/boot/loader/loader.conf" <<EOF
default arch.conf
timeout 1
EOF

  cat >"$arch_conf" <<EOF
title   Arch Linux
linux   /vmlinuz-linux
EOF

  echo "initrd /$CPU_VENDOR-ucode.img" >>"$arch_conf"

  echo "initrd /initramfs-linux.img" >>"$arch_conf"
  echo "options root=UUID=$root_uuid rw rootflags=subvol=@ quiet" >>"$arch_conf"
}

nvidia_blacklist_entry() {
  local arch_conf="/boot/loader/entries/arch.conf"
  local nvidia_conf="/boot/loader/entries/arch-blacklist-nvidia.conf"

  [[ -f "$arch_conf" ]] || fatal "Boot entry $arch_conf does not exist."
  cp "$arch_conf" "$nvidia_conf"
  sed -i '/^options / s/$/ module_blacklist=nvidia,nvidia_drm,nouveau/' "$nvidia_conf"
  info "Created NVIDIA-blacklisted boot entry at $nvidia_conf"
}

#######################################
# Install and configure bootloader (GRUB, systemd-boot, or rEFInd)
# Globals:
#   BOOTLOADER, ROOT_PARTITION, CPU_VENDOR
#######################################
configure_bootloader() {
  info "Configuring bootloader: ${BOOTLOADER}"

  case "$BOOTLOADER" in
  grub)
    install_grub
    ;;

  systemd-boot)
    install_gummiboot
    nvidia_blacklist_entry
    ;;

  refind)
    refind-install || fatal "rEFInd installation failed."
    ;;
  esac

  success "Bootloader ${BOOTLOADER} configured successfully."
}
