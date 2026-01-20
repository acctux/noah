#!/usr/bin/env python3
import json
from pathlib import Path
import shutil
import subprocess
from noah_lib.utils import get_logger

log = get_logger("USB Mount and Copy")


def run_cmd(cmd, check=False):
    try:
        log.info(f"Running: {cmd}")
        result = subprocess.run(cmd, text=True, shell=True, check=check)
        return result
    except subprocess.CalledProcessError as e:
        log.error(f"Failed: {cmd}\nExit code: {e.returncode}")
        return e


def check_usb_files(key_dir, key_files):
    missing_files = False
    for key_file in key_files:
        file_path = Path(f"/root/{key_dir}/{key_file}")
        if not file_path.exists():
            missing_files = True
            log.error(f"Needed: {file_path}")
    return missing_files


def check_wireguard_dir():
    wireguard_dir = Path("/root/wireguard")
    if not wireguard_dir.is_dir():
        log.error(f"Needed: {wireguard_dir} is not a directory")
        return True
    if not any(wireguard_dir.iterdir()):
        log.error(f"Needed: {wireguard_dir} is empty")
        return True
    return False


def string_to_float_size(size_str):
    if not size_str:
        return 0.0
    K = 1024
    M = 1024**2
    G = 1024**3
    T = 1024**4
    size_str = size_str.strip().upper()
    units = {"K": K, "M": M, "G": G, "T": T}
    return float(size_str[:-1]) * units.get(size_str[-1], 1.0)


def mnt_keys_partition(usb_mnt: Path, min_size: str, usb_fs_type: str):
    output = subprocess.check_output(
        ["lsblk", "-J", "-o", "NAME,SIZE,FSTYPE,MOUNTPOINT,TYPE"], text=True
    )
    data = json.loads(output)
    candidates = []

    def recurse(devices):
        for dev in devices:
            if (
                dev["type"] == "part"
                and dev.get("fstype") == usb_fs_type
                and dev.get("mountpoint") is None
                and string_to_float_size(dev["size"]) > string_to_float_size(min_size)
            ):
                candidates.append(
                    (
                        dev["name"],
                        dev["size"],
                        dev.get("fstype"),
                    )
                )
            if "children" in dev:
                recurse(dev["children"])

    recurse(data["blockdevices"])
    while True:
        print(f"{'No.':<5} {'Name':<8} {'Size':<8} {'FS Type':>8}")
        print("-" * 45)
        for i, (name, size, fstype) in enumerate(candidates, 1):
            print(f"{i:<5} {name:<8} {size:<8} {fstype:>8}")
        choice = input(f"Enter 1-{len(candidates)}: ").strip()
        if not choice.isdigit():
            log.error("Not a number.")
            continue
        choice_num = int(choice)
        if not (1 <= choice_num <= len(candidates)):
            log.error("Out of range.")
            continue
        selected_path = f"/dev/{candidates[choice_num - 1][0]}"
        break
    usb_mnt.mkdir(parents=True, exist_ok=True)
    try:
        run_cmd([f"mount {selected_path} {usb_mnt}"], check=True)
        return selected_path
    except subprocess.CalledProcessError as e:
        log.error(f"Failed to mount {selected_path}: {e}")


def usb_cp_keys(usb_mount, key_dir, key_files):
    print("Preparing to copy key files from USB...")
    dest_dir = Path.home() / key_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    for key_file in key_files:
        src = Path(usb_mount) / key_dir / key_file
        dest = dest_dir / key_file
        if not dest.exists():
            try:
                shutil.copy2(src, dest)
                log.info(f"Copied {key_file} to {dest}")
            except FileNotFoundError:
                log.error(f"Source file {src} not found on USB.")
        else:
            log.error(f"{key_file} already exists in {dest_dir}, skipping copy.")


def usb_cp_folder(usb_mount, folder_name):
    log.info("Preparing to copy folder from USB...")
    src_dir = Path(usb_mount) / folder_name
    dest_dir = Path.home() / folder_name
    if not dest_dir.exists():
        try:
            shutil.copytree(src_dir, dest_dir)
            log.info(f"Copied folder {folder_name} to {dest_dir}")
        except FileNotFoundError:
            log.error(f"Source folder {src_dir} not found on USB.")
        except Exception as e:
            log.error(f"Failed to copy folder {folder_name} from USB: {e}")


def unmount_partition(usb_mount: Path):
    result = run_cmd(["mountpoint", "-q", f"{usb_mount}"], check=False)
    if result.returncode == 0:
        run_cmd(["umount", f"{usb_mount}"], check=True)
        log.info(f"Unmounted USB from {usb_mount}.")
    if usb_mount.exists():
        try:
            Path(usb_mount).unlink()
        except OSError:
            pass


def mnt_cp_keys(
    min_size: str,
    usb_fs_type: str,
    key_dir: str | None = None,
    key_files: list[str] | None = None,
    wireguard_dir: str | None = None,
    pass_file: str | None = None,
    usb_mnt=Path("/mnt/usb"),
):
    if key_dir and key_files or wireguard_dir or pass_file:
        if check_usb_files(key_dir, key_files):
            mnt_keys_partition(usb_mnt, min_size, usb_fs_type)
            if key_dir and key_files:
                usb_cp_keys(usb_mnt, key_dir, key_files)
            if wireguard_dir:
                usb_cp_folder(usb_mnt, wireguard_dir)
            unmount_partition(usb_mnt)
    else:
        log.info("All required files present.")
