import os
from pathlib import Path
import subprocess
import sys
import pyperclip
from utils import get_logger, run_cmd
import conf as nl
from noah_lib.usb_mnt_cp import mnt_cp_keys
from noah_lib.usr_key_crypt import import_ssh_key, import_gpg_key, initialize_gocrypt
from noah_lib.usr_app_dir import (
    install_icon_theme,
    set_folder_icons,
    hide_app_icons,
    clone_repos,
)
from noah_lib.dotsync import deploy_dotfiles

CACHE_FILE = nl.HOME / ".cache" / "first_done"
log = get_logger("Noah")


def run_interactive(cmd: list[str], check: bool = True) -> int:
    log.info(f"Running (interactive): {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
        text=True,
    )
    returncode = proc.wait()
    if check and returncode != 0:
        raise subprocess.CalledProcessError(returncode, cmd)
    return returncode


def run_sudo_commands():
    commands = [
        "sudo mariadb-install-db --user=mysql --basedir=/usr --datadir=/var/lib/mysql",
        "sudo resolvconf -u",
        "sudo firewall-cmd --set-default-zone=block",
    ]
    for cmd in commands:
        result = run_cmd(cmd.split(), True)
        if result and result.returncode != 0:
            log.error(f"Command failed: {cmd}")


def setup_service(
    user_script: str = "d.py",
) -> None:
    run_script = nl.HOME / user_script
    service_dir = nl.HOME / ".config/systemd/user"
    service_name = f"{run_script.stem}.service"
    service_path = service_dir / service_name
    service_path.write_text(f"""[Unit]
Description=Open Alacritty running {user_script} on login
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/usr/bin/alacritty -e python {run_script}
Restart=no

[Install]
WantedBy=graphical-session.target
""")
    run_cmd(["systemctl", "--user", "enable", service_name])


def pass_and_input(password_file):
    password = password_file.read_text().strip()
    os.environ["CLIPBOARD_STATE"] = "sensitive"
    pyperclip.copy(password)
    log.info("Password copied to clipboard.")
    cmd = ["firedragon", "https://addons.mozilla.org/en-US/firefox/addon/proton-pass/"]
    subprocess.Popen(cmd).wait()
    pyperclip.copy("")
    log.info("Clipboard cleared.")
    os.environ.pop("CLIPBOARD_STATE", None)


def launch_apps():
    apps = ["firedragon", "protonmail-bridge", "betterbird", "steam"]
    processes = []
    for app in apps:
        processes.append(subprocess.Popen(app))
    for app, process in zip(apps, processes):
        process.wait()
        log.info(f"{app} closed")


def main():
    if not CACHE_FILE.exists():
        mnt_cp_keys(
            nl.min_usb_size,
            nl.usb_fs_type,
            nl.usb_key_dir,
            nl.key_files,
            nl.wireguard_dir,
        )
        cmd = ["chsh", "-s", "/usr/bin/zsh"]
        run_interactive(cmd)
        run_sudo_commands()
        if nl.ssh_key.exists():
            import_ssh_key(nl.ssh_key)
        if Path(nl.gpg_key).exists():
            import_gpg_key(nl.gpg_key)
        initialize_gocrypt(nl.enc_dir)
        if not (nl.HOME / ".local/share/icons/WhiteSur-dark").exists():
            install_icon_theme()
        set_folder_icons(nl.HOME, nl.dir_icons)
        clone_repos(nl.git_user, nl.git_repos, nl.ssh_dir)
        hide_app_icons(nl.hide_apps)
        deploy_dotfiles(nl.dots_dir, nl.HOME, nl.dirs_to_link, nl.ind_dirs)
        setup_service()
        CACHE_FILE.touch()
        if input("Do you want to reboot the system? [Y/n]: ").strip().lower() == "n":
            log.info("Reboot cancelled.")
        else:
            run_cmd(["systemctl", "reboot"], True)
    else:
        pass_and_input(nl.HOME / nl.ssh_dir / f"{nl.key_files[2]}")
        launch_apps()
        cmd = ["gh", "auth", "login", "-h", "github.com", "-s", "delete_repo"]
        run_interactive(cmd)


if __name__ == "__main__":
    main()
