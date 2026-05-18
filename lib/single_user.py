from packages.aur import aur_pkgs
from lib.datahandler import NoahConfig
from archinstall.lib.models import User
from textwrap import dedent
from utils import log, write_etc_file, modify_mkinit, copy_dir, copy_file
from archinstall.lib.installer import Installer
from pathlib import Path


def aur_and_remove_root(
    installation: Installer,
    user_name: str,
    sudo_defaults: list[str],
    no_root: bool = True,
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
    if no_root:
        installation.arch_chroot("sudo passwd -dl root", user_name)
        no_root_ssh = {
            "etc/ssh/sshd_config.d/20-deny_root.conf": "PermitRootLogin no\n"
        }
        write_etc_file(installation.target, no_root_ssh)
    write_sudoers(False)


def inst_snapper(
    installation: Installer,
    username: str,
    snapper_subvolumes: dict[str, str] = {
        "root": "/",
        "home": "/home",
    },
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
    for config_name, mountpoint in snapper_subvolumes.items():
        installation.arch_chroot(
            f"snapper --no-dbus -c {config_name} create-config {mountpoint}"
        )
    installation.arch_chroot(
        f"snapper --no-dbus -c {config_name} set-config 'ALLOW_USERS={username}' SYNC_ACL='yes'"
    )
    installation.enable_service(["snapper-cleanup.timer", "snapper-timeline.timer"])
    modify_mkinit(installation.target, hook="btrfs-overlayfs", after="filesystems")


def create_automount(installation: Installer, username: str):
    etc_file = {
        "etc/polkit-1/rules.d/49-rules.rules": dedent(
            """\
            polkit.addRule(function(action, subject) {
                if (
                    subject.isInGroup("storage") &&
                    (
                        action.id == "org.freedesktop.udisks2.filesystem-mount" ||
                        action.id == "org.freedesktop.udisks2.filesystem-mount-system" ||
                        action.id == "org.freedesktop.udisks2.encrypted-unlock" ||
                        action.id == "org.freedesktop.udisks2.encrypted-unlock-system"
                    )
                ) {
                    return polkit.Result.YES;
                }
                if (
                    action.id === "org.kde.kpmcore.externalcommand.init" &&
                    subject.isInGroup("wheel")
                ) {
                    return polkit.Result.YES;
                }
            });
            """
        )
    }
    write_etc_file(installation.target, etc_file)
    installation.arch_chroot(f"usermod -aG storage {username}")


def auto_add_user_groups(
    installation: Installer,
    username: str,
    base_pkgs: list[str],
) -> None:
    pkg_groups = {
        "realtime-privileges": "realtime",
        "android-udev": "adbusers",
        "scrcpy": "adbusers",
        "gnome-logs": "adm",
    }
    groups = []
    for pkg, group in pkg_groups.items():
        if pkg in base_pkgs and group not in groups:
            groups.append(group)
    if not groups:
        return
    group_str = groups[0] if len(groups) == 1 else ",".join(groups)
    installation.arch_chroot(f"usermod -aG {group_str} {username}")


def copy_root_to_mnt(nc: NoahConfig, username: str):
    if key_conf := nc.key_copy_config:
        list_tuple_paths = key_conf.root_to_mnt(username)
        for src, dest in list_tuple_paths:
            copy_file(src, dest)
    if usb_file_conf := nc.additional_usb_to_cp_config:
        for copy in usb_file_conf.copies:
            for src, dest in copy.root_to_mnt(username):
                copy_file(src, dest)
    if usb_dir_conf := nc.dir_contents_to_cp_config:
        for copy in usb_dir_conf.copies:
            for src, dest in copy.root_to_mnt(username):
                copy_dir(src, dest)


def single_user_and_user_list(
    installation: Installer,
    users: list[User],
    nc: NoahConfig,
    script_d: Path,
    base_pkgs: list[str],
):
    user_1 = users[0].username
    inst_snapper(installation, user_1)
    aur_and_remove_root(installation, user_1, nc.sudo_defaults)
    auto_add_user_groups(installation, user_1, base_pkgs)
    create_automount(installation, user_1)
    copy_dir(script_d, (installation.target / "home" / user_1 / script_d.name))
    copy_root_to_mnt(nc, user_1)
