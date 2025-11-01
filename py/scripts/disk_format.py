#!/usr/bin/env python3
import subprocess
from scripts.my_log import log
import sys
import os

DEVICE = "/dev/sda"  # Example, replace or pass dynamically
EFI_SIZE = ""  # Example EFI partition size
EFI_PARTITION = None
ROOT_PARTITION = None
ROOT_LABEL = "Arch"
MOUNT_OPTIONS = "noatime,compress=zstd"


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


def fatal(msg):
    print(f"[FAIL] {msg}")
    sys.exit(1)


def check_disk(disk):
    """Check if a partition scheme exists on the given disk, and optionally wipe it."""

    log.info(f"Checking disk: {disk}")

    def run(cmd, check=False):
        return subprocess.run(
            cmd,
            shell=True,
            check=check,
        )

    # Check if a partition table exists
    if run(f"blkid -p {disk}").returncode in (0, 2):
        reply = input(f"Partition scheme exists on {disk}. Wipe it? (y/N) ").strip()
        if reply.lower() == "y":
            # Attempt to unmount partitions
            if run(f"umount -R {disk}*").returncode != 0:
                log.warning("Failed to unmount some partitions")

            log.info(f"Wiping partition table on {disk}...")
            if run(f"sgdisk -Z {disk}").returncode != 0:
                log.warning("Failed to wipe partition table")
            else:
                run(f"partprobe {disk}")
                log.info(f"Partition table wiped on {disk}.")
        else:
            log.warning(f"User chose not to wipe {disk}.")
            return 1
    return 0


def set_partitions(DEVICE, EFI_SIZE):
    """Partition the given DEVICE with EFI and root."""
    log.info(f"Partitioning {DEVICE}...")

    run(f"sgdisk -Z {DEVICE}")
    run(f"sgdisk -a 2048 -o {DEVICE}")

    part_count = 1
    device_name = os.path.basename(DEVICE)
    part_suffix = "p" if "nvme" in device_name else ""

    # EFI partition
    log.info("Creating EFI system partition...")
    run(
        f"sgdisk -n {part_count}:0:+{EFI_SIZE} -t {part_count}:ef00 -c {part_count}:EFIBOOT {DEVICE}"
    )
    EFI_PARTITION = f"{DEVICE}{part_suffix}{part_count}"
    part_count += 1

    # Root partition
    log.info("Creating root partition...")
    run(
        f"sgdisk -n {part_count}:0:0 -t {part_count}:8300 -c {part_count}:ROOT {DEVICE}"
    )
    ROOT_PARTITION = f"{DEVICE}{part_suffix}{part_count}"

    run(f"partprobe {DEVICE}", check=False)
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
        fatal(f"Root partition not found: {ROOT_PARTITION}")
    os.sync()


def mount_install():
    """Mount partitions and create subvolumes."""
    log.info("Mounting partitions...")

    run(f"mount {ROOT_PARTITION} /mnt")
    run("btrfs subvolume create /mnt/@")
    run("btrfs subvolume create /mnt/@home")
    run("umount /mnt")

    run(f"mount -o {MOUNT_OPTIONS},subvol=@ {ROOT_PARTITION} /mnt")
    os.makedirs("/mnt/home", exist_ok=True)
    run(f"mount -o {MOUNT_OPTIONS},subvol=@home {ROOT_PARTITION} /mnt/home")

    os.makedirs("/mnt/boot", exist_ok=True)
    run(f"mount {EFI_PARTITION} /mnt/boot")
    log.info("EFI partition mounted at /mnt/boot")

    log.info("All partitions mounted.")


def format_disk():
    """Main entry point."""
    # if check_disk(DEVICE) == 1:
    #     sys.exit(1)
    set_partitions(DEVICE, EFI_SIZE)
    format_partitions(EFI_PARTITION, ROOT_PARTITION, ROOT_LABEL)
    mount_install()


if __name__ == "__main__":
    format_disk()
