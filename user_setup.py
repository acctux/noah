#!/usr/bin/env python3
import getpass
import os
from pathlib import Path
import time
import gnupg
import re
import shutil
import subprocess
import pyperclip
import textwrap
from utils import get_logger, run_cmd, ping, ask_pass, UserGitRepo

log = get_logger("Noah")
###########################################################
# CONF
###########################################################
user_name = "nick"
ssh_key = "id_ed25519"
gpg_key = "my_sec_gpg.asc"
pass_manager_pass = "pass.txt"
git_user = "acctux"
git_dir = "Lit"
docs = "Docs"
desk = "Desktop"
games = "Games"
enc_dir = "Encrypted"
###########################################################
# GIT/DOT FILE
############################################################
HOME = Path.home()
CONFIG_DIR = HOME / ".config"
SHARE_DIR = HOME / ".local" / "share"
DOTS_P = HOME / "Lit" / "polka"
BASE = HOME / "Lit" / "Docs" / "base"
dots_dir = "polka"
git_repos = [UserGitRepo(target_dir=git_dir, repos=[docs, "noah", dots_dir])]
dirs_to_link = ["local/bin"]
ind_dirs = [
    ((BASE / "fonts"), (SHARE_DIR / "fonts")),
    ((BASE / "task"), (CONFIG_DIR / "task")),
    ((BASE / "zsh"), (CONFIG_DIR / "zsh")),
    ((BASE / "git"), (CONFIG_DIR / "git")),
    ((BASE / "gh"), (CONFIG_DIR / "gh")),
]
###########################################################
# ICONS
###########################################################
dirs_icons = [
    (f"{desk}/{games}", "folder-games"),
    (f"{desk}/{enc_dir}", "folder-locked"),
    (git_dir, "folder-github"),
    (f"{git_dir}/noah", "folder-root"),
    (f"{git_dir}/{docs}", "folder-bookmark"),
    (f"{git_dir}/{dots_dir}", "folder-html"),
]
###########################################################
# YAZI
###########################################################
yazi_plugins = [
    "yazi-rs/plugins:jump-to-char",
    "uhs-robert/sshfs",
    "boydaihungst/gvfs",
    "uhs-robert/recycle-bin",
    "h-hg/yamb",
]
firewall_services = ["kdeconnect", "ssh", "wireguard"]
firewall_ports = ["6881-6889/tcp", "6881-6889/udp"]


def cleanup(HOME: Path) -> None:
    for f in [(HOME / "keys" / "pass.txt")]:
        if f.exists():
            f.unlink()
    for d in [(HOME / "archinstall")]:
        if d.exists():
            shutil.rmtree(d)


def run(cmd, *, interactive=False, check=True, input_text=None):
    if interactive:
        return subprocess.Popen(cmd).wait()
    return subprocess.run(
        cmd, input=input_text, check=check, text=True, capture_output=True
    )


def iwctl_scan() -> None:
    result = run_cmd(["sudo", "iwctl", "station", "wlan0", "scan"], True)
    if result and result.returncode != 0:
        return
    time.sleep(10)


def run_firewall(firewall_services: list, firewall_ports: list):
    def fw_cmd(*args):
        return ["sudo", "firewall-cmd", "--permanent", "--zone=block"] + list(args)

    firewall_cmds = [
        ["sudo", "firewall-cmd", "--set-default-zone=block"],
        *[fw_cmd(f"--add-service={s}") for s in firewall_services],
        *[fw_cmd(f"--add-port={p}") for p in firewall_ports],
    ]
    for cmd in firewall_cmds:
        result = run_cmd(cmd, True)
        if result and result.returncode != 0:
            log.error(f"Firewall failed: {cmd}")


############################
# Dotfile Symlink
############################
def link_path(src: Path, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    rel = src.relative_to(dst.parent, walk_up=True)
    if dst.is_symlink() and dst.readlink() == rel:
        return False
    else:
        if dst.is_dir():
            shutil.rmtree(dst)
        dst.unlink(missing_ok=True)
    if dst.exists():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink(missing_ok=True)
        log.info(f"Removed: {dst}")
    dst.symlink_to(rel, target_is_directory=src.is_dir())
    log.info(f"Linked: {dst} → {rel}")
    return True


def dotted_destination(src: Path, source_dir: Path, target_dir: Path) -> Path:
    parts = src.relative_to(source_dir).parts
    return target_dir / Path("." + parts[0], *parts[1:])


def file_candidates(
    target_dir: Path,
    dotfiles_dir: Path,
    dirs_to_link: list[str],
    ind_dirs: list[tuple[Path, Path]],
):
    for src in dotfiles_dir.rglob("*"):
        if src.is_file():
            rel = src.relative_to(dotfiles_dir)
            if rel.parts[0] == ".git":
                continue
            if any(rel.is_relative_to(Path(d)) for d in dirs_to_link):
                continue
            yield src, dotted_destination(src, dotfiles_dir, target_dir)
    for d in dirs_to_link:
        src = dotfiles_dir / d
        if src.is_dir():
            yield src, dotted_destination(src, dotfiles_dir, target_dir)
    for src_dir, dst_dir in ind_dirs:
        if not src_dir.is_dir():
            continue
        for src in src_dir.rglob("*"):
            if src.is_file():
                yield src, dst_dir / src.relative_to(src_dir)


def deploy_dotfiles(
    HOME: Path,
    dot_dir: Path,
    dirs_to_link: list[str],
    ind_dirs: list[tuple[Path, Path]],
):
    if not dot_dir.is_dir():
        log.error(f"Dotfiles directory not found: {dot_dir}")
        return
    linked = 0
    for src, dst in file_candidates(HOME, dot_dir, dirs_to_link, ind_dirs):
        if link_path(src, dst):
            linked += 1
    if shutil.which("hyprctl"):
        subprocess.run(["hyprctl", "reload"], check=False)
        log.info("Hyprland reloaded")
    log.info(f"Linked: {linked}")


############################
# Encryption/Keys
############################
def import_ssh(key_file: str, key_dir=HOME / ".ssh") -> None:
    key_path = key_dir / key_file
    if key_path.exists():
        socket = f"/run/user/{os.getuid()}/gcr/ssh"
        os.environ["SSH_AUTH_SOCK"] = socket
        if not Path(socket).exists():
            run_cmd(["systemctl", "--user", "enable", "gcr-ssh-agent.socket"])
            run_cmd(["systemctl", "--user", "start", "gcr-ssh-agent.socket"])
        if run_cmd(["ssh-add", str(key_path)], check=True):
            log.info(f"SSH key {key_path} added or already present.")
        else:
            log.error(f"Failed to add SSH key {key_path}.")


def import_gpg(gpg_key: str, gpg_dir=HOME / ".gnupg") -> None:
    gpg_path = gpg_dir / gpg_key
    if gpg_path.exists():
        key_data = gpg_path.read_text()
        gpg = gnupg.GPG()
        import_result = gpg.import_keys(
            key_data, passphrase=ask_pass("GPG Password: ", False, 6)
        )
        print(import_result.results)


def init_gocrypt(enc_dir: Path) -> None:
    if not enc_dir.exists():
        enc_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"gocryptfs directory {enc_dir} created.")
    if not Path(enc_dir / "gocryptfs.conf").exists():
        while True:
            pw1 = getpass.getpass("Enter new gocryptfs password: ")
            pw2 = getpass.getpass("Confirm password: ")
            if pw1 == pw2 and pw1:
                break
            log.warning("Passwords do not match or empty. Try again.\n")
        cmd = ["gocryptfs", "-init", "--passfile", "/dev/stdin", str(enc_dir)]
        run_cmd(cmd, check=True, input_text=pw1)
        log.info(f"gocryptfs initialized at {enc_dir}.")


def setup_service(script_dir: str, script="user_setup.py") -> None:
    run_script = HOME / script_dir / script
    service_name = f"{run_script.stem}.service"
    service_path = HOME / ".config" / "systemd" / "user" / service_name
    svc_txt = textwrap.dedent(f"""\
        [Unit]
        Description=Open Alacritty running {script} on login
        After=graphical-session.target

        [Service]
        Type=oneshot
        ExecStart=/usr/bin/kitty python {run_script}
        Restart=no

        [Install]
        WantedBy=graphical-session.target
    """)
    service_path.write_text(svc_txt)
    run_cmd(["systemctl", "--user", "enable", service_name])


def enable_mariadb(user_name) -> None:
    while True:
        p1 = getpass.getpass("Mariadb password: ")
        p2 = getpass.getpass("Confirm: ")
        if p1 == p2:
            password = p1
            break
        print("Passwords do not match, try again.")
    commands = [
        [
            "sudo",
            "mariadb-install-db",
            "--user=mysql",
            "--basedir=/usr",
            "--datadir=/var/lib/mysql",
        ],
        ["sudo", "systemctl", "start", "mariadb"],
        [
            "sudo",
            "/usr/bin/mariadb",
            "-e",
            (
                f"CREATE USER '{user_name}'@'localhost' IDENTIFIED BY '{password}'; "
                f"GRANT ALL PRIVILEGES ON mydb.* TO '{user_name}'@'localhost'; "
                "FLUSH PRIVILEGES;"
            ),
        ],
    ]
    for cmd in commands:
        result = run_cmd(cmd, True)
        if result and result.returncode != 0:
            log.error(f"Command failed: {cmd}")


############################
# Git/Repos
############################
def ensure_github_known_hosts(kh=HOME / ".ssh" / "known_hosts") -> None:
    kh.parent.mkdir(parents=True, exist_ok=True)
    if not kh.exists():
        kh.touch()
    content = kh.read_text(errors="ignore")
    if "github.com" not in content:
        scan = run_cmd(["ssh-keyscan", "-H", "github.com"], check=True)
        if scan and scan.stdout:
            kh.write_text(content + scan.stdout)
            log.info("Added github.com to known_hosts")
        else:
            log.warning("Failed to scan github.com for known_hosts")


def fix_git_url(repo_path: Path, git_user: str, repo_name: str) -> None:
    config_path = repo_path / ".git" / "config"
    if config_path.exists():
        with open(config_path, "r") as config_file:
            config = config_file.read()
        match = re.search(r"url = (git@.*\.git|https://.*\.git)", config)
        if match:
            current_url = match.group(0).split("=")[1].strip()
            if "git@" not in current_url:
                new_url = f"git@github.com:{git_user}/{repo_name}.git"
                config = config.replace(current_url, new_url)
                with open(config_path, "w") as config_file:
                    config_file.write(config)
                log.info(f"Fixed URL in {repo_path}: {current_url} -> {new_url}")


def clone_repos(git_user: str, git_repo: UserGitRepo) -> None:
    base_path = Path(git_repo.target_dir)
    for name in git_repo.repos:
        repo_path = base_path / name
        if repo_path.exists() and any(repo_path.iterdir()):
            continue
        repo_path.mkdir(parents=True, exist_ok=True)
        git_str = f"git@github.com:{git_user}/{name}.git"
        if run_cmd(
            ["git", "clone", git_str, str(repo_path)],
            check=True,
        ):
            log.info(f"Cloned {name} into {repo_path}")
        else:
            log.warning(f"Failed to clone {name}.")
        fix_git_url(repo_path, git_user, name)


def configure_git() -> None:
    result = subprocess.run(["ssh-add", "-l"], capture_output=True, text=True)
    lines = result.stdout.strip().splitlines()
    if not lines:
        log.warning("No SSH keys found")
    parts = lines[0].split()
    if len(parts) < 3:
        log.warning("Unexpected ssh-add output format")
    my_email = parts[2]
    my_name = input("Enter your full real name (git): ").strip()
    if not my_name:
        raise ValueError("Name cannot be empty")
    run_cmd(["git", "config", "--global", "user.email", my_email])
    run_cmd(["git", "config", "--global", "user.name", my_name])
    print(f"Configured git with email={my_email} and name={my_name}")


############################
# Icons/Folders
############################
def set_folder_icons(
    custom_folder_icons: list[tuple[str, str]],
    icon_dir="/usr/share/icons/WhiteSur-dark/places/scalable",
) -> None:
    for folder, icon_name in custom_folder_icons:
        icon = f"{icon_dir}/{icon_name}.svg"
        dir_path = HOME / folder
        dir_path.mkdir(parents=True, exist_ok=True)
        if Path(icon).exists():
            icon_uri = f"file://{icon}"
            cmd = ["gio", "set", str(dir_path), "metadata::custom-icon", icon_uri]
            run_cmd(cmd, True)


############################
# Launch Apps
############################
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


def launch_apps(apps=["firedragon", "protonmail-bridge", "betterbird", "steam"]):
    processes = []
    for app in apps:
        processes.append(subprocess.Popen(app))
    for app, process in zip(apps, processes):
        process.wait()
        log.info(f"{app} closed")


def verify_install(git_repos: UserGitRepo):
    base_path = HOME / git_repos.target_dir
    for target in git_repos:
        for repo in target:
            repo_path = base_path / repo.capitalize()
            if not repo_path.exists() or not any(repo_path.iterdir()):
                log.error(f"Git repository {repo} is empty or missing: {repo_path}")
            return False
    if not Path("/usr/share/icons/WhiteSur-dark").exists():
        log.error("Icon folder 'WhiteSur-dark' not found.")
        return False
    nvim_config = HOME / ".config/nvim"
    if not nvim_config.exists() or not nvim_config.is_symlink():
        log.error(f"{nvim_config} is not a symlink.")
        return False
    return True


def uv_add():
    result = subprocess.run(
        ["uv", "add", "openmeteo-requests"],
        cwd=f"/home/{user_name}/Lit/polka/local/bin/weather",
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"uv add failed:\n{result.stderr}")
    return result.stdout


def scrcpy_setup(port=5555, timeout=3) -> None:
    answer = input("Is your Android phone connected? (Y/n): ").strip().lower()
    if answer not in ("y", "yes", ""):
        print("Please connect your device via USB first.")
        return
    ip = next(
        (
            line.split("src")[-1].strip()
            for line in subprocess.run(
                ["adb", "shell", "ip", "route"],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.splitlines()
            if "wlan" in line and "src" in line
        ),
        None,
    )
    if not ip:
        print("Could not determine device IP.")
        return
    target = f"{ip}:{port}"
    print(f"Trying {target}")
    msg = subprocess.run(
        ["adb", "connect", target],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    print((msg.stdout + msg.stderr).lower())


############################
# Main
############################
def main(HOME=Path.home()):
    cache_file = HOME / ".cache" / "noah_success.txt"
    enc_path = HOME / "Desktop" / enc_dir
    if not cache_file.exists():
        # run(["chsh", "-s", "/usr/bin/zsh"], interactive=True)
        # run_firewall(firewall_services, firewall_ports)
        # run(["sudo", "rm", "/etc/resolv.conf"])
        # run(["sudo", "resolvconf", "-u"])
        # run(["sudo", "systemctl", "restart", "iwd"])
        # run(["tuned-adm", "profile", "laptop-ac-powersave"])
        # time.sleep(3)
        # iwctl_scan()
        # if not ping:
        #     iwctl_scan()
        # enable_mariadb(user_name)
        # import_ssh(ssh_key)
        # import_gpg(gpg_key)
        # if not enc_path.exists() or not any(enc_path.iterdir()):
        #     init_gocrypt(enc_path)
        # set_folder_icons(dirs_icons)
        # configure_git()
        # ensure_github_known_hosts()
        # for target in git_repos:
        #     clone_repos(git_user, target)
        # for plugin in yazi_plugins:
        #     run_cmd(["ya", "pkg", "add", plugin])
        if any((DOTS_P).iterdir()):
            deploy_dotfiles(HOME, DOTS_P, dirs_to_link, ind_dirs)
        uv_add()
        scrcpy_setup()
        setup_service(Path(__file__).resolve().parent.name)
        for target in git_repos:
            if not verify_install(target):
                log.error("Verification failed. Cache not updated.")
                return
        cleanup(HOME)
        cache_file.touch()
        if input("Reboot now? [Y/n]: ").strip().lower() == "n":
            log.info("Reboot cancelled.")
            return
        run_cmd(["systemctl", "reboot"], True)
    else:
        pass_and_input(pass_manager_pass, (HOME))
        launch_apps()
        run(
            ["gh", "auth", "login", "-h", "github.com", "-s", "delete_repo"],
            interactive=True,
        )


if __name__ == "__main__":
    main()
