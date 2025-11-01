#!/usr/bin/env python3
import subprocess
from pyutils.my_log import log
import sys
import os

DEVICE = ""  # Example, replace or pass dynamically
EFI_SIZE = ""
SUBVOLUME_NAMES = ["home", "pacman", "log"]

ROOT_PARTITION = ""
EFI_PARTITION = ""


def run(cmd, check=True):
    """Run a shell command with error handling."""
    try:
        subprocess.run(
            cmd, shell=True, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return True
    except subprocess.CalledProcessError as e:
        log.warning(f"Command failed: {cmd}\n{e.stderr.decode().strip()}")
        return False


def check_disk(device_path):
    """Check if a partition scheme exists on the given disk, and optionally wipe it."""

    log.info(f"Checking disk: {device_path}")

    def run(cmd, check=False):
        return subprocess.run(
            cmd,
            shell=True,
            check=check,
        )

    # Check if a partition table exists
    if run(f"blkid -p {device_path}").returncode in (0, 2):
        reply = input(
            f"Partition scheme exists on {device_path}. Wipe it? (y/N) "
        ).strip()
        if reply.lower() == "y":
            # Attempt to unmount partitions
            if run(f"umount -R {device_path}*").returncode != 0:
                log.warning("Failed to unmount some partitions")

            log.info(f"Wiping partition table on {device_path}...")
            if run(f"sgdisk -Z {device_path}").returncode != 0:
                log.warning("Failed to wipe partition table")
            else:
                run(f"partprobe {device_path}")
                log.info(f"Partition table wiped on {device_path}.")
        else:
            log.warning(f"User chose not to wipe {device_path}.")
            return 1
    return 0


def set_partitions(device_path, EFI_SIZE):
    """Partition the given DEVICE with EFI and root."""
    log.info(f"Partitioning {device_path}...")

    run(f"sgdisk -Z {device_path}")
    run(f"sgdisk -a 2048 -o {device_path}")

    part_count = 1

    # EFI partition
    log.info("Creating EFI system partition...")
    run(
        f"sgdisk -n {part_count}:0:+{EFI_SIZE} -t {part_count}:ef00 -c {part_count}:EFIBOOT {device_path}"
    )
    EFI_PARTITION = f"{device_path}{part_count}"
    part_count += 1

    # Root partition
    log.info("Creating root partition...")
    run(
        f"sgdisk -n {part_count}:0:0 -t {part_count}:8300 -c {part_count}:ROOT {device_path}"
    )
    ROOT_PARTITION = f"{device_path}{part_count}"

    run(f"partprobe {device_path}", check=False)
    os.sync()
    log.info(f"Partitions created: EFI={EFI_PARTITION}, ROOT={ROOT_PARTITION}")
    return EFI_PARTITION, ROOT_PARTITION


def format_partitions(EFI_PARTITION, ROOT_PARTITION, ROOT_LABEL):
    """Format EFI and root partitions."""
    log.info("Formatting partitions...")

    if run(f"mkfs.vfat -F32 -n EFI -i 0077 {EFI_PARTITION}"):
        log.info("EFI partition formatted as FAT32")
    else:
        log.warning(f"EFI partitioning failed not found: {EFI_PARTITION}")

    if run(f"mkfs.btrfs -f -L {ROOT_LABEL} {ROOT_PARTITION}"):
        log.info(f"Root partition formatted as Btrfs with label {ROOT_LABEL}")
    else:
        log.error(f"Root partition not found: {ROOT_PARTITION}")
        sys.exit(1)
    os.sync()


# -------------- INSTALL MOUNT -------------------
def create_subvolumes(SUBVOLUME_NAMES, ROOT_PARTITION):
    run(f"mount {ROOT_PARTITION} /mnt")
    log.info("Creating subvolumes under /mnt...")
    run("btrfs subvolume create /mnt/@")
    for vol in SUBVOLUME_NAMES:
        subvol_name = f"@{vol}"
        log.info(f"Creating subvolume {subvol_name}")
        run(f"btrfs subvolume create /mnt/{subvol_name}")


def mount_volumes(EFI_PARTITION, ROOT_PARTITION, SUBVOLUME_NAMES, MOUNT_OPTIONS):
    efi_mount_point = "/mnt/boot"
    log.info("Mounting subvolumes.")
    run(f"mount -o {MOUNT_OPTIONS},subvol=@ {ROOT_PARTITION} /mnt")

    for vol in SUBVOLUME_NAMES:
        log.info(f"Mounting subvolume {vol}")
        os.makedirs(f"/mnt/{vol}", exist_ok=True)
        run(f"mount -o {MOUNT_OPTIONS},subvol=@home {ROOT_PARTITION} /mnt/{vol}")

    log.info(f"Mounting EFI partition at:{efi_mount_point}")
    os.makedirs(f"{efi_mount_point}", exist_ok=True)
    run(f"mount {EFI_PARTITION} {efi_mount_point}")


def mount_install(EFI_PARTITION, ROOT_PARTITION, MOUNT_OPTIONS):
    """Mount partitions and create subvolumes."""
    create_subvolumes(SUBVOLUME_NAMES, ROOT_PARTITION)
    run("umount /mnt")
    mount_volumes(EFI_PARTITION, ROOT_PARTITION, SUBVOLUME_NAMES, MOUNT_OPTIONS)

    log.info("All partitions mounted.")


# def format_disk():
#     """Main entry point."""
#     if check_disk(DEVICE) == 1:
#         sys.exit(1)
#     set_partitions(DEVICE, EFI_SIZE)
#     format_partitions(EFI_PARTITION, ROOT_PARTITION, ROOT_LABEL)
#     mount_install()
