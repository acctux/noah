from archinstall.lib.models import User
from textwrap import dedent
from utils import log
from archinstall.lib.installer import Installer
from lib.datahandler import UserService, NoahConfig


def hide_apps(installation: Installer, user: str, apps_to_hide: list[str]):
    user_home = f"home/{user}"
    for app in apps_to_hide:
        file_p = f"{user_home}/.local/share/applications/{app}.desktop"
        (installation.target / file_p).write_text("[Desktop Entry]\nNoDisplay=true\n")
        installation.chown(user, f"/{file_p}")


###################################
# USR_SVC
###################################
def enable_user_serv(installation: Installer, unit: UserService, username: str) -> None:
    target_dirs = unit.target_paths(username)
    source_paths = unit.source_paths(username)
    for src, tgt in zip(source_paths, target_dirs):
        installation.arch_chroot(f"mkdir -p {tgt.parent}", username)
        installation.arch_chroot(f"ln -sfn {src} {tgt}", username)
        log.info("%s -> %s", src, tgt)


def user_service(
    installation: Installer,
    user: str,
    terminal: str,
    script_dir: str,
    user_script="user_setup.py",
) -> None:
    if terminal.strip().lower() == "kitty":
        terminal = "kitty --hold"
    if terminal.strip().lower() == "alacritty":
        terminal = "alacritty -e"
    run_script = f"/home/{user}/{script_dir}/{user_script}"
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
    unit = UserService(source=f"/{dir_path}", target="graphical-session", serv=[name])
    enable_user_serv(installation, unit, user)


def mpd_tmpfiles(installation: Installer, user: str) -> None:
    cache = f"home/{user}/.cache/"
    dir_path = installation.target / cache / "mpd/playlists"
    dir_path.mkdir(parents=True, exist_ok=True)
    dir_path.chmod(0o755)
    installation.arch_chroot(f"chown -R {user}:{user} /{cache}")


def multi_user_funcs(
    installation: Installer, user: User, nc: NoahConfig, script_dir: str
):
    installation.arch_chroot("xdg-user-dirs-update", user.username)
    hide_apps(installation, user.username, nc.apps_to_hide)
    user_service(installation, user.username, nc.terminal, script_dir)
    mpd_tmpfiles(installation, user.username)
    if serv_conf := nc.user_services_config:
        for user_serv in serv_conf.services:
            enable_user_serv(installation, user_serv, user.username)
    installation.arch_chroot(
        f"chown -R {user.username}:{user.username} /home/{user.username}"
    )
    installation.arch_chroot("chown -R root:root /usr/lib/systemd/user")
