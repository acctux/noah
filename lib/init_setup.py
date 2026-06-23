###################################
# USB Files
###################################
from archinstall.lib.args import ArchConfigHandler, Arguments, ArchConfig
import time
from utils import run_dmc, yes_no, get_logger, copy_it
from lib.datahandler import NoahConfig
import subprocess
import json
from pathlib import Path

log = get_logger("Noah")


def unmount_usb(usb_mnt: Path):
    run_dmc(["umount", str(usb_mnt)], check=True)
    run_dmc(["udevadm", "settle"])
    time.sleep(1)


def get_device(
    min_gb: int = 20,
    allowed_fs: list[str] = ["ext4", "exfat"],
) -> str:
    def recurse(devices):
        for dev in devices:
            size_str = dev.get("size", "0G")
            try:
                size_val = float(
                    "".join(c for c in size_str if c.isdigit() or c == ".")
                )
                if size_str.endswith("M"):
                    size_val /= 1024
                elif size_str.endswith("T"):
                    size_val *= 1024
            except ValueError:
                size_val = 0.0
            if (
                dev["type"] == "part"
                and (dev.get("fstype") in allowed_fs)
                and dev.get("mountpoint") is None
                and size_val >= min_gb
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
    if not candidates:
        print(f"\033[91mNo valid ext4 or exfat partitions found >= {min_gb}GB.\033[0m")
        return ""

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
            print("Enter valid number.")
            continue
        selected_path = f"/dev/{candidates[int(choice) - 1][0]}"
        break
    return selected_path


def copy_usb_to_root(usb_path: Path, missing: list[tuple[Path, Path]]):
    if not yes_no("Mount USB?"):
        return
    selected = get_device()
    if not selected:
        return
    run_dmc(["mount", "-o", "ro", str(selected), str(usb_path)], check=True)
    run_dmc(["udevadm", "settle"])
    time.sleep(1)
    for src, dest in missing:
        copy_it(src, dest)
    if yes_no("Files copied, unmount?"):
        unmount_usb(usb_path)


def init_arch_conf(
    arch_config_json: dict,
    auth_conf_path: Path | None,
    arch_config_handler: ArchConfigHandler,
) -> ArchConfigHandler:
    arch_config = ArchConfig.from_config(arch_config_json, Arguments(None))
    arch_config_handler.config.hostname = arch_config.hostname
    arch_config_handler.config.ntp = arch_config.ntp
    arch_config_handler.config.swap = arch_config.swap
    arch_config_handler.config.profile_config = arch_config.profile_config
    arch_config_handler.config.network_config = arch_config.network_config
    arch_config_handler.config.pacman_config = arch_config.pacman_config
    arch_config_handler.config.timezone = arch_config.timezone
    arch_config_handler.config.bootloader_config = arch_config.bootloader_config
    arch_config_handler.config.ntp = arch_config.ntp
    arch_config_handler.config.kernels = arch_config.kernels
    arch_config_handler.config.packages = arch_config.packages
    arch_config_handler.config.services = arch_config.services
    arch_config_handler.config.app_config = arch_config.app_config
    if not auth_conf_path or not auth_conf_path.is_file():
        return arch_config_handler
    with open(auth_conf_path, "r") as f:
        users_dict = json.load(f)
        auth_conf = ArchConfig.from_config(users_dict, Arguments(None))
        arch_config_handler.config.auth_config = auth_conf.auth_config
        return arch_config_handler


def init_setup(
    arch_config_json: dict,
    noahconf_json: dict,
    arch_config_handler: ArchConfigHandler,
    usb_mnt: Path = Path("/mnt/usb"),
) -> tuple[ArchConfigHandler, NoahConfig]:
    nc = NoahConfig.from_config(noahconf_json)
    print(nc.auth_config)
    if usb_mnt.is_mount() and yes_no("USB mounted, unmount?"):
        unmount_usb(usb_mnt)
    if nc.copy_config or nc.auth_config:
        missing = []
        if nc.copy_config:
            for src, dest in nc.copy_config.resolve_usb_to_root():
                if not dest.exists():
                    missing.append((src, dest))
        if nc.auth_config:
            auth_src, auth_dest = nc.auth_config.resolve_usb_to_root()
            if not auth_dest.exists():
                missing.append((auth_src, auth_dest))
        if missing:
            log.warning("Not present: " + ", ".join([tar.name for _, tar in missing]))
            usb: Path = Path("/mnt/usb")
            usb.mkdir(parents=True, exist_ok=True)
            copy_usb_to_root(usb, missing)
        else:
            log.info("All files to copy from USB found.")
    arch_config_handler = init_arch_conf(
        arch_config_json, auth_dest, arch_config_handler
    )
    return arch_config_handler, nc
