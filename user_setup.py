from pathlib import Path
from utils import get_logger, run_cmd
from noah_user.usr_key_crypt import import_ssh_key, initialize_gocrypt, import_gpg_key
from noah_user.usr_dotsync import deploy_dotfiles
from noah_user.usr_bash_cmds import run_sudo_commands, enable_mariadb, run_interactive
from noah_user.usr_post import pass_and_input, launch_apps, cleanup
from noah_user.usr_app_dir import (
    ensure_github_known_hosts,
    install_icon_theme,
    set_folder_icons,
    hide_app_icons,
    clone_repos,
    setup_service,
)
from noah_conf.conf import (
    dots_dir,
    enc_dir,
    ssh_key,
    git_repos,
    git_user,
    gpg_key,
    custom_dir_icons,
    usb_key_dir,
    dirs_to_link,
    ind_dirs,
    hide_apps,
    pass_manager_pass,
)

log = get_logger("Noah")


# unmount
# virt machine version
def verify_install(HOME: Path, git_repos: list[tuple[Path, str]]):
    for path, repo in git_repos:
        repo_path = path / repo.capitalize()
        if not repo_path.exists() or not any(repo_path.iterdir()):
            log.error(f"Git repository {repo} is empty or missing: {repo_path}")
            return False
    if not (HOME / ".local/share/icons/WhiteSur-dark").exists():
        log.error("Icon folder 'WhiteSur-dark' not found.")
        return False
    nvim_config = HOME / ".config/nvim"
    if not nvim_config.exists() or not nvim_config.is_symlink():
        log.error(f"{nvim_config} is not a symlink.")
        return False
    return True


def main(
    ssh_key=ssh_key,
    enc_dir=enc_dir,
    custom_dir_icons=custom_dir_icons,
    git_repos=git_repos,
    git_user=git_user,
    hide_apps=hide_apps,
    dots_dir=dots_dir,
    dirs_to_link=dirs_to_link,
    ind_dirs=ind_dirs,
    pass_manager_pass=pass_manager_pass,
    usb_key_dir=usb_key_dir,
    HOME=Path.home(),
):
    script_dir = Path(__file__).resolve().parent.name
    gnupg_dir = HOME / ".gnupg"
    ssh_dir = HOME / ".ssh"
    cache_file = HOME / ".cache" / "first_done.txt"

    if not (HOME / ".cache" / cache_file).exists():
        run_interactive(["chsh", "-s", "/usr/bin/zsh"])
        run_sudo_commands()
        enable_mariadb()
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
        setup_service(script_dir)
        if not verify_install(HOME, git_repos):
            log.error("Installation verification failed. Cache file not updated.")
            return
        cleanup(HOME)
        cache_file.touch()
        if input("Do you want to reboot the system? [Y/n]: ").strip().lower() == "n":
            log.info("Reboot cancelled.")
            return
        run_cmd(["systemctl", "reboot"], True)
    else:
        pass_and_input(pass_manager_pass, (HOME / usb_key_dir))
        launch_apps()
        run_interactive(
            ["gh", "auth", "login", "-h", "github.com", "-s", "delete_repo"]
        )


if __name__ == "__main__":
    main()
