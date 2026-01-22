import os
from pathlib import Path
import subprocess
import sys
import pyperclip
from utils import get_logger, run_cmd
from noah_conf.conf import (
    DOTS_DIR,
    ENC_DIR,
    HOME,
    GPG_DIR,
    SSH_DIR,
    ssh_key,
    GIT_REPOS,
    git_user,
    gpg_key,
    custom_dir_icons,
    dirs_to_link,
    ind_dirs,
    hide_apps,
    pass_manager_pass,
)
from noah_user.usr_key_crypt import import_ssh_key, import_gpg_key, initialize_gocrypt
from noah_user.usr_dotsync import deploy_dotfiles
from noah_user.usr_app_dir import (
    ensure_github_known_hosts,
    install_icon_theme,
    set_folder_icons,
    hide_app_icons,
    clone_repos,
)

# TODO investigate Ayugram vs Telegram dependencies
# cleanup service
# unmount
# virt machine version
CACHE_FILE = HOME / ".cache" / "first_done"
GPG_PATH = HOME / GPG_DIR / gpg_key
SSH_PATH = HOME / SSH_DIR / ssh_key
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
        "sudo systemctl restart iwd",
    ]
    for cmd in commands:
        result = run_cmd(cmd.split(), True)
        if result and result.returncode != 0:
            log.error(f"Command failed: {cmd}")


def setup_service(
    user_script: str = "user_setup.py", script_dir: str | None = None
) -> None:
    run_script = HOME / user_script
    if script_dir:
        run_script = HOME / script_dir / user_script
    service_name = f"{run_script.stem}.service"
    service_path = HOME / ".config" / "systemd" / "user" / service_name
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


def pass_and_input(password_file: str, pass_dir: Path):
    password = (pass_dir / password_file).read_text().strip()
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


def verify_install(git_repos: list[tuple[Path, str]]):
    for path, repo in git_repos:
        repo_path = path / repo.capitalize()
        if not repo_path.exists() or not any(repo_path.iterdir()):
            log.error(f"Git repository {repo} is empty or missing: {repo_path}")
            return False
    icon_folder = HOME / ".local/share/icons/WhiteSur-dark"
    if not icon_folder.exists():
        log.error("Icon folder 'WhiteSur-dark' not found.")
        return False
    nvim_config = HOME / ".config/nvim"
    if not nvim_config.exists():
        log.error("nvim config folder '~/.config/nvim' does not exist.")
        return False
    if not nvim_config.is_symlink():
        log.error("nvim config folder '~/.config/nvim' is not a symlink.")
        return False
    return True


def main():
    if not CACHE_FILE.exists():
        cmd = ["chsh", "-s", "/usr/bin/zsh"]
        run_interactive(cmd)
        run_sudo_commands()
        if SSH_PATH.exists():
            import_ssh_key(ssh_key)
        if GPG_PATH.exists():
            import_gpg_key(GPG_PATH)
        if not ENC_DIR.exists() and not len(list(ENC_DIR.iterdir())) > 0:
            initialize_gocrypt(ENC_DIR)
        if not not any((HOME / ".local/share/icons/WhiteSur-dark").rglob("*")):
            install_icon_theme()
        set_folder_icons(HOME, custom_dir_icons)
        ensure_github_known_hosts()
        for path, name in GIT_REPOS:
            repo_path = path / name.capitalize()
            if not repo_path.exists():
                clone_repos(git_user, repo_path, name)
        hide_app_icons(hide_apps)
        if DOTS_DIR.exists():
            deploy_dotfiles(DOTS_DIR, HOME, dirs_to_link, ind_dirs)
        setup_service(script_dir="archinstall")
        if verify_install(GIT_REPOS):
            CACHE_FILE.touch()
        else:
            log.error("Installation verification failed. Cache file not updated.")
            return
        if input("Do you want to reboot the system? [Y/n]: ").strip().lower() == "n":
            log.info("Reboot cancelled.")
        else:
            run_cmd(["systemctl", "reboot"], True)
    else:
        pass_and_input(pass_manager_pass, SSH_DIR)
        launch_apps()
        cmd = ["gh", "auth", "login", "-h", "github.com", "-s", "delete_repo"]
        run_interactive(cmd)


if __name__ == "__main__":
    main()
