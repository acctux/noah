import subprocess
from pathlib import Path
from archinstall.lib.configuration import ConfigurationOutput
from archinstall.lib.disk.filesystem import FilesystemHandler
from archinstall.lib.global_menu import DiskLayoutConfigurationMenu
from archinstall.lib.installer import Bootloader, Installer
from archinstall.lib.models.device import DiskLayoutType, EncryptionType
from archinstall.tui import Tui
from utils import run_cmd, get_logger
from archinstall.lib.interactions.general_conf import (
    PostInstallationAction,
    ask_post_installation,
)
from archinstall.lib.args import (
    LocaleConfiguration,
    Password,
    User,
    arch_config_handler,
)
from noah_conf.pkg import pkgs
from noah_lib.sys_pac import chaotic_repo, config_pac_conf
from noah_lib.sys_etc import configure_sudo, modify_fstab, modify_mkinit, sys_dots
from noah_lib.sys_files import copy_file_list, user_service, copy_dir
from noah_lib.sys_functions import src_pass_file, type_password, run_cc, modify_systemd
from noah_lib.usb_mnt_cp import mnt_cp_keys
from noah_conf.conf import (
    usb_key_dir,
    user_name,
    usb_cp_files,
    hostname,
    refl_options,
    mkinit_hooks,
    wireguard_dir,
    sys_services,
    sys_dir_to_cp,
    disable_svcs,
    pass_manager_pass,
    groups,
    min_usb_size,
    usb_fs_type,
)

###########################################################
# CONSTANTS
###########################################################
script_dir = Path(__file__).resolve().parent
user_home = f"home/{user_name}"
log = get_logger("Noah")


###########################################################
# Installer
###########################################################
def perform_installation(mountpoint=Path("/mnt")) -> None:
    config = arch_config_handler.config
    if not config.disk_config:
        log.error("No disk configuration provided")
        return
    disk_config = config.disk_config

    with Installer(mountpoint, disk_config, [], ["linux"]) as installation:
        ############-Ensure User Pass Exists-##########
        if pw := src_pass_file(usb_key_dir, pass_manager_pass, user_name):
            log.info("Password Sourced")
        else:
            pw = type_password(user_name)

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
        installation.minimal_installation(
            [], True, hostname, LocaleConfiguration("us", "en_US", "UTF-8")
        )

        ###############-Install reflector-###############
        installation.add_additional_packages("reflector")
        cmd = f"reflector {' '.join(refl_options)} --save /etc/pacman.d/mirrorlist"
        ref_cmd = cmd
        log.info("Running reflector to update mirror list.")
        run_cc([ref_cmd], mountpoint)

        ####################-System D-####################
        installation.add_bootloader(Bootloader.Systemd)
        modify_systemd(mountpoint)

        ###########-WiFi Pass and Time Zone-############
        installation.copy_iso_network_config()
        installation.set_timezone("US/Eastern")

        #############-Pkg Management-###############
        config_pac_conf(mountpoint)
        chaotic_repo(mountpoint)
        installation.add_additional_packages(pkgs)

        #############-Etc Management-###############
        modify_mkinit(mountpoint, mkinit_hooks)
        sys_dots(mountpoint, script_dir, sys_dir_to_cp)
        copy_dir(wireguard_dir, mountpoint / "etc" / "wireguard", set_root=True)
        installation.enable_service(sys_services)
        run_cc([f"systemctl disable {' '.join(disable_svcs)}"], mountpoint)

        #############-User and Sudo-###############
        installation.create_users(User(user_name, Password(pw), True, groups))
        configure_sudo(user_name, mountpoint, pwd_require=False)
        usr_cmd = ["xdg-user-dirs-update", f"mkdir -p /{user_home}/.cache/mpd"]
        run_cc(usr_cmd, mountpoint, user_name)

        #############-CP Files to User Home-###############
        copy_file_list(user_name, mountpoint, usb_cp_files, usb_key_dir)
        copy_dir(str(script_dir), (mountpoint / user_home / script_dir.name))

        #############-Own Everything-###############
        run_cc([f"chown -R {user_name}:{user_name} /{user_home}"], mountpoint)
        user_service(script_dir.name, mountpoint, user_name, user_home)

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
        min_usb_size,
        usb_fs_type,
        usb_key_dir,
        usb_cp_files,
        wireguard_dir,
    )
    ref_cmd = ["reflector", *refl_options, "--save", "/etc/pacman.d/mirrorlist"]
    run_cmd(ref_cmd)
    config_pac_conf()
    chaotic_repo()
    perform_installation(Path("/mnt"))


_minimal()
