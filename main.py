#!/usr/bin/env python3
import outsidepy.usb_select as usb
import outsidepy.setup_disk as sd
import outsidepy.disk_format as df
import outsidepy.gather_necessary as gn
import outsidepy.misc as misc
import pyutils.utils as utils
from pyutils.my_log import log
from pathlib import Path

import insidepy.scripts.pacman as pac

# -------------------- CONFIG -------------------- #
FS_TYPES = ["ext4", "btrfs"]
MIN_SIZE = "20G"
EFI_DEFAULT = "512M"
ROOT_LABEL = "Arch"
MOUNT_OPTIONS = "noatime,compress=zstd"
BOOTLOADER = "systemd-boot"
INSTALL_SCRIPT = "noah"
KEY_DIR = ".ssh"
KEY_FILES = ["id_ed25519", "my-private-key.asc", "pass.asc"]
SCRIPT_DIR = Path(__file__).resolve().parent
PKG_D = SCRIPT_DIR / "pkg"

SCRIPT_DIR = Path(__file__).resolve()
PKG_D = Path(SCRIPT_DIR / "pkg")
PKG_LISTS = ["business", "chaotic", "cli-tools", "coding", "dependencies"]


def outside_env():
    """
    Entry point for running disk setup interaction.
    """
    device_path = ""
    DEVICE = ""
    EFI_SIZE = ""
    print("=== Disk Setup Utility ===")

    COUNTRY_ISO, CPU_VENDOR, GPU_VENDOR = gn.get_necessary()
    log.info(f"Detected: {COUNTRY_ISO} {GPU_VENDOR} {CPU_VENDOR}")

    user_password = misc.ask_password()
    log.info(f"Your pass: {user_password}")
    usb.mnt_cp_keys(KEY_DIR, KEY_FILES)
    sd.umount_recursive()

    try:
        EFI_SIZE = sd.ask_efi_size(EFI_DEFAULT)
        DEVICE = sd.prompt_user_selection(
            sd.find_install_partition(sd.get_lsblk_json())
        )
        device_path = f"/dev/{DEVICE}"
        log.info(f"{DEVICE} {EFI_SIZE} {device_path}")
    except KeyboardInterrupt:
        print("\nAborted by user.")
    except Exception as e:
        print(f"Error: {e}")

    df.check_disk(device_path)
    EFI_PARTITION, ROOT_PARTITION = df.set_partitions(device_path, EFI_SIZE)
    df.format_partitions(EFI_PARTITION, ROOT_PARTITION, ROOT_LABEL)
    df.mount_install(EFI_PARTITION, ROOT_PARTITION, MOUNT_OPTIONS)

    utils.update_reflector(COUNTRY_ISO)
    pacstrap_pkgs = ["base", "base-devel", "btrfs-progs", "linux", "linux-firmware"]
    misc.pacstrap_base(packages=pacstrap_pkgs)

    misc.generate_fstab()

    misc.write_secret_conf(
        BOOTLOADER,
        ROOT_PARTITION,
        user_password,
        CPU_VENDOR,
        GPU_VENDOR,
        COUNTRY_ISO,
    )
    misc.rsync_files_sys(INSTALL_SCRIPT, KEY_DIR)


def inside_env():
    pac.install_pkg_list("dependencies", PKG_D)


def main():
    outside_env()
    # inside_env()


main()
