from archinstall.lib.args import ArchConfig
from textwrap import dedent
from archinstall.lib.installer import Installer
from utils import write_etc_file, modify_mkinit
from lib.limine import write_limine_opt


def install_apparmor(installation: Installer):
    installation.add_additional_packages(["apparmor", "apparmor.d-git"])
    kernel_param = {"apparmor": "lsm=landlock,lockdown,yama,integrity,apparmor,bpf"}
    write_limine_opt(installation.target, kernel_param)
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
    write_limine_opt(installation.target, {"plymouth": "quiet splash"})
    modify_mkinit(installation.target, hook="plymouth", after="kms")


def install_snapper(installation: Installer, arch_config: ArchConfig):
    installation.add_additional_packages("limine-snapper-sync")
    installation.arch_chroot("snapper -c root create-config /")
    installation.arch_chroot("snapper -c home create-config /home")
    if arch_config.auth_config:
        if users := arch_config.auth_config.users:
            installation.arch_chroot(
                f"snapper -c home set-config 'ALLOW_USERS={users[0]}' SYNC_ACL='yes'"
            )
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
    installation.enable_service(["snapper-cleanup.timer", "snapper-timeline.timer"])
    modify_mkinit(installation.target, hook="btrfs-overlayfs", after="filesystems")
