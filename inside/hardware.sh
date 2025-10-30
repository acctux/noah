install_gpu_drivers() {
  case "$GPU_VENDOR" in
  amd)
    info "Installing AMD GPU drivers..."
    pacman -S --noconfirm --needed \
      mesa \
      vulkan-radeon
    ;;
  nvidia)
    info "Installing NVIDIA GPU drivers..."
    pacman -S --noconfirm --needed \
      linux-headers \
      dkms \
      nvidia-open-dkms \
      nvidia-utils \
      libglvnd
    ;;
  intel)
    info "Installing Intel GPU drivers..."
    pacman -S --noconfirm --needed \
      mesa \
      vulkan-intel \
      libva-utils \
      libvdpau-va-gl
    ;;
  *)
    pacman -S --noconfirm --needed \
      mesa \
      vulkan-radeon
    ;;
  esac
}

zram_config() {
  pacman -S --noconfirm --needed zram-generator
  tee /etc/systemd/zram-generator.conf >/dev/null <<EOF
[zram0]
zram-size = min(ram / 2, 4096)
compression-algorithm = zstd
EOF

  tee /etc/sysctl.d/99-vm-zram-parameters.conf >/dev/null <<EOF
vm.swappiness = 180
vm.watermark_boost_factor = 0
vm.watermark_scale_factor = 125
vm.page-cluster = 0
EOF
}

config_hardware() {
  install_gpu_drivers
  zram_config
}
