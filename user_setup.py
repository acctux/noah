import os
import subprocess
import sys
import pyperclip
from utils import get_logger, run_cmd
import noah_conf.conf as nl
import noah_conf.dot_conf as dc
from noah_user.usr_key_crypt import import_ssh_key, import_gpg_key, initialize_gocrypt
from noah_user.usr_dotsync import deploy_dotfiles
from noah_user.usr_app_dir import (
    install_icon_theme,
    set_folder_icons,
    hide_app_icons,
    clone_repos,
)

# TODO investigate Ayugram vs Telegram dependencies
# cleanup service
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
        "sudo rm /etc/resolv.conf",
        "sudo resolvconf -u",
        "sudo firewall-cmd --set-default-zone=block",
        "paru -R telegram-desktop",
    ]
    for cmd in commands:
        result = run_cmd(cmd.split(), True)
        if result and result.returncode != 0:
            log.error(f"Command failed: {cmd}")


def setup_service(user_script: str) -> None:
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


def verify_install():
    for path, repo in nl.git_repos:
        repo_path = path / repo
        if not repo_path.exists() or len(list(repo_path.iterdir())) == 0:
            log.error(f"Git repository {repo} is empty or missing.")
            return False
    icon_folder = nl.HOME / ".local/share/icons/WhiteSur-dark"
    if not icon_folder.exists():
        log.error("Icon folder 'WhiteSur-dark' not found.")
        return False
    return True


def main():
    if not CACHE_FILE.exists():
        cmd = ["chsh", "-s", "/usr/bin/zsh"]
        run_interactive(cmd)
        run_sudo_commands()
        import_ssh_key(nl.ssh_key)
        import_gpg_key(nl.gpg_key)
        initialize_gocrypt(nl.enc_dir)
        if not (nl.HOME / ".local/share/icons/WhiteSur-dark").exists():
            install_icon_theme()
        set_folder_icons(nl.HOME, nl.dir_icons)
        clone_repos(nl.git_user, nl.git_repos, nl.ssh_dir)
        hide_app_icons(nl.hide_apps)
        deploy_dotfiles(dc.dots_dir, dc.HOME, dc.dirs_to_link, dc.ind_dirs)
        setup_service(nl.user_script)
        if verify_install():
            CACHE_FILE.touch()
        else:
            log.error("Installation verification failed. Cache file not updated.")
            return
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
