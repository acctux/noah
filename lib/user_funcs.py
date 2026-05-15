from textwrap import dedent
from utils import run_dmc, copy_dir, copy_file, log
import shutil
from archinstall.lib.installer import Installer
from lib.datahandler import NoahConfig, CopyProcessor, UsrSrv
from pathlib import Path


def hide_apps(installation: Installer, user: str, apps_to_hide: list[str]):
    user_home = f"home/{user}"
    for app in apps_to_hide:
        file_p = f"{user_home}/.local/share/applications/{app}.desktop"
        (installation.target / file_p).write_text("[Desktop Entry]\nNoDisplay=true\n")
        installation.chown(user, f"/{file_p}")


def copy_skel(mountpoint: Path, nc: NoahConfig):
    tmp = mountpoint / "tmp" / nc.dots_repo
    tmp.mkdir(exist_ok=True)
    git = f"https://github.com/{nc.git_user}/{nc.dots_repo}.git"
    run_dmc(["git", "clone", git, str(tmp)])
    shutil.rmtree(tmp / ".git")
    for p in tmp.iterdir():
        p.rename(p.parent / ("." + p.name))
    copy_dir(tmp, mountpoint / "etc" / "skel")


###################################
# USR_SVC
###################################
def enable_user_serv(
    installation: Installer, units: list[UsrSrv], username: str
) -> None:
    home = Path(f"/home/{username}")
    for unit in units:
        source_dir = Path(unit.source)
        if unit.source == "/.config/systemd/user":
            source_dir = home / ".config/systemd/user"
        for service in unit.services:
            target_dir = home / ".config/systemd/user" / f"{unit.target}.target.wants"
            source_path = source_dir / service
            installation.arch_chroot(f"mkdir -p {target_dir}", username)
            link_path = installation.target / target_dir.relative_to("/") / service
            if not link_path.exists():
                installation.arch_chroot(
                    f"ln -sf {source_path} {target_dir}/{service}", username
                )
                log.info(f"{source_path} -> {target_dir}/{service}")


def user_service(
    installation: Installer,
    user: str,
    terminal: str,
    user_script="user_setup.py",
    script_dir: str = Path(__file__).resolve().parent.name,
) -> None:
    if terminal.strip().lower() == "alacritty":
        terminal = "alacritty -e"
    dir_path = f"home/{user}/.config/systemd/user"
    run_script = f"/home/{user}/{script_dir}/{user_script}"
    name = f"{user_script.rsplit('.', 1)[0]}.service"
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
    (installation.target / dir_path / name).write_text(content)
    installation.arch_chroot(f"chown {user}:{user} /{dir_path}/{name}")
    unit = UsrSrv(source=f"/{dir_path}", target="graphical-session", services=[name])
    enable_user_serv(installation, [unit], user)


def install_icons(installation: Installer):
    git = "https://github.com/vinceliuice/WhiteSur-icon-theme.git"
    installation.arch_chroot(f"git clone {git}")
    installation.arch_chroot("bash ./WhiteSur-icon-theme/install.sh")
    installation.arch_chroot("rm -rf ./WhiteSur-icon-theme")
    icon_path = installation.target / "usr/share/icons"
    white_sur_light = icon_path / "WhiteSur-light"
    if white_sur_light.exists():
        shutil.rmtree(white_sur_light)
        log.info(f"Removed {white_sur_light}")
    themes_to_modify = []
    for folder in icon_path.iterdir():
        if folder.is_dir() and ("-dark" in folder.name or "WhiteSur" in folder.name):
            themes_to_modify.append(folder)
    for theme_dir in themes_to_modify:
        for svg_file in theme_dir.rglob("*.svg"):
            if svg_file.is_file():
                text = svg_file.read_text()
                if "#ffffff" in text:
                    svg_file.write_text(text.replace("#ffffff", "#F4F5F6"))
                    log.info(f"Modified {svg_file}")


###################################
# User Space
###################################
def copy_all_usb(processor: CopyProcessor, installer: "Installer", username: str):
    key_paths = set(processor.file_home_paths(username))

    def apply_permissions(dest: Path, home: bool):
        if not home:
            return
        if dest in key_paths:
            dest.chmod(0o600 if dest.is_file() else 0o700)
        else:
            dest.chmod(0o644 if dest.is_file() else 0o755)
        installer.chown(username, str(dest))

    def copy_item(src: Path, dest: Path, home: bool):
        if src.is_file():
            copy_file(src, dest)
        elif src.is_dir():
            copy_dir(src, dest)
        apply_permissions(dest, home)

    # ------------------- (root-owned) -------------------
    for src, dest in zip(processor.usb_paths(), processor.file_chroot_paths()):
        copy_item(src, dest, home=False)
    for src, dest in zip(processor.dir_usb_paths(), processor.dir_chroot_paths()):
        copy_item(src, dest, home=False)
    # ------------------- (user-owned) -------------------
    for src, dest in zip(processor.usb_paths(), processor.file_home_paths(username)):
        copy_item(src, dest, home=True)
    for src, dest in zip(processor.dir_usb_paths(), processor.dir_home_paths(username)):
        copy_item(src, dest, home=True)


def mpd_tmpfiles(installation: Installer, user: str) -> None:
    cache = f"home/{user}/.cache/"
    dir_path = installation.target / cache / "mpd/playlists"
    dir_path.mkdir(parents=True, exist_ok=True)
    dir_path.chmod(0o755)
    installation.arch_chroot(f"chown -R {user}:{user} /{cache}")
