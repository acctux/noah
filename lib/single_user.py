from packages.aur import aur_pkgs
from lib.datahandler import NoahConfig
from archinstall.lib.models import User
from textwrap import dedent
from utils import log, write_etc_file, copy_it
from archinstall.lib.installer import Installer
from pathlib import Path


def aur_and_remove_root(
    installation: Installer,
    user_name: str,
    sudo_default: list[str] | None = None,
) -> None:
    def write_sudoers(pword_require: str) -> None:
        write_data = [f"{user_name} ALL=(ALL:ALL) {pword_require}"]
        if sudo_default:
            write_data += "\n".join(f"Defaults    {line}" for line in sudo_default)
        sudoers_file = installation.target / f"etc/sudoers.d/00_{user_name}"
        sudoers_file.write_text("\n".join(write_data))

    write_sudoers("NOPASSWD:ALL")
    log.info(f"Removed pass requirement for {user_name}")
    installation.arch_chroot(
        cmd=f"paru -S --noconfirm --needed {' '.join(aur_pkgs)}",
        run_as=user_name,
    )
    installation.arch_chroot(
        cmd="sudo passwd -dl root",
        run_as=user_name,
    )
    write_etc_file(
        mnt_point=installation.target,
        files_to_write={
            "etc/ssh/sshd_config.d/20-deny_root.conf": "PermitRootLogin no\n"
        },
    )
    write_sudoers("ALL")
    log.info(f"Created pass requirement for {user_name}")


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


def copy_root_to_mnt(installation: Installer, nc: NoahConfig, username: str) -> None:
    if cc := nc.copy_config:
        if path_tuples := cc.resolve_root_to_mnt(
            mnt_point=installation.target,
            username=username,
        ):
            for src, dest in path_tuples:
                dest.parent.mkdir(parents=True, exist_ok=True)
                copy_it(src, dest)


def auto_add_user_groups(
    installation: Installer,
    username: str,
    base_pkgs: list[str],
    pkg_groups={
        "realtime-privileges": "realtime",
        "android-udev": "adbusers",
        "scrcpy": "adbusers",
        "gnome-logs": "adm",
    },
) -> None:
    groups = []
    for pkg, group in pkg_groups.items():
        if pkg in base_pkgs and group not in groups:
            groups.append(group)
    if not groups:
        return
    group_str = groups[0] if len(groups) == 1 else ",".join(groups)
    installation.arch_chroot(f"usermod -aG {group_str} {username}")


def single_user_and_user_list(
    installation: Installer,
    users: list[User],
    nc: NoahConfig,
    script_d: Path,
    base_pkgs: list[str],
):
    user_1 = users[0].username
    aur_and_remove_root(installation, user_1, nc.sudo_defaults)
    auto_add_user_groups(installation, user_1, base_pkgs)
    create_automount(installation, user_1)
    copy_it(script_d, (installation.target / "home" / user_1 / script_d.name))
    copy_root_to_mnt(installation, nc, user_1)
