###################################
# USB Files
###################################
import time
from utils import (
    UsbFileCopy,
    UsbDirCopy,
    run_dmc,
    yes_no,
    get_logger,
    copy_file,
    copy_dir,
)
import subprocess
import json
from pathlib import Path

log = get_logger("Noah")


def get_device(min_gb: int = 20, usb_fs_type: str = "ext4") -> str:
    def recurse(devices):
        for dev in devices:
            if (
                dev["type"] == "part"
                and dev.get("fstype") == usb_fs_type
                and dev.get("mountpoint") is None
                and float(dev["size"][:-1]) > min_gb
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

    data = json.loads(
        subprocess.check_output(
            ["lsblk", "-J", "-o", "NAME,SIZE,FSTYPE,MOUNTPOINT,TYPE"]
        )
    )
    candidates = []
    recurse(data["blockdevices"])
    while True:
        print(
            f"\033[91m{'No.':<5}\033[0m "
            f"\033[93m{'Name':<10}\033[0m "
            f"\033[94m{'Size':<10}\033[0m "
            f"\033[96m{'FS Type':>10}\033[0m"
        )
        print("-" * 45)
        for i, (name, size, fstype) in enumerate(candidates, 1):
            print(
                f"\033[91m{i:<5}\033[0m "
                f"\033[93m{name:<10}\033[0m "
                f"\033[94m{size:<10}\033[0m "
                f"\033[96m{fstype:>10}\033[0m"
            )
        choice = input(f"\033[92mEnter 1-{len(candidates)}: \033[0m").strip()
        if not choice.isdigit() or not (1 <= int(choice) <= len(candidates)):
            log.error("Enter valid number.")
            continue
        selected_path = f"/dev/{candidates[int(choice) - 1][0]}"
        break
    return selected_path


def collect_missing_paths(
    file_cp_list: list[UsbFileCopy], dir_cp_list: list[UsbDirCopy]
) -> tuple[list[tuple[Path, Path]], list[tuple[Path, Path]]]:
    missing_keys: list[tuple[Path, Path]] = []
    missing_dirs: list[tuple[Path, Path]] = []
    root_home = Path("/root")
    for group in file_cp_list:
        source_d = group.source_dir
        for target in group.target_dirs:
            for name in target.file_names:
                dest_path = root_home / target.dest / name
                if not dest_path.exists():
                    missing_keys.append((Path(source_d) / name, dest_path))
    for group in dir_cp_list:
        for name in group.dir_names:
            dest_dir = root_home / name
            if not dest_dir.is_dir():
                missing_dirs.append((Path(group.source_dir) / name, dest_dir))
    return missing_keys, missing_dirs


def copy_usb_to_root(usb_mnt, missing_files, missing_dirs):
    for src_path, dest_path in missing_files:
        src = usb_mnt / src_path
        if src.is_file():
            copy_file(src, dest_path)
    for src_path, dest_path in missing_dirs:
        src = usb_mnt / src_path
        if src.is_dir():
            copy_dir(src, dest_path)
        else:
            log.error(f"{src} does not exist on USB")


def mnt_cp_keys(
    file_cp_list: list[UsbFileCopy],
    dir_cp_list: list[UsbDirCopy],
    usb_mnt: Path = Path("/mnt/usb"),
) -> None:
    def unmount_usb():
        run_dmc(["umount", str(usb_mnt)], check=True)
        run_dmc(["udevadm", "settle"])
        time.sleep(1)

    if usb_mnt.is_mount() and yes_no("USB mounted, unmount?"):
        unmount_usb()
    missing_files, missing_dirs = collect_missing_paths(file_cp_list, dir_cp_list)
    if missing_files or missing_dirs:
        log.warning(
            f"Not yet present:\n{'\n'.join(str(path) for _, path in (missing_files + missing_dirs))}"
        )
        if not yes_no("Mount USB?"):
            return
        selected = get_device()
        usb_mnt.mkdir(parents=True, exist_ok=True)
        run_dmc(["mount", "-o", "ro", str(selected), str(usb_mnt)], check=True)
        run_dmc(["udevadm", "settle"])
        time.sleep(1)
        copy_usb_to_root(usb_mnt, missing_files, missing_dirs)
        if yes_no("Files copied, unmount?"):
            unmount_usb()
    else:
        log.info("All files to copy from USB found.")
