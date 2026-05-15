from textwrap import dedent
from archinstall.lib.installer import Installer
from utils import write_etc_file, modify_mkinit
from lib.limine import write_limine_opt


def install_apparmor(installation: Installer):
    installation.add_additional_packages(["apparmor", "apparmor.d-git"])
    write_limine_opt(
        installation.target,
        filename="apparmor",
        kernel_params="lsm=landlock,lockdown,yama,integrity,apparmor,bpf",
    )
    installation.enable_service("apparmor")
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


def install_plymouth(installation: Installer):
    installation.add_additional_packages("plymouth")
    write_limine_opt(
        installation.target,
        filename="plymouth",
        kernel_params="quiet splash",
    )
    modify_mkinit(installation.target, hook="plymouth", after="kms")


def install_snapper(installation: Installer):
    installation.add_additional_packages("limine-snapper-sync")
    write_etc_file(
        installation.target,
        {
            "etc/systemd/system/snapper-timeline.timer.d/15-snapper-timeline.conf": dedent(
                """\
                [Timer]
                OnCalendar=
                OnCalendar=*:0/15
                """
            ),
            "etc/systemd/system/snapper-cleanup.timer.d/20-snapper-cleanup.conf": dedent(
                """\
                [Timer]
                OnUnitActiveSec=1h
                """
            ),
        },
    )
    snapper: dict[str, str] = {
        "root": "/",
        "home": "/home",
    }
    for config_name, mountpoint in snapper.items():
        installation.arch_chroot(
            f"snapper --no-dbus -c {config_name} create-config {mountpoint}"
        )
    installation.enable_service(["snapper-cleanup.timer", "snapper-timeline.timer"])
    modify_mkinit(installation.target, hook="btrfs-overlayfs", after="filesystems")
