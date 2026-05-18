###################################
# USB Files
###################################
from archinstall.lib.args import ArchConfigHandler, Arguments, ArchConfig
from archinstall.lib.hardware import GfxDriver, _sys_info
import time
from utils import run_dmc, yes_no, get_logger, copy_file
from lib.datahandler import NoahConfig
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


def copy_usb_to_root(nc: NoahConfig):
    if key_conf := nc.key_copy_config:
        list_tuple_paths = key_conf.usb_to_root()
        for src, dest in list_tuple_paths:
            copy_file(src, dest)
    if usb_file_conf := nc.additional_usb_to_cp_config:
        for copy in usb_file_conf.copies:
            for src, dest in copy.usb_to_root():
                copy_file(src, dest)
    if usb_dir_conf := nc.dir_contents_to_cp_config:
        for copy in usb_dir_conf.copies:
            for src, dest in copy.usb_to_root():
                copy_file(src, dest)


def mnt_cp_keys(nc: NoahConfig, usb_mnt: Path = Path("/mnt/usb")):
    """
    Ensure USB files are copied to /root and return a CopyProcessor instance.
    """

    def unmount_usb():
        run_dmc(["umount", str(usb_mnt)], check=True)
        run_dmc(["udevadm", "settle"])
        time.sleep(1)

    if usb_mnt.is_mount() and yes_no("USB mounted, unmount?"):
        unmount_usb()
    missing = check_missing(nc)
    if missing:
        log.warning("Not yet present: " + ", ".join(missing))
        if not yes_no("Mount USB?"):
            return
        selected = get_device()
        usb_mnt.mkdir(parents=True, exist_ok=True)
        run_dmc(["mount", "-o", "ro", str(selected), str(usb_mnt)], check=True)
        run_dmc(["udevadm", "settle"])
        time.sleep(1)
        copy_usb_to_root(nc)
        log.info("Missing files copied from USB to /root.")
        if yes_no("Files copied, unmount?"):
            unmount_usb()
    else:
        log.info("All files to copy from USB found.")


def get_gfx_drivers(graphics_devices: dict[str, str]) -> list[GfxDriver]:
    driver_map = {
        "nvidia": GfxDriver.NvidiaOpenKernel,
        "geforce": GfxDriver.NvidiaOpenKernel,
        "amd": GfxDriver.AmdOpenSource,
        "ati": GfxDriver.AmdOpenSource,
        "intel": GfxDriver.IntelOpenSource,
    }
    return [
        driver_map.get(device.lower().split()[0], GfxDriver.VMOpenSource)
        for device in graphics_devices
    ]


def check_missing(config: NoahConfig) -> list[Path]:
    missing: list[Path] = []
    if config.key_copy_config:
        src_base = (
            config.key_copy_config.resolver.usb / config.key_copy_config.source_dir
        )
        for name in config.key_copy_config.keys.values():
            path = src_base / name
            if not path.exists():
                missing.append(path)
    if config.additional_usb_to_cp_config:
        for copy in config.additional_usb_to_cp_config.copies:
            src_base = copy.resolver.usb / copy.source_dir
            for name in copy.names:
                path = src_base / name
                if not path.exists():
                    missing.append(path)
    if config.dir_contents_to_cp_config:
        for copy in config.dir_contents_to_cp_config.copies:
            src_base = copy.resolver.usb / copy.source_dir
            for name in copy.names:
                path = src_base / name
                if not path.exists():
                    missing.append(path)
    return missing


def init_arch_conf(arch_config_json: dict, auth_conf_path: str) -> ArchConfigHandler:
    arch_config_handler = ArchConfigHandler()
    arch_config = ArchConfig.from_config(arch_config_json, Arguments(None))
    if Path(auth_conf_path).is_file():
        with open(auth_conf_path, "r") as f:
            users_dict = json.load(f)
            auth_conf = ArchConfig.from_config(users_dict, Arguments(None))
            arch_config_handler.config.auth_config = auth_conf.auth_config
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
    arch_config_handler.config.services = arch_config.services
    arch_config_handler.config.app_config = arch_config.app_config
    return arch_config_handler


def init_setup(
    arch_config_json: dict,
    auth_conf_path: str,
    noahconf_json: dict,
    base_pkgs: list[str],
    non_vm_pkgs: list[str],
) -> tuple[ArchConfigHandler, NoahConfig, list[GfxDriver]]:
    nc = NoahConfig.from_config(noahconf_json)
    mnt_cp_keys(nc)
    arch_config_handler = init_arch_conf(arch_config_json, auth_conf_path)
    gfx_drivers = get_gfx_drivers(_sys_info.graphics_devices)
    if GfxDriver.VMOpenSource in gfx_drivers:
        base_pkgs.extend(["spice-vdagent", "qemu-guest-agent"])
    else:
        base_pkgs.extend(non_vm_pkgs)
    arch_config_handler.config.packages = base_pkgs
    return arch_config_handler, nc, gfx_drivers
