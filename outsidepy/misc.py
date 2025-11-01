#!/usr/bin/env python3
from pyutils.my_log import log
import pyutils.utils as utils
import getpass
import subprocess
import sys
from pathlib import Path

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


#######################################
# Append all globals to sensitive_conf
#######################################
def write_secret_conf(
    bootloader, root_partition, swordpas, cpu_vendor, gpu_vendor, iso
):
    tmp_conf = SCRIPT_DIR / "grandmas_recipes"
    root_uuid = ""
    if bootloader == "systemd-boot":
        try:
            result = subprocess.run(
                ["blkid", "-s", "UUID", "-o", "value", root_partition],
                capture_output=True,
                text=True,
                check=True,
            )
            root_uuid = result.stdout.strip()
        except subprocess.CalledProcessError as e:
            log.error(f"{e}")
            sys.exit(1)

    conf_content = (
        f"SWORDPAS={swordpas}\n"
        f"CPU_VENDOR={cpu_vendor}\n"
        f"GPU_VENDOR={gpu_vendor}\n"
        f"ISO={iso}\n"
        f"ROOT_UUID={root_uuid}\n"
    )

    with open(tmp_conf, "w") as f:
        f.write(conf_content)
    log.info(f"Wrote configuration to {tmp_conf}")


#######################################
# Copy configuration and key files to the target system
#######################################
def rsync_files_sys(install_script, key_dir):
    """Copy configuration and key files to target system (/mnt)."""
    log.info("Passing configuration files to target system...")

    try:
        # Mirrorlist
        subprocess.run(
            ["rsync", "-a", "/etc/pacman.d/mirrorlist", "/mnt/etc/pacman.d/"],
            check=True,
        )
        # Installer script
        subprocess.run(
            [
                "rsync",
                "-ac",
                f"{Path.home()}/{install_script}/",
                f"/mnt/root/{install_script}/",
            ],
            check=True,
        )
        # Key directory
        subprocess.run(
            ["rsync", "-ac", f"{Path.home()}/{key_dir}/", f"/mnt/root/{key_dir}/"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        log.error(f"File sync failed: {e}")
        sys.exit(1)

    log.info("Configuration files transferred successfully.")


def pacstrap_base(packages=[]):
    """Install base packages to the target system."""
    target = "/mnt"

    log.info(f"Installing packages to {target}: {' '.join(packages)}")
    cmd = ["pacstrap", target] + packages
    utils.run_or_fatal(cmd)


def generate_fstab():
    """Generate fstab for the installed system."""
    target = "/mnt"
    log.info("Generating fstab...")
    try:
        with open(f"{target}/etc/fstab", "w") as fstab_file:
            if subprocess.run(
                ["genfstab", "-U", target], check=True, stdout=fstab_file
            ):
                log.info("fstab generated.")
    except subprocess.CalledProcessError:
        log.error("Failed to generate fstab.")
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
