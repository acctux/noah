from packages.aur import aur_pkgs
from lib.datahandler import NoahConfig, UserService, CopyConfiguration
from archinstall.lib.models import User
from textwrap import dedent
from utils import log, write_etc_file, copy_it
from archinstall.lib.installer import Installer
from pathlib import Path


###################################
# USR_SVC
###################################
def hide_apps(installation: Installer, user: str, apps_to_hide: list[str]):
    user_home = f"home/{user}"
    for app in apps_to_hide:
        file_p = f"{user_home}/.local/share/applications/{app}.desktop"
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
    user_setup_script_dir: str,
    user_script="user_setup.py",
) -> None:
    if terminal.strip().lower() == "kitty":
        terminal = "kitty --hold"
    if terminal.strip().lower() == "alacritty":
        terminal = "alacritty -e"
    run_script = f"/home/{user}/{user_setup_script_dir}/{user_script}"
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


def copy_root_to_mnt(
    installation: Installer, cc: CopyConfiguration, username: str
) -> None:
    if path_tuples := cc.resolve_root_to_mnt(
        mnt_point=installation.target,
        username=username,
    ):
        for src, target in path_tuples:
            dest = installation.target / target
            dest.parent.mkdir(parents=True, exist_ok=True)
            copy_it(src, dest)
            if ".ssh" in dest.parts or ".gnupg" in dest.parts:
                dest.chmod(0o600)
                dest.parent.chmod(0o700)
            elif "etc" in dest.parts and "wireguard" in dest.parts:
                if dest.is_dir():
                    dest.chmod(0o700)
                    for item in dest.iterdir():
                        if item.suffix == ".conf":
                            item.chmod(0o600)
                else:
                    dest.chmod(0o600)
                    dest.parent.chmod(0o700)


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
    user_1 = users[0].username
    aur_and_remove_root(installation, user_1, nc.sudo_defaults)
    create_automount(installation, users)
    for user in users:
        if nc.copy_config:
            copy_root_to_mnt(installation, nc.copy_config, user.username)
        auto_add_user_groups(installation, user.username, base_pkgs)
        copy_it(
            script_d, (installation.target / "home" / user.username / script_d.name)
        )
        installation.arch_chroot("xdg-user-dirs-update", user.username)
        if nc.apps_to_hide:
            hide_apps(installation, user.username, nc.apps_to_hide)
        user_service(installation, user.username, nc.terminal, str(script_d))
        mpd_tmpfiles(installation, user.username)
        if serv_conf := nc.user_services_config:
            if srvcs := serv_conf.services:
                for serv in srvcs:
                    enable_user_serv(installation, serv, user.username)
        installation.arch_chroot(
            f"chown -R {user.username}:{user.username} /home/{user.username}"
        )
    installation.arch_chroot("chown -R root:root /usr/lib/systemd/user")
