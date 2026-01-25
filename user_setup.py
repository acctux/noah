import os
from pathlib import Path
import subprocess
import pyperclip
from utils import get_logger, run_cmd
from noah_user.usr_key_crypt import import_ssh_key, initialize_gocrypt
from noah_user.usr_dotsync import deploy_dotfiles
from noah_user.usr_bash_cmds import run_sudo_commands, enable_mariadb, run_interactive
from noah_user.usr_app_dir import (
    ensure_github_known_hosts,
    install_icon_theme,
    set_folder_icons,
    hide_app_icons,
    clone_repos,
)
from noah_conf.conf import (
    DOTS_DIR,
    ENC_DIR,
    HOME,
    ssh_key,
    GIT_REPOS,
    git_user,
    gpg_key,
    custom_dir_icons,
    usb_key_dir,
    dirs_to_link,
    ind_dirs,
    hide_apps,
    pass_manager_pass,
)

# cleanup service
# unmount
# virt machine version
# rm ~/archinstall ~/keys/pass.txt
log = get_logger("Noah")


def import_gpg_key(gpg_path: Path):
    proc = subprocess.run(
        ["gpg", "--import", str(gpg_path)],
        text=True,
    )
    if proc.returncode != 0:
        log.error(f"Failed to import GPG key from {gpg_path}.")
        return
    proc = subprocess.run(
        [
            "gpg",
            "--with-colons",
            "--import-options",
            "show-only",
            "--import",
            str(gpg_path),
        ],
        capture_output=True,
        text=True,
    )
    fingerprint = None
    for line in proc.stdout.splitlines():
        if line.startswith("fpr:"):
            fingerprint = line.split(":")[9]
            break
    if not fingerprint:
        log.error("Failed to determine GPG key fingerprint.")
        return
    log.info(f"GPG key imported: {fingerprint}")
    proc = subprocess.run(
        ["gpg", "--import-ownertrust"],
        input=f"{fingerprint}:6:\n",
        text=True,
    )
    if proc.returncode == 0:
        log.info(f"GPG key trusted (ultimate): {fingerprint}")
    else:
        log.error(f"Failed to set trust for GPG key: {fingerprint}")


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


def main(
    ssh_key=ssh_key,
    enc_dir=ENC_DIR,
    custom_dir_icons=custom_dir_icons,
    git_repos=GIT_REPOS,
    git_user=git_user,
    hide_apps=hide_apps,
    dots_dir=DOTS_DIR,
    dirs_to_link=dirs_to_link,
    ind_dirs=ind_dirs,
    pass_manager_pass=pass_manager_pass,
    usb_key_dir=usb_key_dir,
    gnupg_dir=HOME / ".gnupg",
    ssh_dir=HOME / ".ssh",
    cache_file=HOME / ".cache" / "first_done",
    HOME=Path.home(),
):
    if not (HOME / ".cache" / cache_file).exists():
        cmd = ["chsh", "-s", "/usr/bin/zsh"]
        run_interactive(cmd)
        run_sudo_commands()
        # enable_mariadb()
        if (ssh_dir / ssh_key).exists():
            import_ssh_key(ssh_key)
        if (gnupg_dir / gpg_key).exists():
            import_gpg_key(gnupg_dir / gpg_key)
        if not enc_dir.exists() or not any(enc_dir.iterdir()):
            initialize_gocrypt(enc_dir)
        check_dir = HOME / ".local/share/icons/WhiteSur-dark"
        if not check_dir.exists() or not any(check_dir.iterdir()):
            install_icon_theme()
        set_folder_icons(custom_dir_icons)
        ensure_github_known_hosts(HOME)
        for path, name in git_repos:
            repo_path = path / name.capitalize()
            if not any(repo_path.iterdir()):
                clone_repos(git_user, repo_path, name)
        hide_app_icons(hide_apps)
        if dots_dir.exists():
            deploy_dotfiles(dots_dir, dirs_to_link, ind_dirs)
        setup_service(script_dir="archinstall")
        if verify_install(git_repos):
            cache_file.touch()
        else:
            log.error("Installation verification failed. Cache file not updated.")
            return
        if input("Do you want to reboot the system? [Y/n]: ").strip().lower() == "n":
            log.info("Reboot cancelled.")
        else:
            run_cmd(["systemctl", "reboot"], True)
    else:
        pass_and_input(pass_manager_pass, (HOME / usb_key_dir))
        launch_apps()
        cmd = ["gh", "auth", "login", "-h", "github.com", "-s", "delete_repo"]
        run_interactive(cmd)


# if __name__ == "__main__":
# main()
import_gpg_key(HOME / ".gnupg" / gpg_key)
