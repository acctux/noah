from archinstall.lib.models import User
from archinstall.lib.args import ArchConfig
from textwrap import dedent
from archinstall.lib.installer import Installer
from utils import write_etc_file, modify_mkinit
from lib.bootloaders import write_limine_opt


def inst_apparmor(installation: Installer):
    installation.add_additional_packages(["apparmor", "apparmor.d-git"])
    write_limine_opt(
        installation, "apparmor", "lsm=landlock,lockdown,yama,integrity,apparmor,bpf"
    )
    content = {
        "etc/apparmor/parser.conf": dedent(
            """\
            write-cache
            cache-loc /etc/apparmor/earlypolicy/
            Optimize=compress-fast
            """
        )
    }
    write_etc_file(installation.target, content)
    installation.enable_service("apparmor")


def inst_plymouth(installation: Installer):
    installation.add_additional_packages("plymouth")
    write_limine_opt(installation, filename="plymouth", kernel_params="quiet splash")
    modify_mkinit(installation.target, hook="plymouth", after="kms")


def realtime_priveleges(installation: Installer, users: list[User]):
    installation.add_additional_packages("realtime-privileges")
    for user in users:
        installation.arch_chroot(f"sudo usermod -aG realtime {user.username}")


def inst_snapper(
    installation: Installer,
    config: ArchConfig,
    snapper: dict[str, str] = {"root": "/", "home": "/home"},
):
    installation.add_additional_packages("limine-snapper-sync")
    write_etc_file(
        installation.target,
        {
            "etc/systemd/system/snapper-timeline.timer.d/15-timeline.conf": dedent(
                """\
                [Timer]
                OnCalendar=
                OnCalendar=*:0/15
                """
            ),
            "etc/systemd/system/snapper-cleanup.timer.d/20-cleanup.conf": dedent(
                """\
                [Timer]
                OnUnitActiveSec=1h
                """
            ),
        },
    )
    for config_name, mountpoint in snapper.items():
        installation.arch_chroot(
            f"snapper --no-dbus -c {config_name} create-config {mountpoint}"
        )
    if config.auth_config:
        if users := config.auth_config.users:
            installation.arch_chroot(
                f"snapper --no-dbus -c {config_name} set-config 'ALLOW_USERS={users[0].username}' SYNC_ACL='yes'"
            )
    installation.enable_service(["snapper-cleanup.timer", "snapper-timeline.timer"])
    modify_mkinit(installation.target, hook="btrfs-overlayfs", after="filesystems")
