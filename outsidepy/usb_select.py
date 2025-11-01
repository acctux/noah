#!/usr/bin/env python3
import json
import subprocess
import os
import shutil
from pathlib import Path
from scripts.my_log import log

# -------------------- Constants -------------------- #
USB_FS_TYPE = "exfat"
MIN_SIZE = "20G"
USB_MNT = "/mnt/usb"


# -------------------- Utilities -------------------- #
def string_to_float_size(size_str):
    """Convert size strings like '512K' or '20G' to bytes."""
    if not size_str:
        return 0.0

    K = 1024
    M = 1024**2
    G = 1024**3
    T = 1024**4

    size_str = size_str.strip().upper()
    units = {"K": K, "M": M, "G": G, "T": T}
    return float(size_str[:-1]) * units.get(size_str[-1], 1.0)


def check_usb_files(KEY_DIR, KEY_FILES):
    missing_files = []
    if not KEY_FILES:
        return True
    if KEY_DIR and KEY_FILES:
        for key_file in KEY_FILES:
            file_path = os.path.join("/root", KEY_DIR, key_file)
            if not os.path.isfile(file_path):
                missing_files += file_path
                log.info(f"Needed: {file_path}")

    return False  # Files don't exist


# ----------- SELECTION LOGIC ----------
def get_lsblk_json():
    """Run lsblk -J and return parsed JSON."""
    output = subprocess.check_output(
        ["lsblk", "-J", "-o", "NAME,SIZE,FSTYPE,MOUNTPOINT,TYPE"], text=True
    )
    return json.loads(output)


def find_keys_partition(data):
    """Return list of USB_FS_TYPE partitions larger than MIN_SIZE as /dev/<name>."""
    candidates = []

    def recurse(devices):
        for dev in devices:
            if (
                dev["type"] == "part"
                and dev.get("fstype") == USB_FS_TYPE
                and dev.get("mountpoint") is None
            ):
                if string_to_float_size(dev["size"]) > string_to_float_size(MIN_SIZE):
                    fstype = dev.get("fstype")
                    candidates.append(
                        (
                            dev["name"],
                            dev["size"],
                            fstype,
                        )
                    )

            if "children" in dev:
                recurse(dev["children"])

    recurse(data["blockdevices"])
    return candidates


def prompt_user_selection(candidates):
    """Prompt the user to select from a list of candidate devices."""
    while True:
        print(f"{'No.':<5} {'Name':<8} {'Size':<8} {'FS Type':>8}")
        print("-" * 45)

        for i, (
            name,
            size,
            fstype,
        ) in enumerate(candidates, 1):
            print(f"{i:<5} {name:<8} {size:<8} {fstype:>8}")
        choice = input(f"Enter 1-{len(candidates)}: ").strip()

        if not choice.isdigit():
            log.error("Not a number.")
            continue

        choice_num = int(choice)
        if not (1 <= choice_num <= len(candidates)):
            log.error("Out of range.")
            continue

        selected_partition = candidates[choice_num - 1]
        selected_path = f"/dev/{selected_partition[0]}"
        log.info(f"Selected: {selected_path}")
        return selected_path


def mount_selected(selected_path):
    Path(USB_MNT).mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["mount", str(selected_path), str(USB_MNT)], check=True)
        log.info(f"Mounted {selected_path} to {USB_MNT}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to mount {selected_path}: {e}")


def copy_keys(KEY_DIR, KEY_FILES):
    """
    Parameters:
        USB_MNT (str): Path to the mounted USB.
        KEY_DIR (str): Subdirectory under home and USB mount where keys are stored.
        KEY_FILES (list of str): List of key filenames to copy.
    """
    log.info("Preparing to copy key files from USB...")
    dest_dir = Path.home() / KEY_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    for key_file in KEY_FILES:
        src = Path(USB_MNT) / KEY_DIR / key_file
        dest = dest_dir / key_file

        if not dest.exists():
            try:
                shutil.copy2(src, dest)
                log.info(f"Copied {key_file} to {dest}")
            except FileNotFoundError:
                log.warning(f"Source file {src} not found on USB.")
            except Exception as e:
                log.warning(f"Failed to copy {key_file} from USB: {e}")
        else:
            log.info(f"{key_file} already exists in {dest_dir}, skipping copy.")


def unmount_partition():
    try:
        result = subprocess.run(["mountpoint", "-q", USB_MNT], check=False)
        if result.returncode == 0:
            try:
                subprocess.run(["umount", USB_MNT], check=True)
                log.info(f"Unmounted USB from {USB_MNT}.")
            except subprocess.CalledProcessError:
                log.warning(f"Failed to unmount USB from {USB_MNT}.")
    except Exception as e:
        log.warning(f"Error checking mountpoint: {e}")

    if Path(USB_MNT).exists():
        try:
            os.rmdir(USB_MNT)
        except OSError:
            pass


# -------------------- Example Usage -------------------- #
def mnt_cp_keys(KEY_DIR, KEY_FILES):
    if not check_usb_files(KEY_DIR, KEY_FILES):
        mount_selected(prompt_user_selection(find_keys_partition(get_lsblk_json())))
        copy_keys(KEY_DIR, KEY_FILES)
        unmount_partition()
    else:
        log.info("All required files present.")
