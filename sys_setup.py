import subprocess
from pathlib import Path

from archinstall.lib.args import Password, User, arch_config_handler
from archinstall.lib.configuration import ConfigurationOutput
from archinstall.lib.disk.filesystem import FilesystemHandler
from archinstall.lib.global_menu import DiskLayoutConfigurationMenu
from archinstall.lib.installer import Bootloader, Installer
from archinstall.lib.interactions.general_conf import (
    PostInstallationAction,
    ask_post_installation,
)
from archinstall.lib.models.device import DiskLayoutType, EncryptionType
from archinstall.tui import Tui

import noah_conf.conf as nl
import noah_conf.pkg as pkg
from utils import run_cmd, get_logger

from noah_lib.sys_pac import chaotic_repo, config_pac_conf
from noah_lib.sys_etc import configure_sudo, modify_fstab, sys_dots
from noah_lib.sys_files import (
    copy_file_list,
    copy_scripts,
    enable_user_services,
    user_service,
    copy_dir,
)
from noah_lib.sys_functions import ensure_password, run_cc, modify_systemd
from noah_lib.usb_mnt_cp import mnt_cp_keys

script_dir = Path(__file__).resolve().parent
user_home = f"home/{nl.user_name}"
log = get_logger("Noah")


def perform_installation(mountpoint=Path("/mnt")) -> None:
    config = arch_config_handler.config
    if not config.disk_config:
        log.error("No disk configuration provided")
        return
    disk_config = config.disk_config

    with Installer(mountpoint, disk_config, [], ["linux"]) as installation:
        pw = ensure_password(nl.usb_key_dir, nl.key_files, nl.user_name)
        if disk_config.config_type != DiskLayoutType.Pre_mount:
            installation.mount_ordered_layout()
        installation.sanity_check()
        if disk_config.config_type != DiskLayoutType.Pre_mount:
            if (
                disk_config.disk_encryption
                and disk_config.disk_encryption.encryption_type
                != EncryptionType.NoEncryption
            ):
                installation.generate_key_files()

        installation.setup_swap()
        installation.minimal_installation([], True, nl.host, nl.my_locale)

        installation.add_additional_packages("reflector")
        ref_cmd = f"reflector {' '.join(nl.refl_opts)} --save /etc/pacman.d/mirrorlist"
        run_cc([ref_cmd], mountpoint)

        installation.add_bootloader(Bootloader.Systemd)
        modify_systemd(mountpoint)

        installation.copy_iso_network_config(enable_services=False)
        installation.set_timezone("US/Eastern")

        config_pac_conf(mountpoint)
        chaotic_repo(mountpoint)

        installation.add_additional_packages(pkg.pkgs)
        sys_dots(mountpoint, script_dir, nl.sys_cp)
        copy_dir(nl.wireguard_dir, mountpoint / "etc" / "wireguard", set_root=True)
        installation.enable_service(nl.sys_services)
        run_cc([f"systemctl disable {' '.join(nl.disable_svcs)}"], mountpoint)

        installation.create_users(User(nl.user_name, Password(pw), True, nl.groups))
        configure_sudo(nl.user_name, mountpoint, pwd_require=False)
        usr_cmd = ["xdg-user-dirs-update", f"mkdir -p /{user_home}/.cache/mpd"]
        run_cc(usr_cmd, mountpoint, nl.user_name)
        enable_user_services(user_home, nl.user_services, mountpoint, nl.user_name)

        copy_file_list(nl.key_files, nl.usb_key_dir, nl.HOME)
        copy_scripts(mountpoint, script_dir, "noah_lib", nl.user_name, nl.user_script)
        user_service(nl.user_script, mountpoint, nl.user_name, user_home)
        run_cc([f"chown -R {nl.user_name}:{nl.user_name} /{user_home}"], mountpoint)

        installation.genfstab()
        modify_fstab(mountpoint)

        if not arch_config_handler.args.silent:
            with Tui():
                action = ask_post_installation()
            match action:
                case PostInstallationAction.EXIT:
                    pass
                case PostInstallationAction.REBOOT:
                    subprocess.run(["reboot"], check=True)
                case PostInstallationAction.CHROOT:
                    try:
                        installation.drop_to_shell()
                    except Exception:
                        pass


def _minimal() -> None:
    with Tui():
        disk_config = DiskLayoutConfigurationMenu(disk_layout_config=None).run()
        arch_config_handler.config.disk_config = disk_config
    config = ConfigurationOutput(arch_config_handler.config)
    config.write_debug()
    config.save()
    if not arch_config_handler.args.silent:
        aborted = False
        with Tui():
            if not config.confirm_config():
                log.warning("Installation aborted")
                aborted = True
        if aborted:
            exit(0)
    if arch_config_handler.config.disk_config:
        fs_handler = FilesystemHandler(arch_config_handler.config.disk_config)
        fs_handler.perform_filesystem_operations()
    mnt_cp_keys(
        nl.min_usb_size, nl.usb_fs_type, nl.usb_key_dir, nl.key_files, nl.wireguard_dir
    )
    ref_cmd = ["reflector", *nl.refl_opts, "--save", "/etc/pacman.d/mirrorlist"]
    run_cmd(ref_cmd)
    config_pac_conf()
    chaotic_repo()
    perform_installation(Path("/mnt"))


_minimal()
