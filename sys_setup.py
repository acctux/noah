#!/usr/bin/env python3
from root_files import etc_files_to_write, new_policies
from pkgs import pacman_pkgs, aur_pkgs
from archinstall.default_profiles.profile import GreeterType
from archinstall.lib.authentication.authentication_handler import AuthenticationHandler
from archinstall.lib.applications.application_handler import ApplicationHandler
from archinstall.lib.hardware import _sys_info, GfxDriver
from archinstall.lib.args import ArchConfig, ArchConfigHandler, Arguments
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
from utils import run_dmc, log, NoahConfig, copy_file, copy_dir, write_etc_file
from lib.mnt_cp import mnt_cp_keys
from lib.bootloaders import install_limine, sysd_boot_params
from lib.apps import inst_plymouth, inst_snapper, inst_apparmor, realtime_priveleges
from lib.pacman import chaotic_repo, modify_pacman_conf
from lib.user_funcs import (
    user_service,
    enable_user_serv,
    copy_keys,
    copy_skel,
    install_icons,
    hide_apps,
    mpd_tmpfiles,
)
from typing import Any
from pathlib import Path
import sys
import time
import subprocess
import json
import shutil
import extraconfig as ec


###################################
# ETC/BOOT
###################################
def aur_and_remove_root(
    installation: Installer, user_name: str, sudo_defaults: list[str]
) -> None:
    def write_sudoers(pless: bool) -> None:
        defaults_block = "\n".join(f"Defaults    {line}" for line in sudo_defaults)
        rule = f"{user_name} ALL=(ALL:ALL) {'NOPASSWD:ALL' if pless else 'ALL'}"
        sudoers_block = "\n".join([rule, defaults_block])
        sudoers_file = installation.target / f"etc/sudoers.d/00_{user_name}"
        sudoers_file.write_text(sudoers_block)
        log.info(
            f"{'Removed' if pless else 'Created'} pass requirement for {user_name}"
        )

    write_sudoers(True)
    installation.arch_chroot(
        f"paru -S --noconfirm --needed {' '.join(aur_pkgs)}", user_name
    )
    installation.arch_chroot("sudo passwd -dl root", user_name)
    write_sudoers(False)


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


def handle_reflector(reflector_country: str):
    reflector_options = [
        f"--country {reflector_country}",
        "--protocol https",
        "--latest 15",
        "--sort rate",
        "--number 3",
        "--save /etc/pacman.d/mirrorlist",
    ]
    run_dmc(
        [
            "reflector",
            *(part for opt in reflector_options for part in opt.split()),
        ]
    )


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
    optional_repositories = (
        config.mirror_config.optional_repositories if config.mirror_config else []
    )
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

        handle_reflector(nc.reflector_country)

        modify_pacman_conf(None, no_extracts=nc.no_extracts)
        installation.minimal_installation(
            optional_repositories=optional_repositories,
            mkinitcpio=run_mkinitcpio,
            hostname=config.hostname,
            locale_config=locale,
            pacman_config=config.pacman_config,
        )
        copy_file(
            Path("/etc/pacman.d/mirrorlist"), mountpoint / "etc/pacman.d/mirrorlist"
        )
        copy_file(
            Path(f"/root/{nc.files_to_cp[0].target_dirs[1].dest}/chaotic.key"),
            mountpoint / "root/chaotic.key",
        )
        modify_pacman_conf(mountpoint, nc.no_extracts)
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
        write_etc_file(mountpoint, etc_files_to_write)
        (mountpoint / "etc/xdg/reflector/reflector.conf").write_text(
            "\n".join(nc.reflector_options)
        )
        for dir_to_cp in nc.dir_contents_to_cp:
            for name in dir_to_cp.dir_names:
                copy_dir(
                    Path("/root") / name, mountpoint / dir_to_cp.target_dir.lstrip("/")
                )
        inst_snapper(installation, config)
        set_extensions(mountpoint, nc.firefox_browser, new_policies)
        sys_dots(mountpoint, script_d)
        install_icons(installation)
        if users:
            for user in users:
                installation.arch_chroot("xdg-user-dirs-update", user.username)
                enable_user_serv(installation, nc.user_services.services, user.username)
                hide_apps(installation, user.username, nc.apps_to_hide)
                user_service(installation, user.username, nc.terminal)
                mpd_tmpfiles(installation, user.username)
            user_1 = users[0].username
            aur_and_remove_root(installation, user_1, nc.sudo_defaults)
            realtime_priveleges(installation, users)
            copy_dir(script_d, (mountpoint / "home" / user_1 / script_d.name))
            copy_keys(installation, user_1, nc.files_to_cp)
        if boot_config := config.bootloader_config:
            if boot_config.bootloader == Bootloader.Systemd:
                if not boot_config.uki:
                    sysd_boot_params(mountpoint, plymouth=True, apparmor=True)
            elif boot_config.bootloader == Bootloader.Limine:
                install_limine(installation)
                inst_apparmor(installation)
                inst_plymouth(installation)
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
        # modify_fstab(mountpoint)

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


def setup_archinstall_conf(
    arch_config_json: dict, auth_conf_path: str
) -> tuple[ArchConfigHandler, list[GfxDriver]]:
    arch_config_handler = ArchConfigHandler()
    with open(auth_conf_path, "r") as f:
        users_dict = json.load(f)
    auth_conf = ArchConfig.from_config(users_dict, Arguments(None))
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
    arch_config_handler.config.services = arch_config.services
    arch_config_handler.config.auth_config = auth_conf.auth_config
    arch_config_handler.config.app_config = arch_config.app_config
    gfx_drivers = get_gfx_drivers(_sys_info.graphics_devices)
    base_pkgs = (
        pacman_pkgs["base"] + pacman_pkgs["language"] + pacman_pkgs["chaotic_repo"]
    )
    if GfxDriver.VMOpenSource in gfx_drivers:
        base_pkgs.extend(["spice-vdagent", "qemu-guest-agent"])
    else:
        base_pkgs.extend(pacman_pkgs["extra"] + pacman_pkgs["extra_chaos"])
    arch_config_handler.config.packages = base_pkgs
    return arch_config_handler, gfx_drivers


def sys_setup() -> None:
    nc = NoahConfig.from_config(ec.json_config)
    mnt_cp_keys(nc.files_to_cp, nc.dir_contents_to_cp)
    arch_config_handler, gfx_drivers = setup_archinstall_conf(
        ec.arch_config_json, "/root/users.json"
    )
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


if __name__ == "__main__":
    sys_setup()
