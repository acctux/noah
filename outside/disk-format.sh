#######################################
# Check if disk has existing partition table and optionally wipe it
# Arguments:
#   $1 - Disk device name (e.g. sda)
# Returns:
#   0 if OK or wiped, 1 if user aborts
#######################################
check_disk() {
  local disk="$1" reply

  if blkid -p "$disk" &>/dev/null; then
    read -rp "Partition scheme exists on $disk. Wipe it? (y/N) " reply
    if [[ "$reply" =~ ^[Yy]$ ]]; then

      umount -R "$disk"* 2>/dev/null ||
        warning "Failed to unmount some partitions"

      info "Wiping partition table on $disk..."
      sgdisk -Z "$disk" ||
        warning "Failed to wipe partition table"
      partprobe "$disk"
      success "Partition table wiped on $disk."
    else
      warning "User chose not to wipe $disk."
      return 1
    fi
  fi
}

#######################################
# Partition the given DEVICE with EFI and root
# Globals:
#   DEVICE, EFI_SIZE, EFI_PARTITION, ROOT_PARTITION
#######################################
set_partitions() {
  info "Partitioning /dev/${DEVICE}..."

  sgdisk -Z "/dev/${DEVICE}"         # Zap existing partitions
  sgdisk -a 2048 -o "/dev/${DEVICE}" # Set optimal alignment

  local part_count=1

  # Determine partition suffix based on device type
  local part_suffix=""
  if [[ "${DEVICE}" == *nvme* ]]; then
    part_suffix="p"
  fi

  # Create EFI system partition
  info "Creating EFI system partition..."
  sgdisk -n ${part_count}:0:${EFI_SIZE} -t ${part_count}:ef00 -c ${part_count}:EFIBOOT "/dev/${DEVICE}"
  EFI_PARTITION="/dev/${DEVICE}${part_suffix}${part_count}"
  ((part_count++))

  # Create root partition (rest of the space)
  info "Creating root partition..."
  sgdisk -n ${part_count}:0:0 -t ${part_count}:8300 -c ${part_count}:ROOT "/dev/${DEVICE}"
  ROOT_PARTITION="/dev/${DEVICE}${part_suffix}${part_count}"

  partprobe "/dev/${DEVICE}"
  sync
  success "Partitions created: EFI=$EFI_PARTITION, ROOT=$ROOT_PARTITION"
}

#######################################
# Format EFI and root partitions
# Globals:
#   EFI_PARTITION, ROOT_PARTITION, ROOT_LABEL
#######################################
format_partitions() {
  info "Formatting partitions..."

  if [[ -b "$EFI_PARTITION" ]]; then
    mkfs.vfat -F32 -n EFI -i 0077 "$EFI_PARTITION"
    success "EFI partition formatted as FAT32"
  else
    warning "EFI partition not found: $EFI_PARTITION"
  fi

  if [[ -b "$ROOT_PARTITION" ]]; then
    mkfs.btrfs -f -L "$ROOT_LABEL" "$ROOT_PARTITION"
    success "Root partition formatted as Btrfs with label $ROOT_LABEL"
  else
    fatal "Root partition not found: $ROOT_PARTITION"
  fi

  sync
}

#######################################
# Mount partitions for installation and setup subvolumes
# Globals:
#   ROOT_PARTITION, EFI_PARTITION, MOUNT_OPTIONS
#######################################
mount_install() {
  info "Mounting partitions..."

  mount "$ROOT_PARTITION" /mnt
  btrfs subvolume create /mnt/@
  btrfs subvolume create /mnt/@home
  umount /mnt

  # Mount main subvolume
  mount -o ${MOUNT_OPTIONS},subvol=@ "$ROOT_PARTITION" /mnt
  mkdir -p /mnt/home
  mount -o ${MOUNT_OPTIONS},subvol=@home "$ROOT_PARTITION" /mnt/home

  # Mount EFI if available
  if [[ -b "$EFI_PARTITION" ]]; then
    mkdir -p /mnt/boot
    mount "$EFI_PARTITION" /mnt/boot
    success "EFI partition mounted at /mnt/boot"
  fi

  success "All partitions mounted."
}

format_disk() {
  check_disk "$DEVICE"
  set_partitions
  format_partitions
  mount_install
}
