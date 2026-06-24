#!/usr/bin/env python3
from lib.noah_disk import noah_handle_fs
from lib.custom_apps import handle_cust_apps
from lib.noah_user_setup import noah_user_setup
from lib.app_and_profile import app_and_prof
from lib.min_install import min_intall_pre, min_install_post
from archinstall.lib.mirror.mirror_handler import MirrorListHandler
from archinstall.lib.translationhandler import tr
from archinstall.lib.packages.util import check_version_upgrade
from archinstall.lib.authentication.authentication_handler import AuthenticationHandler
from archinstall.lib.applications.application_handler import ApplicationHandler
from archinstall.lib.args import ArchConfig, ArchConfigHandler
from archinstall.lib.configuration import ConfigurationOutput
from archinstall.lib.disk.filesystem import FilesystemHandler
from archinstall.lib.disk.utils import disk_layouts
from archinstall.lib.general.general_menu import (
    PostInstallationAction,
    select_post_installation,
)
from archinstall.lib.global_menu import GlobalMenu
from archinstall.lib.installer import (
    Installer,
    run_custom_user_commands,
    accessibility_tools_in_use,
)
from archinstall.lib.menu.util import delayed_warning
from archinstall.lib.models import Bootloader
from archinstall.lib.models.device import DiskLayoutType, EncryptionType, SnapshotType
from archinstall.lib.models.users import User
from archinstall.lib.output import debug, error, info
from archinstall.tui.ui.components import tui
from archinstall.lib.network.network_handler import install_network_config
from archinstall.lib.profile.profiles_handler import profile_handler
from lib.init_setup import init_setup
from lib.datahandler import NoahConfig
from lib.bootloaders import bootloader_handling
from pathlib import Path
import sys
import time
import subprocess
import jsonconfig as json_conf


###################################
# Archinstall
###################################
def show_menu(arch_config_handler: ArchConfigHandler) -> None:
    upgrade = check_version_upgrade()
    title_text = "Archlinux"
    if upgrade:
        text = tr("New version available") + f": {upgrade}"
        title_text += f" ({text})"
    global_menu = GlobalMenu(arch_config_handler.config)
    global_menu.disable_all()
    global_menu.set_enabled("disk_config", True)
    global_menu.set_enabled("archinstall_language", True)
    global_menu.set_enabled("locale_config", True)
    global_menu.set_enabled("timezone", True)
    global_menu.set_enabled("bootloader_config", True)
    global_menu.set_enabled("ntp", True)
    global_menu.set_enabled("kernels", True)
    global_menu.set_enabled("profile_config", True)
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
    mirror_list_handler: MirrorListHandler,
    application_handler: ApplicationHandler,
    nc: NoahConfig,
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
    mountpoint = disk_config.mountpoint if disk_config.mountpoint else mountpoint
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

        min_intall_pre(nc)
        installation.minimal_installation(
            optional_repositories=optional_repositories,
            mkinitcpio=run_mkinitcpio,
            hostname=config.hostname,
            locale_config=locale,
            pacman_config=config.pacman_config,
        )
        min_install_post(installation, nc)

        if mirror_config := config.mirror_config:
            installation.set_mirrors(mirror_list_handler, mirror_config, on_target=True)

        if config.swap and config.swap.enabled:
            installation.setup_swap(algo=config.swap.algorithm)

        installation.add_bootloader(
            Bootloader.Limine,
            uki_enabled=False,
            bootloader_removable=False,
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

        if profile_config := config.profile_config:
            profile_handler.install_profile_config(installation, profile_config)

        if config.packages and config.packages[0] != "":
            installation.add_additional_packages(config.packages)

        if timezone := config.timezone:
            installation.set_timezone(timezone)

        if config.ntp:
            installation.activate_time_synchronization()

        if accessibility_tools_in_use():
            installation.enable_espeakup()

        if config.auth_config and config.auth_config.root_enc_password:
            root_user = User("root", config.auth_config.root_enc_password, False)
            installation.set_user_password(root_user)

        if (profile_config := config.profile_config) and profile_config.profile:
            profile_config.profile.post_install(installation)
            if users:
                profile_config.profile.provision(installation, users)

        if disk_config.has_default_btrfs_vols():
            btrfs_options = disk_config.btrfs_options
            if btrfs_options:
                installation.setup_btrfs_snapshot(
                    SnapshotType.Snapper, Bootloader.Limine
                )
        app_and_prof(installation, config)
        bootloader_handling(installation, config)
        handle_cust_apps(installation, nc, script_d)
        if users:
            noah_user_setup(installation, users, nc, script_d, config.packages)
        if services := config.services:
            installation.enable_service(services)
        if disable_svcs := nc.disable_svcs:
            installation.disable_service(disable_svcs)
        if mask_svcs := nc.disable_svcs:
            installation.arch_chroot(f"systemctl mask {' '.join(mask_svcs)}")
        noah_handle_fs(config, installation, users)
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


def main(arch_config_handler: ArchConfigHandler | None = None) -> None:
    if arch_config_handler is None:
        arch_config_handler = ArchConfigHandler()
    mirror_list_handler = MirrorListHandler(
        offline=arch_config_handler.args.offline,
        verbose=arch_config_handler.args.verbose,
    )
    arch_config_handler, nc = init_setup(
        arch_config_json=json_conf.archinstall_json,
        noahconf_json=json_conf.noah_json,
        arch_config_handler=arch_config_handler,
    )
    if not arch_config_handler.args.silent:
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
            return main(arch_config_handler)
    if arch_config_handler.config.disk_config:
        fs_handler = FilesystemHandler(arch_config_handler.config.disk_config)
        if not delayed_warning(tr("Starting device modifications in ")):
            return main()
        fs_handler.perform_filesystem_operations()
    perform_installation(
        arch_config_handler=arch_config_handler,
        mirror_list_handler=mirror_list_handler,
        auth_handler=AuthenticationHandler(),
        application_handler=ApplicationHandler(),
        nc=nc,
    )


if __name__ == "__main__":
    main()
