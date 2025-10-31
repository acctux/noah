ensure_variables_nonzero() {
  local required_vars=(
    INSTALL_SCRIPT
    TIMEZONE
    HOST_NAME
    USER_NAME
    LOCALE
    BOOTLOADER
    ROOT_LABEL
    KEYMAP
    MOUNT_OPTIONS
  )

  local missing=()
  for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
      missing+=("$var")
    fi
  done

  if ((${#missing[@]})); then
    error "Following variables required:"
    printf '  %s\n' "${missing[@]}"
    exit 1
  fi

  info "All required variables are set."
}

#######################################
# Detect country ISO
#######################################
get_country_iso() {
  ISO=$(curl -4 -s ifconfig.co/country-iso || true)
  ISO=${ISO:-${LOCALE#*_}}
  echo "Detected ISO: $ISO"
}

#######################################
# Detect CPU vendor
#######################################
detect_cpu() {
  if grep -q "GenuineIntel" /proc/cpuinfo; then
    CPU_VENDOR="intel"
  elif grep -q "AuthenticAMD" /proc/cpuinfo; then
    CPU_VENDOR="amd"
  else
    CPU_VENDOR="intel"
  fi
  echo "Detected CPU: $CPU_VENDOR"
}

#######################################
# Detect GPU vendor
#######################################
detect_gpu() {
  local gpu_info
  gpu_info=$(lspci || true)

  if grep -E "Radeon|AMD" <<<"$gpu_info" && grep -q 'VGA' <<<"$gpu_info"; then
    GPU_VENDOR="amd"
  elif grep -E "NVIDIA|GeForce" <<<"$gpu_info"; then
    GPU_VENDOR="nvidia"
  elif grep -E "Intel.*(Tiger Lake|Alder Lake|Iris Xe|UHD)" <<<"$gpu_info"; then
    GPU_VENDOR="intel"
  fi
  echo "Detected GPU: $GPU_VENDOR"
}

get_necessary_info() {
  ensure_variables_nonzero
  detect_cpu
  detect_gpu
  get_country_iso
}
