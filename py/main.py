#!/usr/bin/env python3
import scripts.setup_disk as sd
import scripts.disk_format as df
import scripts.gather_necessary as gn
import scripts.utils as utils
from scripts.my_log import log
import getpass
import subprocess
import sys

# -------------------- Constants -------------------- #
FS_TYPES = ["ext4", "btrfs"]
MIN_SIZE = "20G"
EFI_DEFAULT = "512M"
ROOT_LABEL = "Arch"
MOUNT_OPTIONS = "noatime,compress=zstd"


def run_or_fatal(cmd, error_msg):
    """Run a shell command and exit on failure."""
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print(error_msg, file=sys.stderr)
        sys.exit(1)


def pacstrap_base(packages=[]):
    """Install base packages to the target system."""
    target = "/mnt"

    print(f"Installing packages to {target}: {' '.join(packages)}")
    cmd = ["pacstrap", target] + packages
    run_or_fatal(cmd, "Failed to install packages.")


def generate_fstab():
    """Generate fstab for the installed system."""
    target = "/mnt"
    print("Generating fstab...")
    try:
        with open(f"{target}/etc/fstab", "w") as fstab_file:
            subprocess.run(["genfstab", "-U", target], check=True, stdout=fstab_file)
    except subprocess.CalledProcessError:
        print("Failed to generate fstab.", file=sys.stderr)
        sys.exit(1)


def ask_password():
    """Prompt the user to enter and confirm a password."""
    while True:
        pass1 = getpass.getpass("Type password: ")
        pass2 = getpass.getpass("Retype password: ")
        if pass1 == pass2:
            return pass1
        else:
            print("Passwords do not match. Please try again.")


def main():
    """
    Entry point for running disk setup interaction.
    """
    device_path = ""
    DEVICE = ""
    EFI_SIZE = ""
    print("=== Disk Setup Utility ===")
    COUNTRY_ISO = gn.get_country_iso()
    CPU_VENDOR = gn.detect_cpu()
    GPU_VENDOR = gn.detect_gpu()
    log.info(f"Detected: {COUNTRY_ISO} {GPU_VENDOR} {CPU_VENDOR}")
    user_password = ask_password()
    log.info(f"Your pass: {user_password}")
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
    pacstrap_base(packages=pacstrap_pkgs)
    generate_fstab()


if __name__ == "__main__":
    main()
