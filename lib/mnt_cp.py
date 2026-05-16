###################################
# USB Files
###################################
import time
from utils import run_dmc, yes_no, get_logger
from lib.datahandler import NoahConfig, CopyProcessor
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


def mnt_cp_keys(
    config: NoahConfig,
    usb_mnt: Path = Path("/mnt/usb"),
) -> CopyProcessor:
    """
    Ensure USB files are copied to /root and return a CopyProcessor instance.
    """

    def unmount_usb():
        run_dmc(["umount", str(usb_mnt)], check=True)
        run_dmc(["udevadm", "settle"])
        time.sleep(1)

    processor = CopyProcessor(config)
    if usb_mnt.is_mount() and yes_no("USB mounted, unmount?"):
        unmount_usb()
    missing_files, missing_dirs = processor.get_missing_root()
    if missing_files or missing_dirs:
        log.warning(
            "Not yet present:\n"
            + "\n".join(str(path) for _, path in (missing_files + missing_dirs))
        )
        if not yes_no("Mount USB?"):
            return processor
        selected = get_device()
        usb_mnt.mkdir(parents=True, exist_ok=True)
        run_dmc(["mount", "-o", "ro", str(selected), str(usb_mnt)], check=True)
        run_dmc(["udevadm", "settle"])
        time.sleep(1)
        processor.copy_usb_to_root()
        log.info("Missing files copied from USB to /root.")
        if yes_no("Files copied, unmount?"):
            unmount_usb()
    else:
        log.info("All files to copy from USB found.")

    return processor
