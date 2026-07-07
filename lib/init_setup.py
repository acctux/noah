###################################
# USB Files
###################################
from archinstall.lib.hardware import SysInfo
from typing import Any
from archinstall.lib.args import ArchConfigHandler, Arguments, ArchConfig
import time
from utils import run_dmc, yes_no, get_logger, copy_it
from lib.datahandler import NoahConfig
import subprocess
import json
from pathlib import Path

log = get_logger("Noah")


def get_device(
    min_gb: int = 20,
    allowed_fs: list[str] = ["ext4", "exfat"],
) -> str:
    def recurse(devices: list[dict[str, Any]]):
        for dev in devices:
            size_str = dev.get("size", "0G")
            try:
                clean_size = [c for c in size_str if c.isdigit() or c == "."]
                size_val = float("".join(clean_size))
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


def auto_services(
    base_pkgs: list[str],
    pkg_srvs={
        "ananicy-cpp": "ananicy-cpp",
        "reflector": "reflector.timer",
        "logrotate": "logrotate.timer",
        "man-db": "man-db.timer",
        "swayosd": "swayosd-libinput-backend",
    },
) -> list[str]:
    srvcs_to_enable = []
    for pkg, srv in pkg_srvs.items():
        if pkg in base_pkgs:
            srvcs_to_enable.append(srv)
    return srvcs_to_enable


def init_arch_conf(
    arch_config_json: dict,
    nc: NoahConfig,
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
    pkgs = arch_config.packages
    sys_info = SysInfo()
    if not sys_info.is_vm():
        if nc.non_vm_pkgs:
            pkgs += nc.non_vm_pkgs
    arch_config_handler.config.packages = pkgs
    auto_srvcs = auto_services(arch_config.packages)
    arch_config_handler.config.services = arch_config.services + auto_srvcs
    arch_config_handler.config.app_config = arch_config.app_config
    if auth_conf_path and auth_conf_path.is_file():
        with open(auth_conf_path, "r") as auth_conf_data:
            arch_config_handler.config.auth_config = ArchConfig.from_config(
                json.load(auth_conf_data), Arguments(None)
            ).auth_config
    return arch_config_handler


def init_setup(
    arch_config_json: dict,
    noahconf_json: dict,
    arch_config_handler: ArchConfigHandler,
    usb_mnt: Path = Path("/mnt/usb"),
) -> tuple[ArchConfigHandler, NoahConfig]:
    def unmount_usb(usb_mnt: Path):
        run_dmc(["umount", str(usb_mnt)], check=True)
        run_dmc(["udevadm", "settle"])
        time.sleep(1)

    nc = NoahConfig.from_config(noahconf_json)
    if usb_mnt.is_mount() and yes_no("USB mounted, unmount?"):
        unmount_usb(usb_mnt)
    if copy_conf := nc.copy_config:
        missing = []
        for src, dest, type in copy_conf.resolve_usb_to_root():
            if not dest.exists():
                missing.append((src, dest, type))
            if type == "auth_conf":
                auth_conf_path = dest
        if missing:
            log.warning(
                f"Not present: {', '.join(dest.name for _, dest, _ in missing)}"
            )
            usb_mnt.mkdir(parents=True, exist_ok=True)
            if yes_no("Mount USB?"):
                if selected := get_device():
                    run_dmc(
                        ["mount", "-o", "ro", str(selected), str(usb_mnt)], check=True
                    )
                    run_dmc(["udevadm", "settle"])
                    time.sleep(1)
                    for src, dest, _ in missing:
                        copy_it(src, dest)
                    if yes_no("Files copied, unmount?"):
                        unmount_usb(usb_mnt)
        else:
            log.info("All files to copy from USB found.")
    arch_config_handler = init_arch_conf(
        arch_config_json, nc, auth_conf_path, arch_config_handler
    )
    return arch_config_handler, nc
