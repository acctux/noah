from packages.aur import aur_pkgs
from lib.datahandler import NoahConfig, UserService
from archinstall.lib.models import User
from textwrap import dedent
from utils import log, write_etc_file, copy_it
from archinstall.lib.installer import Installer
from pathlib import Path


###################################
# USR_SVC
###################################
def hide_apps(installation: Installer, user: str, apps_to_hide: list[str]):
    for app in apps_to_hide:
        file_p = f"home/{user}/.local/share/applications/{app}.desktop"
        (installation.target / file_p).write_text("[Desktop Entry]\nNoDisplay=true\n")
        installation.chown(user, f"/{file_p}")


def create_automount(installation: Installer, users: list[User]):
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
    for user in users:
        installation.arch_chroot(f"usermod -aG storage {user.username}")


def enable_user_serv(installation: Installer, unit: UserService, username: str) -> None:
    sources = unit.get_source_paths(username)
    targets = unit.get_target_paths(username)
    for src, tgt in zip(sources, targets):
        installation.arch_chroot(f"mkdir -p {tgt.parent}", username)
        installation.arch_chroot(f"ln -sfn {src} {tgt}", username)
        log.info("Enabled service: %s -> %s", src, tgt)


def user_service(
    installation: Installer,
    user: str,
    terminal: str,
    current_script_dir: Path,
    user_script="user_setup.py",
) -> None:
    if terminal.strip().lower() == "kitty":
        terminal = "kitty --hold"
    if terminal.strip().lower() == "alacritty":
        terminal = "alacritty -e"
    user_script_dir = f"home/{user}/{current_script_dir.name}"
    run_script = f"/{user_script_dir}/{user_script}"
    content = dedent(
        f"""\
        [Unit]
        Description=Open {terminal} {run_script} on login
        After=graphical-session.target

        [Service]
        Type=oneshot
        ExecStartPre=/usr/bin/sleep 5
        ExecStart=/usr/bin/{terminal} python {run_script}
        Restart=no

        [Install]
        WantedBy=graphical-session.target
        """
    )
    dir_path = f"home/{user}/.config/systemd/user"
    name = f"{user_script.rsplit('.', 1)[0]}.service"
    copy_it(current_script_dir, (installation.target / user_script_dir))
    (installation.target / dir_path / name).write_text(content)
    installation.arch_chroot(f"chown {user}:{user} /{dir_path}/{name}")
    unit = UserService(
        source=f"/{dir_path}",
        target="graphical-session",
        services=[name],
    )
    enable_user_serv(installation, unit, user)


def mpd_tmpfiles(installation: Installer, user: str) -> None:
    cache = f"home/{user}/.cache/"
    dir_path = installation.target / cache / "mpd/playlists"
    dir_path.mkdir(parents=True, exist_ok=True)
    dir_path.chmod(0o755)
    installation.arch_chroot(f"chown -R {user}:{user} /{cache}")


###################################
# USR_SVC
###################################
def aur_and_remove_root(
    installation: Installer,
    users: list[User],
    sudo_default: list[str] | None = None,
) -> None:
    def write_sudoers(pword_require: str, user_name: str) -> None:
        write_data = [f"{user_name} ALL=(ALL:ALL) {pword_require}"]
        if sudo_default:
            write_data += "\n".join(f"Defaults    {line}" for line in sudo_default)
        sudoers_file = installation.target / f"etc/sudoers.d/00_{user_name}"
        sudoers_file.write_text("\n".join(write_data))

    def find_sudo_user() -> str | None:
        for user in users:
            if user.sudo:
                sudo_user = user.username
            for g in user.groups:
                if g == "wheel":
                    sudo_user = user.username
        return sudo_user

    sudo_user = find_sudo_user()
    if sudo_user:
        write_sudoers("NOPASSWD:ALL", sudo_user)
        log.info(f"Removed pass requirement for {sudo_user}")
        installation.arch_chroot(
            cmd=f"paru -S --noconfirm --needed {' '.join(aur_pkgs)}",
            run_as=sudo_user,
        )
        installation.arch_chroot(cmd="sudo passwd -dl root", run_as=sudo_user)
        write_etc_file(
            mnt_point=installation.target,
            files_to_write={
                "etc/ssh/sshd_config.d/20-deny_root.conf": "PermitRootLogin no\n"
            },
        )
        write_sudoers("ALL", sudo_user)
        log.info(f"Created pass requirement for {sudo_user}")


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


def noah_user_setup(
    installation: Installer,
    users: list[User],
    nc: NoahConfig,
    script_d: Path,
    base_pkgs: list[str],
):
    aur_and_remove_root(installation, users, nc.sudo_defaults)
    create_automount(installation, users)
    for user in users:
        if nc.copy_config:
            nc.copy_config.copy_root_to_mnt(installation.target, user.username)
        auto_add_user_groups(installation, user.username, base_pkgs)
        installation.arch_chroot("xdg-user-dirs-update", user.username)
        if nc.apps_to_hide:
            hide_apps(installation, user.username, nc.apps_to_hide)
        user_service(installation, user.username, nc.terminal, script_d)
        mpd_tmpfiles(installation, user.username)
        if serv_conf := nc.user_services_config:
            if srvcs := serv_conf.services:
                for serv in srvcs:
                    enable_user_serv(installation, serv, user.username)
        installation.arch_chroot(
            f"chown -R {user.username}:{user.username} /home/{user.username}"
        )
    installation.arch_chroot("chown -R root:root /usr/lib/systemd/user")
