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
KEY_DIR = ".ssh"
KEY_FILES = ["id_ed25519", "my-private-key.asc", "pass.asc"]
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


def get_unmounted_partitions():
    """Return a list of tuples (name, size, fstype) for partitions that are unmounted."""
    data = get_lsblk_json()  # your function returning lsblk -J JSON
    unmounted = []

    def recurse(devices):
        for dev in devices:
            if dev["type"] == "part" and dev.get("mountpoint") is None:
                unmounted.append(
                    (
                        dev["name"],
                        dev.get("size"),
                        dev.get("fstype"),
                    )
                )
            if "children" in dev:
                recurse(dev["children"])

    recurse(data["blockdevices"])
    return unmounted


def find_usb_partitions(data):
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
            print("Not a number.")
            continue

        choice_num = int(choice)
        if not (1 <= choice_num <= len(candidates)):
            print("Out of range.")
            continue

        selected_partition = candidates[choice_num - 1]
        selected_path = f"/dev/{selected_partition[0]}"
        log.info(f"Selected: {selected_path}")
        return selected_path


def mount_selected(selected_path):
    try:
        subprocess.run(["sudo", "mount", str(selected_path), str(USB_MNT)], check=True)
        log.success(f"Mounted {selected_path} to {USB_MNT}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to mount {selected_path}: {e}")


def copy_missing_keys(KEY_DIR, KEY_FILES, USB_MNT):
    """
    Copy key files from a USB mount to the user's home directory if they don't exist yet.

    Parameters:
        KEY_DIR (str): Subdirectory under home and USB mount where keys are stored.
        KEY_FILES (list of str): List of key filenames to copy.
        USB_MNT (str): Path to the mounted USB.
        info, success, warning (callables): Logging functions.
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
                log.success(f"Copied {key_file} to {dest}")
            except FileNotFoundError:
                log.warning(f"Source file {src} not found on USB.")
            except Exception as e:
                log.warning(f"Failed to copy {key_file} from USB: {e}")
        else:
            log.info(f"{key_file} already exists in {dest_dir}, skipping copy.")


# -------------------- Example Usage -------------------- #
if __name__ == "__main__":
    if not check_usb_files(KEY_DIR, KEY_FILES):
        print(get_unmounted_partitions())
        mount_selected(prompt_user_selection(find_usb_partitions(get_lsblk_json())))
        copy_missing_keys(KEY_DIR, KEY_FILES, USB_MNT)
    else:
        log.success("All required files present.")
