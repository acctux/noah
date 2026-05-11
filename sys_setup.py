#!/usr/bin/env python3
import uuid
from archinstall.default_profiles.profile import GreeterType
from archinstall.lib.authentication.authentication_handler import (
    AuthenticationHandler,
)
from archinstall.lib.applications.application_handler import ApplicationHandler
from archinstall.lib.hardware import _sys_info, GfxDriver
from archinstall.lib.args import (
    ArchConfig,
    ArchConfigHandler,
    Arguments,
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
from archinstall.lib.network.network_handler import install_network_config
from archinstall.lib.profile.profiles_handler import profile_handler
from utils import run_dmc, yes_no, get_logger
from noah_processor import NoahConfig, UsbFileCopy, UsrSrv, UsbDirCopy
from typing import Any
from pathlib import Path
import sys
import time
import subprocess
import json
import re
import shutil
import extraconfig as ec
from textwrap import dedent

log = get_logger("Noah")


#########################
# UTILS
#########################
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


def collect_missing_paths(
    file_cp_list: list[UsbFileCopy], dir_cp_list: list[UsbDirCopy]
) -> tuple[list[tuple[Path, Path]], list[tuple[Path, Path]]]:
    missing_keys: list[tuple[Path, Path]] = []
    missing_dirs: list[tuple[Path, Path]] = []
    root_home = Path("/root")
    for group in file_cp_list:
        source_d = group.source_dir
        for name in group.file_names:
            dest_path = root_home / group.target_dir / name
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
    if missing_files:
        log.warning(
            f"Requested files not yet present: \033[36m{', '.join(path.name for _, path in missing_files)}\033[0m"
        )
    if missing_dirs:
        log.warning(
            f"Missing \033[36m{', '.join(path.name for _, path in missing_dirs)}\033[0m"
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
        ["pacman-key", "--add", "chaotic.key"],
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


def mpd_tmpfiles(installation: Installer, users: list[User]) -> None:
    for user in users:
        cache = f"home/{user.username}/.cache/"
        dir_path = installation.target / cache / "mpd/playlists"
        dir_path.mkdir(parents=True, exist_ok=True)
        dir_path.chmod(0o755)
        installation.arch_chroot(f"chown -R {user.username}:{user.username} /{cache}")


def configure_sudo(mnt_point: Path, user_name: str, pless=False) -> None:
    sudoers_content = dedent(
        f"""\
        {user_name} ALL=(ALL:ALL) {"NOPASSWD:ALL" if pless else "ALL"}
        Defaults    insults
        Defaults    passwd_tries=10
        Defaults    lecture=never
        Defaults    passwd_timeout=0
        Defaults    timestamp_timeout=20
        Defaults    pwfeedback
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


def sysd_boot_params(
    mnt_point: Path, plymouth: bool, apparmor: bool, boot_opts=[]
) -> None:
    if plymouth:
        boot_opts.extend(["quiet", "splash"])
    if apparmor:
        boot_opts.append("lsm=landlock,lockdown,yama,integrity,apparmor,bpf")
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
    home = Path(f"/home/{username}")
    for unit in units:
        source_dir = Path(unit.source)
        if unit.source == "/.config/systemd/user":
            source_dir = home / ".config/systemd/user"
        for service in unit.services:
            target_dir = home / ".config/systemd/user" / f"{unit.target}.target.wants"
            source_path = source_dir / service
            installation.arch_chroot(f"mkdir -p {target_dir}", username)
            link_path = installation.target / target_dir.relative_to("/") / service
            if not link_path.exists():
                installation.arch_chroot(
                    f"ln -sf {source_path} {target_dir}/{service}", username
                )
                log.info(f"{source_path} -> {target_dir}/{service}")


def user_service(
    installation: Installer,
    user: User,
    terminal: str,
    user_script="user_setup.py",
    script_dir: str = Path(__file__).resolve().parent.name,
) -> None:
    if terminal.strip().lower() == "alacritty":
        terminal = "alacritty -e"
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
    installation.arch_chroot(
        f"chown {user.username}:{user.username} /{dir_path}/{name}"
    )
    unit = UsrSrv(source=f"/{dir_path}", target="graphical-session", services=[name])
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
    installation: Installer, username: str, groups: list[UsbFileCopy]
) -> None:
    root_home = Path("/root")
    for group in groups:
        sys_path = Path("home") / username / group.target_dir
        target_dir = installation.target / sys_path
        target_dir.mkdir(parents=True, exist_ok=True)
        target_dir.chmod(0o700)
        installation.chown(username, str(sys_path))
        for name in group.file_names:
            src = root_home / group.target_dir / name
            dest = target_dir / name
            copy_file(src, dest)
            dest.chmod(0o600)
            installation.chown(username, str(sys_path / name))


def set_extensions(mnt_point: Path, browser: str, new_policies: dict[str, Any]) -> None:
    file_path = mnt_point / "usr" / "lib" / browser / "distribution" / "policies.json"
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


def hide_apps(installation: Installer, user: str, apps_to_hide: list[str]):
    user_home = f"home/{user}"
    for app in apps_to_hide:
        file_p = f"{user_home}/.local/share/applications/{app}.desktop"
        (installation.target / file_p).write_text("[Desktop Entry]\nNoDisplay=true\n")
        installation.chown(user, f"/{file_p}")


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
        base_packages=[],
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
            optional_repositories=[],
            mkinitcpio=run_mkinitcpio,
            hostname=config.hostname,
            locale_config=locale,
            pacman_config=None,
        )
        copy_file(
            Path("/etc/pacman.d/mirrorlist"), mountpoint / "etc/pacman.d/mirrorlist"
        )
        generate_pacman_conf(mountpoint, list(nc.no_extracts))
        copy_skel(mountpoint, nc)
        chaotic_repo(installation)

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

        if config.network_config:
            install_network_config(
                config.network_config, installation, config.profile_config
            )

        users = None
        if config.auth_config:
            if config.auth_config.users:
                users = config.auth_config.users
                installation.create_users(config.auth_config.users)
                auth_handler.setup_auth(
                    installation, config.auth_config, config.hostname
                )

        if app_config := config.app_config:
            application_handler.install_applications(installation, app_config)

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
        write_etc_file(mountpoint, ec.etc_files_to_write)
        reflector_timer_conf = mountpoint / "etc/xdg/reflector/reflector.conf"
        reflector_timer_conf.write_text("\n".join(nc.reflector_options))
        for dir_to_cp in nc.dir_contents_to_cp:
            for name in dir_to_cp.dir_names:
                copy_dir(
                    Path("/root") / name, mountpoint / dir_to_cp.target_dir.lstrip("/")
                )
        set_extensions(mountpoint, nc.firefox_browser, ec.new_policies)
        sys_dots(mountpoint, script_d)
        install_icons(installation)
        modify_mkinit(mountpoint, list(nc.mkinit_hooks), plymouth=True)
        if users:
            for user in users:
                installation.arch_chroot("xdg-user-dirs-update", user.username)
                enable_user_serv(installation, nc.user_services.services, user.username)
                enable_user_serv(installation, nc.user_services.services, user.username)
                hide_apps(installation, user.username, nc.apps_to_hide)
                user_service(installation, user, nc.terminal)
            user_1 = users[0].username
            mpd_tmpfiles(installation, users)
            configure_sudo(mountpoint, user_1, pless=True)
            cmd = f"paru -S --noconfirm --needed {' '.join(ec.aur_pkgs)}"
            installation.arch_chroot(cmd, user_1)
            cmd = "sudo passwd -dl root"
            installation.arch_chroot(cmd, user_1)
            cmd = "usermod --expiredate 1 root"
            installation.arch_chroot(cmd, user_1)
            configure_sudo(mountpoint, user_1)
            copy_dir(script_d, (mountpoint / f"home/{user_1}" / script_d.name))
            cmd = f"paru -S --noconfirm --needed {' '.join(ec.aur_pkgs)}"
            installation.arch_chroot(cmd, user_1)
            copy_keys(installation, user_1, nc.files_to_cp)
        if config.bootloader_config:
            if config.bootloader_config.bootloader == Bootloader.Systemd:
                if not config.bootloader_config.uki:
                    sysd_boot_params(mountpoint, plymouth=True, apparmor=True)

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


# def find_hd(conf_json: dict, preferred_device: str = "vda") -> dict:
#     lsblk = json.loads(
#         subprocess.check_output(["lsblk", "-J", "-b", "-o", "NAME,SIZE,LOG-SEC"])
#     )
#     for d in lsblk["blockdevices"]:
#         if d["name"] == preferred_device:
#             conf_json["disk_config"]["device_modifications"][0]["device"] = (
#                 f"/dev/{d['name']}"
#             )
#             conf_json["disk_config"]["device_modifications"][0]["partitions"][0][
#                 "obj_id"
#             ] = str(uuid.uuid4())
#             conf_json["disk_config"]["device_modifications"][0]["partitions"][0][
#                 "size"
#             ]["sector_size"]["value"] = int(d["log-sec"])
#             conf_json["disk_config"]["device_modifications"][0]["partitions"][0][
#                 "start"
#             ]["sector_size"]["value"] = int(d["log-sec"])
#             conf_json["disk_config"]["device_modifications"][0]["partitions"][1][
#                 "obj_id"
#             ] = str(uuid.uuid4())
#             conf_json["disk_config"]["device_modifications"][0]["partitions"][1][
#                 "size"
#             ]["sector_size"]["value"] = int(d["log-sec"])
#             conf_json["disk_config"]["device_modifications"][0]["partitions"][1][
#                 "size"
#             ]["value"] = int(d["size"]) - ((1 * 1024 * 1024) + (512 * 1024 * 1024))
#             conf_json["disk_config"]["device_modifications"][0]["partitions"][1][
#                 "start"
#             ]["sector_size"]["value"] = int(d["log-sec"])
#             conf_json["disk_config"]["device_modifications"][0]["partitions"][1][
#                 "start"
#             ]["value"] = (1 * 1024 * 1024) + (512 * 1024 * 1024)
#     # arch_config_json["disk_config"]["disk_encryption"]["partitions"] = [
#     #     arch_config_json["disk_config"]["device_modifications"][0]["partitions"][1][
#     #         "obj_id"
#     #     ]
#     # ]
#     return conf_json


def sys_setup() -> None:
    nc = NoahConfig.from_config(ec.json_config)
    mnt_cp_keys(nc.files_to_cp, nc.dir_contents_to_cp)
    with open("users.json", "r") as f:
        users_dict = json.load(f)
    # arch_json = find_hd(ec.arch_config_json)
    # print(arch_json)
    auth_arch_config = ArchConfig.from_config(users_dict, Arguments(None))
    arch_config = ArchConfig.from_config(ec.arch_config_json, Arguments(None))
    arch_config_handler = ArchConfigHandler()
    arch_config_handler.config.hostname = arch_config.hostname
    arch_config_handler.config.ntp = arch_config.ntp
    arch_config_handler.config.swap = arch_config.swap
    arch_config_handler.config.profile_config = arch_config.profile_config
    arch_config_handler.config.timezone = arch_config.timezone
    arch_config_handler.config.bootloader_config = arch_config.bootloader_config
    arch_config_handler.config.ntp = arch_config.ntp
    arch_config_handler.config.kernels = arch_config.kernels
    arch_config_handler.config.services = arch_config.services
    arch_config_handler.config.auth_config = auth_arch_config.auth_config
    arch_config_handler.config.app_config = arch_config.app_config
    gfx_drivers = get_gfx_drivers(_sys_info.graphics_devices)
    base_pkgs = ec.pkgs["base"] + ec.pkgs["language"] + ec.pkgs["chaotic_repo"]
    if GfxDriver.VMOpenSource not in gfx_drivers:
        base_pkgs.extend(ec.pkgs["extra"] + ec.pkgs["extra_chaos"])
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
        arch_config_handler=arch_config_handler,
        auth_handler=AuthenticationHandler(),
        application_handler=ApplicationHandler(),
        nc=nc,
        gfx_drivers=gfx_drivers,
    )


# if __name__ == "__main__":
#     sys_setup()
cmd = ["pacman-key", "--add", "chaotic.key"]
run_dmc(cmd)
