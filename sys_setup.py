#!/usr/bin/env python3
from archinstall.lib.command import SysCommand
import shlex
from archinstall.default_profiles.profile import GreeterType
from archinstall.lib.authentication.authentication_handler import AuthenticationHandler
from archinstall.lib.applications.application_handler import ApplicationHandler
from archinstall.lib.hardware import _sys_info, GfxDriver
from archinstall.lib.args import (
    ArchConfig,
    ArchConfigHandler,
    AuthenticationConfiguration,
)
from archinstall.lib.configuration import ConfigurationOutput
from archinstall.lib.disk.filesystem import FilesystemHandler
from archinstall.lib.disk.utils import disk_layouts
from archinstall.lib.general.general_menu import (
    PostInstallationAction,
    select_post_installation,
)
from archinstall.lib.global_menu import GlobalMenu
from archinstall.lib.installer import Installer, run_custom_user_commands
from archinstall.lib.menu.util import delayed_warning
from archinstall.lib.models import Bootloader
from archinstall.lib.models.device import DiskLayoutType, EncryptionType
from archinstall.lib.models.users import User
from archinstall.lib.output import debug, error, info
from archinstall.tui.ui.components import tui
from archinstall.lib.models.users import Password
from archinstall.lib.network.network_handler import install_network_config
from pathlib import Path
import sys
import time
import subprocess
import json
import re
import shutil
import pwd
import os
from utils import UsrSrv, NoahConfig, arch_config, pkgs, aur_pkgs
from getpass import getpass
import logging
from textwrap import dedent
from archinstall.lib.profile.profiles_handler import profile_handler


#########################
# LOG
#########################
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",  # cyan
        logging.INFO: "\033[34m",  # blue
        logging.WARNING: "\033[93m",  # yellow
        logging.ERROR: "\033[31m",  # red
        logging.CRITICAL: "\033[41m",  # red background
    }
    RESET = "\033[0m"
    UNDERLINE = "\033[4m"
    NAME_COLOR = "\033[93m"  # yellow

    def format(self, record):
        colored_name = f"{self.NAME_COLOR}{record.name}{self.RESET}"
        level_color = self.COLORS.get(record.levelno, "")
        colored_message = f"{level_color}{record.getMessage()}{self.RESET}"
        message = f"{colored_name}: {colored_message}"
        if record.levelno == logging.CRITICAL:
            message = f"{self.UNDERLINE}{message}{self.RESET}"
        return message


def get_logger(log_name: str | None = None, level=logging.INFO):
    logger = logging.getLogger(log_name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ColorFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


log = get_logger("Noah")


def run_dmc(
    cmd: list[str],
    check: bool = False,
    input_text: str = "",
    shell: bool = False,
    cwd=None,
    interactive=False,
):
    if interactive:
        return subprocess.Popen(cmd).wait()
    log = get_logger("Run CMD")
    try:
        log.info(" ".join(cmd))
        result = subprocess.run(
            cmd,
            text=True,
            check=check,
            capture_output=True,
            input=input_text,
            shell=shell,
            cwd=cwd,
        )
        if result.stdout:
            log.info(f"stdout: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        log.error(f"Command failed: {' '.join(cmd)} (exit {e.returncode})")
        if e.stdout:
            log.info(f"stdout: {e.stdout.strip()}")
        if e.stderr:
            log.error(f"stderr: {e.stderr.strip()}")
        return e


def yes_no(prompt: str, default: bool = True) -> bool:
    while True:
        r = (
            input(f"\033[92m{prompt} {'(Y/n)' if default else '(y/N)'}: \033[0m")
            .strip()
            .lower()
        )
        if r == "":
            return default
        if r in ("y"):
            return True
        if r in ("n"):
            return False


def ping(host: str = "google.com") -> bool:
    cmd = ["ping", "-c", "1", host]
    return (
        subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
        == 0
    )


#########################
# UTILS
#########################
def run_chroot(
    commands: list[str], mnt_point: Path, username: str | None = None, peek=True
) -> None:
    script_path = "var/tmp/user-commands.sh"
    chroot_path = mnt_point / script_path
    chroot_path.parent.mkdir(parents=True, exist_ok=True)
    with open(chroot_path, "w") as script:
        script.write("#!/bin/bash\n")
        if peek:
            script.write("set -e\n")
        for cmd in commands:
            if username:
                log.info(f"Will run as {username}: {cmd}")
                cmd = f"su - {username} -c {shlex.quote(cmd)}"
            log.info(f"Chroot run: {cmd}")
            script.write(cmd + "\n")
    chroot_path.chmod(0o755)
    SysCommand(f"arch-chroot -S {mnt_point} /{script_path}")
    chroot_path.unlink()


def load_users_json(json_file: Path) -> dict:
    if not json_file.exists():
        log.error(f"JSON file {json_file} does not exist.")
        return {"users": []}
    try:
        with json_file.open() as f:
            data = json.load(f)
            users = data.get("users", [])
            if not users:
                log.warning(f"No users found in {json_file}")
            return {"users": users}
    except Exception as e:
        log.error(f"Failed to read JSON: {e}")
        return {"users": []}


def copy_file(src: Path, dest: Path) -> None:
    if not src.is_file():
        log.error(f"{src} does not exist")
        return
    dest = dest / src.name if dest.is_dir() else dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    log.info(f"Copied file: {src} -> {dest}")


def copy_dir(src: Path, dest: Path) -> None:
    if not src.is_dir():
        log.error(f"{src} does not exist")
        return
    shutil.copytree(src, dest, dirs_exist_ok=True, ignore_dangling_symlinks=True)
    log.info(f"Copied directory: {src} -> {dest}")


###################################
# USB Files
###################################
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
    key_dir: str | None = None,
    key_files: list[str] | None = None,
    wireguard_dir: str | None = None,
    usb_mnt: Path = Path("/mnt/usb"),
    home: Path = Path.home(),
) -> None:
    if usb_mnt.is_mount() and yes_no("USB mounted, unmount?"):
        run_dmc(["umount", str(usb_mnt)])
        run_dmc(["udevadm", "settle"])
        time.sleep(1)
    missing = []
    if key_dir and key_files:
        missing += [k for k in key_files if not (home / key_dir / k).exists()]
    if wireguard_dir and not (home / wireguard_dir).is_dir():
        missing.append(wireguard_dir)
    if not missing:
        log.info("All required files present.")
        return
    if not yes_no(f"Mount USB to copy {', '.join(missing)}"):
        return
    selected = get_device()
    run_dmc(["udevadm", "settle"])
    usb_mnt.mkdir(parents=True, exist_ok=True)
    run_dmc(["mount", "-o", "ro", str(selected), str(usb_mnt)], check=True)
    time.sleep(2)
    if key_dir and key_files:
        (home / key_dir).mkdir(parents=True, exist_ok=True)
        for k in key_files:
            copy_file(usb_mnt / key_dir / k, home / key_dir / k)
    if wireguard_dir:
        copy_dir(usb_mnt / wireguard_dir, home / wireguard_dir)
    time.sleep(1)
    if yes_no("Files copied, unmount?"):
        run_dmc(["umount", str(usb_mnt)])
        run_dmc(["udevadm", "settle"])
        time.sleep(1)


###################################
# ETC/BOOT
###################################
def generate_pacman_conf(
    mnt_point: Path | None,
    no_extracts: list,
    parallel_downloads: int = 10,
    multilib: bool = True,
) -> None:
    no_extract_lines = "\n        ".join(
        [f"NoExtract = {item}" for item in no_extracts]
    )
    pacman_content = dedent(f"""
        [options]
        HoldPkg = pacman glibc
        Architecture = auto
        Color
        ILoveCandy
        ParallelDownloads = {parallel_downloads}
        DownloadUser = alpm
        SigLevel    = Required DatabaseOptional
        LocalFileSigLevel = Optional
        {no_extract_lines}

        [core]
        Include = /etc/pacman.d/mirrorlist

        [extra]
        Include = /etc/pacman.d/mirrorlist

        {"[multilib]\n        Include = /etc/pacman.d/mirrorlist" if multilib else ""}
    """)
    pacman_p = "etc/pacman.conf"
    pac_p = Path("/") / pacman_p
    if mnt_point:
        pac_p = mnt_point / pacman_p
    pac_p.write_text(pacman_content)


def write_etc_file(mnt_point: Path, files_to_write: dict[str, str]) -> None:
    for filepath, content in files_to_write.items():
        full_path = mnt_point / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with full_path.open("w") as file:
            file.write(content)
            log.info(f"Content: {content}\nWritten to: {full_path}")


def chaotic_repo(installation: Installer) -> None:
    srv = "keyserver.ubuntu.com"
    web = "https://cdn-mirror.chaotic.cx/chaotic-aur/"
    cmds = [
        ["pacman-key", "--init"],
        ["pacman-key", "--recv-key", "3056513887B78AEB", "--keyserver", srv],
        ["pacman-key", "--lsign-key", "3056513887B78AEB"],
        ["pacman", "-U", "--noconfirm", f"{web}chaotic-keyring.pkg.tar.zst"],
        ["pacman", "-U", "--noconfirm", f"{web}chaotic-mirrorlist.pkg.tar.zst"],
    ]
    for cmd in cmds:
        run_dmc(cmd)
        installation.arch_chroot(" ".join(cmd))
    for path in [Path("/etc/pacman.conf"), installation.target / "etc/pacman.conf"]:
        with path.open("a") as f:
            f.write("\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n")
    run_dmc(["pacman", "-Sy"], check=True)
    installation.arch_chroot("pacman -Sy")


def generate_mpd_tmpfiles(installation: Installer, users: list[User]) -> None:
    for user in users:
        base = installation.target / "home"
        dir_path = base / user.username / ".cache" / "mpd" / "playlists"
        dir_path.mkdir(parents=True, exist_ok=True)
        dir_path.chmod(0o755)
        installation.chown(user.username, str(dir_path))
        installation.chown(user.username, str(dir_path.parent))


def configure_sudo(mnt_point: Path, user_name: str, pless=False) -> None:
    sudoers_content = dedent(
        f"""\
        {user_name} ALL=(ALL:ALL) {"NOPASSWD:ALL" if pless else "ALL"}
        Defaults    insults
        Defaults    passwd_tries=10
        Defaults    lecture=never
        Defaults    passwd_timeout=0
        Defaults    timestamp_timeout=20
        Defaults    timestamp_type=global
        Defaults    editor=/usr/sbin/nvim, !env_editor
        """
    )
    (mnt_point / f"etc/sudoers.d/00_{user_name}").write_text(sudoers_content)
    log.info(f"{'Removed' if pless else 'Created'} pass requirement for {user_name}")


def sys_dots(mnt_point: Path, script_dir: Path) -> None:
    for dir_name in ["etc", "usr"]:
        source_dir = script_dir / dir_name
        target_dir = mnt_point / dir_name
        log.info("Processing %s -> %s", source_dir, target_dir)
        if not source_dir.exists():
            log.error("Source directory not found: %s", source_dir)
            continue
        shutil.copytree(
            source_dir, target_dir, dirs_exist_ok=True, copy_function=shutil.copy2
        )
        log.info("Copied %s to %s", source_dir, target_dir)


def sysd_plymouth_setup(mnt_point: Path, boot_opts=["quiet", "splash"]) -> None:
    entries_dir = mnt_point / "boot" / "loader" / "entries"
    for entry in entries_dir.iterdir():
        lines = entry.read_text().splitlines()
        new_lines = []
        for line in lines:
            if line.startswith("options "):
                existing_opts = line[len("options ") :].split()
                for opt in boot_opts:
                    if opt not in existing_opts:
                        existing_opts.append(opt)
                line = "options " + " ".join(existing_opts)
            new_lines.append(line)
        entry.write_text("\n".join(new_lines) + "\n")


def modify_fstab(mnt_point: Path) -> None:
    fstab_path = mnt_point / "etc" / "fstab"
    content = fstab_path.read_text()
    content = re.sub(r"^(?!#).*?\bfmask=\d+", "fmask=0077", content, flags=re.MULTILINE)
    content = re.sub(r"^(?!#).*?\bdmask=\d+", "dmask=0077", content, flags=re.MULTILINE)
    fstab_path.write_text(content)


def modify_mkinit(mnt_point: Path, hooks: list[str], plymouth: bool) -> None:
    if plymouth and "plymouth" not in hooks:
        hooks.insert(hooks.index("kms") + 1, "plymouth")
    with open(f"/{mnt_point}/etc/mkinitcpio.conf", "r+") as mkinit:
        content = mkinit.read()
        content = re.sub(r"\nHOOKS=.*", f"\nHOOKS=({' '.join(hooks)})", content)
        mkinit.seek(0)
        mkinit.truncate()
        mkinit.write(content)


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


###################################
# USR_SVC
###################################
def enable_user_serv(
    installation: Installer, units: list[UsrSrv], username: str
) -> None:
    base_dir = f"home/{username}/.config/systemd/user"
    for unit in units:
        target_dir = f"{base_dir}/{unit.target}.target.wants"
        full_target_dir = installation.target / target_dir
        full_target_dir.mkdir(parents=True, exist_ok=True)
        installation.chown(username, f"/{target_dir}")
        for service in unit.services:
            source_path = Path(unit.source) / service
            symlink_path = full_target_dir / service
            symlink_path.symlink_to(source_path)
            installation.chown(username, f"/{target_dir}")


def user_service(
    installation: Installer,
    users: list[User],
    terminal: str,
    user_script="sys_setup.py",
    script_dir: str = Path(__file__).resolve().parent.name,
) -> None:
    if terminal.strip().lower() == "alacritty":
        terminal = "alacritty -e"
    for user in users:
        dir_path = f"home/{user.username}/.config/systemd/user"
        run_script = f"/home/{user.username}/{script_dir}/{user_script}"
        name = f"{user_script.rsplit('.', 1)[0]}.service"
        content = dedent(
            f"""\
            [Unit]
            Description=Open {terminal} {run_script} on login
            After=graphical-session.target

            [Service]
            Type=oneshot
            ExecStart=/usr/bin/{terminal} python {run_script}
            Restart=no

            [Install]
            WantedBy=graphical-session.target
            """
        )
        (installation.target / dir_path / name).write_text(content)
        unit = UsrSrv(
            source=f"/{dir_path}", target="graphical-session", services=[name]
        )
    for user in users:
        enable_user_serv(installation, [unit], user.username)


def install_icons(installation: Installer):
    git = "https://github.com/vinceliuice/WhiteSur-icon-theme.git"
    installation.arch_chroot(f"git clone {git}")
    installation.arch_chroot("bash ./WhiteSur-icon-theme/install.sh")
    installation.arch_chroot("rm -rf ./WhiteSur-icon-theme")
    icon_path = installation.target / "usr/share/icons"
    white_sur_light = icon_path / "WhiteSur-light"
    if white_sur_light.exists():
        shutil.rmtree(white_sur_light)
        log.info(f"Removed {white_sur_light}")
    themes_to_modify = []
    for folder in icon_path.iterdir():
        if folder.is_dir() and ("-dark" in folder.name or "WhiteSur" in folder.name):
            themes_to_modify.append(folder)
    for theme_dir in themes_to_modify:
        for svg_file in theme_dir.rglob("*.svg"):
            if svg_file.is_file():
                text = svg_file.read_text()
                if "#ffffff" in text:
                    svg_file.write_text(text.replace("#ffffff", "#F4F5F6"))
                    log.info(f"Modified {svg_file}")


###################################
# User Space
###################################
def copy_keys(
    installation: Installer,
    usb_key_dir: str,
    username: str,
    to_cp: dict[str, tuple[str, ...]],
) -> None:
    for folder, files in to_cp.items():
        sys_path = f"home/{username}/{folder}"
        mnt_dir = installation.target / sys_path
        mnt_dir.mkdir(parents=True, exist_ok=True)
        mnt_dir.chmod(0o700)
        for name in files:
            src = Path("/root") / usb_key_dir / name
            dest = mnt_dir / name
            copy_file(src, dest)
            dest.chmod(0o600)
            installation.chown(username, f"/{sys_path}/{name}")
        installation.chown(username, f"/{sys_path}")


def set_extensions(mnt_point: Path, browser: str, ext_names: list[str]) -> None:
    file_path = mnt_point / "usr" / "lib" / browser / "distribution" / "policies.json"
    uninstall_names = ["google", "bing", "amazondotcom", "ebay", "twitter"]
    new_policies = {
        "DisableAppUpdate": True,
        "DisableDeveloperTools": False,
        "DisableFeedbackCommands": True,
        "DisableFirefoxStudies": True,
        "DisablePocket": True,
        "DisableProfileImport": False,
        "DisableSetDesktopBackground": False,
        "DisableTelemetry": True,
        "OverrideFirstRunPage": "about:welcome",
        "OverridePostUpdatePage": "",
        "DNSOverHTTPS": {"Enabled": False, "ProviderURL": "", "Locked": False},
        "HardwareAcceleration": True,
        "WebsiteFilter": {
            "Block": ["https://localhost/*"],
            "Exceptions": ["https://localhost/*"],
        },
        "Extensions": {
            "Install": [
                f"https://addons.mozilla.org/firefox/downloads/latest/{ext}/latest.xpi"
                for ext in ext_names
            ],
            "Uninstall": [f"{name}@search.mozilla.org" for name in uninstall_names],
        },
        "3rdparty": {
            "Extensions": {
                "uBlock0@raymondhill.net": {
                    "adminSettings": {
                        "assetsBootstrapLocation": "https://codeberg.org/librewolf/source/raw/branch/main/assets/uBOAssets.json"
                    }
                }
            }
        },
        "SearchEngines": {
            "PreventInstalls": False,
            "Default": "DuckDuckGo",
            "Remove": ["Bing", "Amazon.com", "eBay", "Twitter"],
        },
    }
    data = {}
    if file_path.exists():
        try:
            data = json.loads(file_path.read_text())
        except json.JSONDecodeError:
            log.warning(f"Corrupt JSON in {file_path}, resetting.")
    data.setdefault("policies", {}).update(new_policies)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data, indent=2))
    log.info(f"Policies for {browser} have been set (overwritten).")


def hide_apps(installation: Installer, users: list[User], nc: NoahConfig):
    for user in users:
        nc.populate_usr_srv(user.username)
        user_home = f"home/{user.username}"
        for app in nc.apps_to_hide:
            file_p = f"{user_home}/.local/share/applications/{app}.desktop"
            (installation.target / file_p).write_text(
                "[Desktop Entry]\nNoDisplay=true\n"
            )
            installation.chown(user.username, f"/{file_p}")


def copy_skel(mountpoint: Path, nc: NoahConfig):
    tmp = mountpoint / "tmp" / nc.dots_repo
    tmp.mkdir(exist_ok=True)
    git = f"https://github.com/{nc.git_user}/{nc.dots_repo}.git"
    run_dmc(["git", "clone", git, str(tmp)])
    shutil.rmtree(tmp / ".git")
    for p in tmp.iterdir():
        p.rename(p.parent / ("." + p.name))
    copy_dir(tmp, mountpoint / "etc" / "skel")


###################################
# Archinstall
###################################
def show_menu(arch_config_handler: ArchConfigHandler) -> None:
    global_menu = GlobalMenu(arch_config_handler.config)
    global_menu.disable_all()
    global_menu.set_enabled("disk_config", True)
    global_menu.set_enabled("archinstall_language", True)
    global_menu.set_enabled("locale_config", True)
    global_menu.set_enabled("timezone", True)
    global_menu.set_enabled("bootloader_config", True)
    global_menu.set_enabled("ntp", True)
    global_menu.set_enabled("kernels", True)
    global_menu.set_enabled("hostname", True)
    global_menu.set_enabled("auth_config", True)
    global_menu.set_enabled("app_config", True)
    global_menu.set_enabled("packages", True)
    global_menu.set_enabled("__config__", True)
    result: ArchConfig | None = tui.run(global_menu)
    if result is None:
        sys.exit(0)


def perform_installation(
    arch_config_handler: ArchConfigHandler,
    auth_handler: AuthenticationHandler,
    application_handler: ApplicationHandler,
    nc: NoahConfig,
    gfx_drivers: list[GfxDriver],
) -> None:
    script_d = Path(__file__).resolve().parent
    start_time = time.monotonic()
    info("Starting installation...")
    mountpoint = arch_config_handler.args.mountpoint
    config = arch_config_handler.config
    if not config.disk_config:
        error("No disk configuration provided")
        return
    disk_config = config.disk_config
    run_mkinitcpio = not config.bootloader_config or not config.bootloader_config.uki
    locale = config.locale_config
    with Installer(
        mountpoint,
        disk_config,
        kernels=config.kernels,
        silent=arch_config_handler.args.silent,
    ) as installation:
        if disk_config.config_type != DiskLayoutType.Pre_mount:
            installation.mount_ordered_layout()
        installation.sanity_check(
            arch_config_handler.args.offline,
            arch_config_handler.args.skip_ntp,
            arch_config_handler.args.skip_wkd,
        )
        if disk_config.config_type != DiskLayoutType.Pre_mount:
            if (
                disk_config.disk_encryption
                and disk_config.disk_encryption.encryption_type
                != EncryptionType.NO_ENCRYPTION
            ):
                installation.generate_key_files()

        run_dmc(
            [
                "reflector",
                *(part for opt in nc.reflector_options for part in opt.split()),
            ]
        )
        generate_pacman_conf(None, no_extracts=list(nc.no_extracts))

        installation.minimal_installation(
            hostname=config.hostname, mkinitcpio=run_mkinitcpio, locale_config=locale
        )

        copy_file(
            Path("/etc/pacman.d/mirrorlist"), mountpoint / "etc/pacman.d/mirrorlist"
        )
        generate_pacman_conf(mountpoint, list(nc.no_extracts))

        if config.swap and config.swap.enabled:
            installation.setup_swap(algo=config.swap.algorithm)
        if (
            config.bootloader_config
            and config.bootloader_config.bootloader != Bootloader.NO_BOOTLOADER
        ):
            installation.add_bootloader(
                config.bootloader_config.bootloader,
                config.bootloader_config.uki,
                config.bootloader_config.removable,
            )
            if config.bootloader_config.bootloader == Bootloader.Systemd:
                if config.bootloader_config.uki:
                    print("Nope")
                else:
                    sysd_plymouth_setup(mountpoint)

        modify_mkinit(mountpoint, list(nc.mkinit_hooks), plymouth=True)

        for driver in gfx_drivers:
            profile_handler.install_gfx_driver(installation, driver)

        if config.network_config:
            install_network_config(
                config.network_config, installation, config.profile_config
            )

        installation.add_additional_packages("realtime-privileges")
        copy_skel(mountpoint, nc)

        users = None
        if config.auth_config:
            if config.auth_config.users:
                users = config.auth_config.users
                installation.create_users(config.auth_config.users)
                configure_sudo(mountpoint, users[0].username, pless=True)

        if app_config := config.app_config:
            application_handler.install_applications(installation, app_config)

        chaotic_repo(installation)

        if config.packages and config.packages[0] != "":
            installation.add_additional_packages(config.packages)

        if timezone := config.timezone:
            installation.set_timezone(timezone)

        if config.ntp:
            installation.activate_time_synchronization()

        if config.auth_config and config.auth_config.root_enc_password:
            root_user = User("root", config.auth_config.root_enc_password, False)
            installation.set_user_password(root_user)

        for gfx_driver in gfx_drivers:
            profile_handler.install_gfx_driver(installation, gfx_driver)
        profile_handler.install_greeter(installation, GreeterType.Ly)
        write_etc_file(mountpoint, nc.etc_files_to_write)
        reflector_timer_conf = mountpoint / "etc/xdg/reflector/reflector.conf"
        reflector_timer_conf.write_text("\n".join(nc.reflector_options))
        copy_dir(Path("/root") / nc.wireguard_dir, mountpoint / "etc" / "wireguard")
        set_extensions(mountpoint, nc.firefox_browser, list(nc.firefox_extensions))
        sys_dots(mountpoint, script_d)
        install_icons(installation)
        if config.auth_config:
            if users:
                for user in users:
                    installation.arch_chroot("xdg-user-dirs-update", user.username)
                    usr_srv = nc.populate_usr_srv(user.username)
                    enable_user_serv(installation, usr_srv, user.username)
                generate_mpd_tmpfiles(installation, users)
                configure_sudo(mountpoint, users[0].username, pless=True)
                cmd = [f"paru -S --noconfirm --needed {' '.join(aur_pkgs)}"]
                run_chroot(cmd, mountpoint, users[0].username)
                cmd = [
                    f"chown -R {users[0].username}:{users[0].username} /home/{users[0].username}"
                ]
                run_chroot(cmd, mountpoint, users[0].username)
                configure_sudo(mountpoint, users[0].username)
                copy_dir(
                    script_d,
                    (mountpoint / f"home/{users[0].username}" / script_d.name),
                )
                copy_keys(installation, nc.usb_key_dir, users[0].username, nc.to_cp)
                user_service(installation, users, nc.terminal)
                hide_apps(installation, users, nc)
                auth_handler.setup_auth(
                    installation, config.auth_config, config.hostname
                )
        if services := config.services:
            installation.enable_service(services)

        installation.disable_service(list(nc.disable_svcs))

        if disk_config.has_default_btrfs_vols():
            btrfs_options = disk_config.btrfs_options
            snapshot_config = btrfs_options.snapshot_config if btrfs_options else None
            snapshot_type = snapshot_config.snapshot_type if snapshot_config else None
            if snapshot_type:
                bootloader = (
                    config.bootloader_config.bootloader
                    if config.bootloader_config
                    else None
                )
                installation.setup_btrfs_snapshot(snapshot_type, bootloader)

        if cc := config.custom_commands:
            run_custom_user_commands(cc, installation)

        installation.genfstab()
        modify_fstab(mountpoint)

        debug(f"Disk states after installing:\n{disk_layouts()}")
        if not arch_config_handler.args.silent:
            elapsed_time = time.monotonic() - start_time
            action: PostInstallationAction = tui.run(
                lambda: select_post_installation(elapsed_time)
            )
            match action:
                case PostInstallationAction.EXIT:
                    pass
                case PostInstallationAction.REBOOT:
                    _ = subprocess.run(["sudo", "reboot"], check=True)
                case PostInstallationAction.CHROOT:
                    try:
                        installation.drop_to_shell()
                    except Exception:
                        pass


def sys_setup() -> None:
    nc = NoahConfig()
    mnt_cp_keys(nc.usb_key_dir, list(nc.usb_cp_files), nc.wireguard_dir)
    arch_config_handler = ArchConfigHandler()
    # users_json = load_users_json(Path("/root") / nc.usb_key_dir / nc.my_pass)
    # if users_list := users_json.get("users", []):
    user = User(
        username="nick",
        password=Password(plaintext="password"),
        sudo=True,
        groups=list(nc.groups),
    )
    arch_config_handler.config.auth_config = AuthenticationConfiguration(
        None, [user], None
    )
    arch_config_handler.config.hostname = arch_config.hostname
    arch_config_handler.config.ntp = arch_config.ntp
    arch_config_handler.config.swap = arch_config.swap
    arch_config_handler.config.profile_config = arch_config.profile_config
    arch_config_handler.config.timezone = arch_config.timezone
    arch_config_handler.config.bootloader_config = arch_config.bootloader_config
    arch_config_handler.config.ntp = True
    arch_config_handler.config.kernels = arch_config.kernels
    arch_config_handler.config.services = arch_config.services + list(
        nc.custom_services
    )
    arch_config_handler.config.app_config = arch_config.app_config
    gfx_drivers = get_gfx_drivers(_sys_info.graphics_devices)
    base_pkgs = pkgs["base"] + pkgs["language"] + pkgs["chaotic_repo"]
    if GfxDriver.VMOpenSource not in gfx_drivers:
        base_pkgs.extend(pkgs["extra"] + pkgs["extra_chaos"])
    arch_config_handler.config.packages = base_pkgs
    show_menu(arch_config_handler)
    config = ConfigurationOutput(arch_config_handler.config)
    config.write_debug()
    config.save()
    if not arch_config_handler.args.silent:
        aborted = False
        res: bool = tui.run(config.confirm_config)
        if not res:
            debug("Installation aborted")
            aborted = True
        if aborted:
            return sys_setup()
    if arch_config_handler.config.disk_config:
        fs_handler = FilesystemHandler(arch_config_handler.config.disk_config)
        if not delayed_warning("Starting device modifications in "):
            return sys_setup()
        fs_handler.perform_filesystem_operations()
    perform_installation(
        arch_config_handler,
        AuthenticationHandler(),
        ApplicationHandler(),
        nc,
        gfx_drivers,
    )


############################
# USER SETUP
############################
def iwctl_scan() -> bool:
    result = run_dmc(["sudo", "iwctl", "station", "wlan0", "scan"], check=False)
    time.sleep(10)
    if result.returncode == 0:
        return True
    return False


############################
# Dotfile Symlink
############################
def deploy_dotfiles(
    HOME: Path,
    dot_dir: Path,
    dirs_to_link: list[str],
    ind_dirs: dict[str, Path],
    sec_dots_dir: Path,
):
    def link_path(src: Path, dst: Path) -> bool:
        dst.parent.mkdir(parents=True, exist_ok=True)
        rel = src.relative_to(dst.parent, walk_up=True)
        if dst.is_symlink() and dst.readlink() == rel:
            return False
        if dst.exists():
            if dst.is_dir() and not dst.is_symlink():
                shutil.rmtree(dst)
            else:
                dst.unlink(missing_ok=True)
            log.info(f"Removed: {dst}")
        dst.symlink_to(rel, target_is_directory=src.is_dir())
        log.info(f"Linked: {dst} → {rel}")
        return True

    linked = 0
    for src in dot_dir.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(dot_dir)
        if rel.parts[0] == ".git":
            continue
        if any(rel.is_relative_to(Path(d)) for d in dirs_to_link):
            continue
        dst = HOME / ("." + str(rel))
        dst.parent.mkdir(parents=True, exist_ok=True)
        if link_path(src, dst):
            linked += 1
    for d in dirs_to_link:
        src = dot_dir / d
        if not src.is_dir():
            continue
        dst = HOME / ("." + d)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if link_path(src, dst):
            linked += 1
    for src_name, dst_dir in ind_dirs.items():
        src_dir = sec_dots_dir / src_name
        if not src_dir.is_dir():
            continue
        for src in src_dir.rglob("*"):
            if not src.is_file():
                continue
            dst = dst_dir / src.relative_to(src_dir)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if link_path(src, dst):
                linked += 1
    run_dmc(["hyprctl", "reload"])
    log.info(f"Linked: {linked}")


############################
# Encryption/Keys
############################
def import_ssh(key_path: Path) -> None:
    if not Path(f"/run/user/{os.getuid()}/gcr/ssh").exists():
        run_dmc(["systemctl", "--user", "enable", "gcr-ssh-agent.socket"])
        run_dmc(["systemctl", "--user", "start", "gcr-ssh-agent.socket"])
    run_dmc(["ssh-add", str(key_path)], check=False)
    log.info(f"SSH key {key_path} added or already present.")


def import_gpg(gpg_path: Path) -> None:
    import gnupg

    key_data = gpg_path.read_text()
    gpg = gnupg.GPG()
    pwd = getpass("Enter GPG Password:")
    import_result = gpg.import_keys(key_data, pwd)
    log.info(import_result.results)


def init_gocrypt(enc_dir: Path) -> None:
    enc_dir.mkdir(parents=True, exist_ok=True)
    while True:
        pw1 = getpass("Enter new gocryptfs password: ")
        pw2 = getpass("Confirm password: ")
        if pw1 == pw2 and pw1:
            break
        log.warning("Passwords do not match or empty. Try again.\n")
    cmd = ["gocryptfs", "-init", "--passfile", "/dev/stdin", str(enc_dir)]
    run_dmc(cmd, check=True, input_text=pw1)
    log.info(f"gocryptfs initialized at {enc_dir}.")


############################
# MariaDB
############################
def enable_mariadb(user_name) -> None:
    while True:
        p1 = getpass("Mariadb password: ")
        p2 = getpass("Confirm: ")
        if p1 == p2:
            password = p1
            break
        print("Passwords do not match, try again.")
    commands = [
        [
            "sudo",
            "mariadb-install-db",
            "--user=mysql",
            "--basedir=/usr",
            "--datadir=/var/lib/mysql",
        ],
        ["sudo", "systemctl", "start", "mariadb"],
        [
            "sudo",
            "/usr/bin/mariadb",
            "-e",
            (
                f"CREATE USER '{user_name}'@'localhost' IDENTIFIED BY '{password}'; "
                f"GRANT ALL PRIVILEGES ON mydb.* TO '{user_name}'@'localhost'; "
                "FLUSH PRIVILEGES;"
            ),
        ],
    ]
    for cmd in commands:
        result = run_dmc(cmd)
        if result and result.returncode != 0:
            log.error(f"Command failed: {cmd}")


############################
# Git/Repos
############################
def ensure_github_known_hosts(HOME: Path) -> None:
    kh = HOME / ".ssh" / "known_hosts"
    kh.parent.mkdir(parents=True, exist_ok=True)
    if not kh.exists():
        kh.touch()
    content = kh.read_text(errors="ignore")
    if "github.com" not in content:
        scan = run_dmc(["ssh-keyscan", "-H", "github.com"])
        if scan and scan.stdout:
            kh.write_text(content + scan.stdout)
            log.info("Added github.com to known_hosts")
        else:
            log.warning("Failed to scan github.com for known_hosts")


def clone_repos(git_user: str, git_repos: list, dest: Path, ssh: bool) -> None:
    def url(repo: str) -> str:
        if ssh:
            return f"git@github.com:{git_user}/{repo}.git"
        return f"https://github.com/{git_user}/{repo}.git"

    dest.mkdir(parents=True, exist_ok=True)
    for repo in git_repos:
        repo_path = dest / repo
        if repo_path.exists():
            log.info(f"{repo_path} exists, skipping.")
            continue
        result = run_dmc(["git", "clone", url(repo), str(repo_path)], check=False)
        if result.returncode == 0:
            log.info(f"Cloned {repo}")
        else:
            log.warning(f"Failed to clone {repo}")


def configure_git() -> None:
    result = run_dmc(["ssh-add", "-l"])
    lines = result.stdout.strip().splitlines()
    if not lines:
        log.warning("No SSH keys found")
        return
    parts = lines[0].split()
    my_email = parts[2]
    my_name = input("Enter your full real name (git): ").strip()
    run_dmc(["git", "config", "--global", "user.email", my_email])
    run_dmc(["git", "config", "--global", "user.name", my_name])
    log.info(f"Configured git with email={my_email} and name={my_name}")


############################
# Icons/Folders
############################
def set_folder_icons(
    custom_folder_icons: dict[Path, str],
    icon_dir="/usr/share/icons/WhiteSur-dark/places/scalable",
) -> None:
    for folder, icon_name in custom_folder_icons.items():
        icon = f"{icon_dir}/{icon_name}.svg"
        folder.mkdir(parents=True, exist_ok=True)
        if Path(icon).exists():
            icon_uri = f"file://{icon}"
            cmd = ["gio", "set", str(folder), "metadata::custom-icon", icon_uri]
            run_dmc(cmd)


############################
# Launch Apps
############################
def pass_and_input(pass_path: Path):
    import pyperclip

    password = pass_path.read_text().strip()
    os.environ["CLIPBOARD_STATE"] = "sensitive"
    pyperclip.copy(password)
    log.info("Password copied to clipboard.")
    cmd = ["firedragon", "https://addons.mozilla.org/en-US/firefox/addon/proton-pass/"]
    subprocess.Popen(cmd).wait()
    pyperclip.copy("")
    log.info("Clipboard cleared.")
    os.environ.pop("CLIPBOARD_STATE", None)


def launch_apps(apps=["floorp", "protonmail-bridge", "betterbird", "steam"]):
    processes = []
    for app in apps:
        processes.append(subprocess.Popen(app))
    for app, process in zip(apps, processes):
        process.wait()
        log.info(f"{app} closed")


def scrcpy_setup(port=5555) -> None:
    answer = yes_no("Is your Android phone connected?")
    if not answer:
        log.info("Please connect your device via USB first.")
        return
    ip = next(
        (
            line.split("src")[-1].strip()
            for line in run_dmc(["adb", "shell", "ip", "route"]).stdout.splitlines()
            if "wlan" in line and "src" in line
        )
    )
    if not ip:
        log.warning("Could not determine device IP.")
        return
    target = f"{ip}:{port}"
    log.info(f"Trying {target}")
    msg = run_dmc(["adb", "connect", target])
    log.info((msg.stdout + msg.stderr).lower())


############################
# Main
############################
def user_setup():
    if shutil.which("zsh"):
        run_dmc(["chsh", "-s", "/usr/bin/zsh"], interactive=True)
    if Path("/etc/resolv.conf").is_symlink() and not ping():
        run_dmc(["sudo", "rm", "/etc/resolv.conf"])
        run_dmc(["sudo", "resolvconf", "-u"])
        run_dmc(["sudo", "systemctl", "restart", "iwd"])
        time.sleep(5)
        iwctl_scan()
        time.sleep(5)
    if shutil.which("tuned"):
        run_dmc(["tuned-adm", "profile", "laptop-ac-powersave"])
    uc = NoahConfig()
    if shutil.which("mariadb"):
        user = pwd.getpwuid(os.getuid()).pw_name
        enable_mariadb(user)
    if uc.ssh_path.exists():
        import_ssh(uc.ssh_path)
        configure_git()
        ensure_github_known_hosts(uc.HOME)
        clone_repos(uc.git_user, uc.repos + uc.private_repos, uc.GIT_DIR, ssh=True)
    else:
        clone_repos(uc.git_user, uc.repos, uc.GIT_DIR, ssh=False)
    if uc.gpg_path and not uc.gpg_path.exists():
        import_gpg(uc.gpg_path)
    if uc.ENCRYPTED and not (uc.ENCRYPTED / "gocryptfs.conf").exists():
        if shutil.which("gocryptfs"):
            init_gocrypt(uc.ENCRYPTED)
    if uc.dirs_icons:
        set_folder_icons(uc.dirs_icons)
    for plugin in uc.yazi_plugins:
        run_dmc(["ya", "pkg", "add", plugin])
    if any((uc.dots_path).iterdir()):
        deploy_dotfiles(uc.HOME, uc.dots_path, uc.dirs_to_link, uc.ind_dirs, uc.sec_dir)
        run_dmc(
            ["uv", "add", "openmeteo-requests"],
            cwd=f"{uc.HOME}/.local/bin/weather",
        )
    if uc.android:
        scrcpy_setup()
    if uc.masterpass_path.is_file():
        pass_and_input(uc.masterpass_path)
        launch_apps()
    run_dmc(
        ["gh", "auth", "login", "-h", "github.com", "-s", "delete_repo"],
        interactive=True,
    )
    for d in [(uc.HOME / "archinstall")]:
        if d.exists():
            shutil.rmtree(d)
    if yes_no("Reboot now?", default=False):
        run_dmc(["systemctl", "reboot"])
        log.info("Reboot cancelled.")
        return


if __name__ == "__main__":
    if os.geteuid() == 0:
        sys_setup()
    else:
        user_setup()
