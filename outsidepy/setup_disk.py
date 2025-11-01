#!/usr/bin/env python3
import json
import subprocess
from pyutils.my_log import log
import re


def umount_recursive():
    """
    Recursively unmount all mount points under /mnt.
    Completely ignores errors and never exits non-zero.
    """
    target = "/mnt"
    subprocess.run(
        ["umount", "-A", "--recursive", target], text=True, capture_output=True
    )
    log.info(f"Tried to unmount recursively: {target} (errors ignored)")


def sanitize_size_input(input_str):
    """
    Convert a size string using first-letter (K, M, G, T, P) to megabytes for sgdisk.
    Defaults to M if no unit is provided.

    Examples:
        '512M' -> '512M'
        '20G'  -> '20480M'
        '100'  -> '100M'  # defaults to M
    """
    input_str = input_str.replace(" ", "")

    match = re.match(r"^([0-9.]+)([KkMmGgTtPp]?)$", input_str)
    if not match:
        raise ValueError(f"Invalid size format: {input_str}")

    value, suffix = match.groups()
    value = float(value)
    suffix = suffix.lower() if suffix else "m"  # default to M

    if suffix == "p":
        value *= 1024**3  # P -> M
    elif suffix == "t":
        value *= 1024**2  # T -> M
    elif suffix == "g":
        value *= 1024  # G -> M
    elif suffix == "m":
        pass  # already in M
    elif suffix == "k":
        value /= 1024  # K -> M
    else:
        raise ValueError("Unknown unit. Use K, M, G, T, or P.")

    final_value = int(round(value))
    return f"{final_value}M"


def ask_efi_size(default_efi_size):
    """
    Prompt the user for EFI partition size and sanitize input.
    Returns the size in KiB as a string (e.g., '524288k').
    """
    try:
        sanitized = sanitize_size_input(default_efi_size)
        return sanitized

    except Exception:
        while True:
            input_str = input(
                "Enter EFI partition size (e.g., 1GiB, 512MB, 524288k): "
            ).strip()
            try:
                sanitized = sanitize_size_input(input_str)
                log.info(f"EFI size set to: {sanitized}")
                return sanitized
            except ValueError as e:
                print(f"{e}. Please try again.")


# ----------- SELECTION LOGIC ----------
def get_lsblk_json():
    """Run lsblk -J and return parsed JSON."""
    output = subprocess.check_output(
        ["lsblk", "-J", "-o", "NAME,SIZE,FSTYPE,MOUNTPOINT,TYPE"], text=True
    )
    return json.loads(output)


def find_install_partition(data):
    """Return list of top-level disks where children match allowed FS types & MIN_SIZE."""
    candidates = []
    # Only iterate top-level blockdevices
    for dev in data["blockdevices"]:
        if dev["type"] == "disk":
            candidates.append((dev["name"], dev["size"]))

    return candidates


def prompt_user_selection(candidates):
    """Prompt the user to select from a list of candidate devices."""
    while True:
        print(f"{'No.':<5} {'Name':<8} {'Size':<8}")
        print("-" * 45)

        for i, (
            name,
            size,
        ) in enumerate(candidates, 1):
            print(f"{i:<5} {name:<8} {size:<8}")
        choice = input(f"Enter 1-{len(candidates)}: ").strip()

        if not choice.isdigit():
            log.error("Not a number.")
            continue

        choice_num = int(choice)
        if not (1 <= choice_num <= len(candidates)):
            log.error("Out of range.")
            continue

        selected_partition = candidates[choice_num - 1]
        selected_name = selected_partition[0]
        part_suffix = "p" if "nvme" in selected_name else ""
        DEVICE = f"{selected_name}{part_suffix}"
        return DEVICE
