#!/usr/bin/env python3
import getpass
import os
from pathlib import Path
import time
import gnupg
import shutil
import subprocess
import pyperclip
from utils import log, ping, ask_pass, yes_no, run

###########################################################
# CONF
###########################################################
user_name = "nick"
git_user = "acctux"
android = True
firewalld = True
firefox_browser = "floorp"
###########################################################
# GIT/DOT FILE
############################################################
HOME = Path.home()
ssh_path = HOME / ".ssh" / "id_ed25519"
gpg_path = HOME / ".gnupg" / "my_sec_gpg.asc"
masterpass_path = HOME / "scripts" / "pass.txt"
DESKTOP = HOME / "Desktop"
ENCRYPTED = DESKTOP / "Encrypted"
GIT_DIR = HOME / "Lit"
dots_path = GIT_DIR / "polka"
DOCS = GIT_DIR / "Docs"
repos = ["noah", "polka"]
private_repos = ["Docs"]
dirs_to_link = ["local/bin"]
secret_dots = DOCS / "base"
ind_dirs = [
    ("fonts", (HOME / ".local" / "share")),
    ("task", (HOME / ".config")),
    ("zsh", (HOME / ".config")),
    ("git", (HOME / ".config")),
    ("gh", (HOME / ".config")),
]
###########################################################
# ICONS
###########################################################
dirs_icons = [
    (DESKTOP / "Games", "folder-games"),
    (ENCRYPTED, "folder-locked"),
    (GIT_DIR, "folder-github"),
    (GIT_DIR / "noah", "folder-root"),
    (DOCS, "folder-bookmark"),
    (dots_path, "folder-html"),
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


def iwctl_scan() -> bool:
    result = run(["sudo", "iwctl", "station", "wlan0", "scan"], check=False)
    time.sleep(10)
    if result.returncode == 0:
        return True
    return False


############################
# Dotfile Symlink
############################
def deploy_dotfiles(
    HOME: Path,
    dot_dir: Path,
    dirs_to_link: list[str],
    ind_dirs: list[tuple[str, Path]],
    sec_dots_dir: Path,
):
    def link_path(src: Path, dst: Path) -> bool:
        dst.parent.mkdir(parents=True, exist_ok=True)
        rel = src.relative_to(dst.parent, walk_up=True)
        if dst.is_symlink() and dst.readlink() == rel:
            return False
        if dst.exists():
            if dst.is_dir() and not dst.is_symlink():
                shutil.rmtree(dst)
            else:
                dst.unlink(missing_ok=True)
            log.info(f"Removed: {dst}")
        dst.symlink_to(rel, target_is_directory=src.is_dir())
        log.info(f"Linked: {dst} → {rel}")
        return True

    linked = 0
    for src in dot_dir.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(dot_dir)
        if rel.parts[0] == ".git":
            continue
        if any(rel.is_relative_to(Path(d)) for d in dirs_to_link):
            continue
        dst = HOME / ("." + str(rel))
        dst.parent.mkdir(parents=True, exist_ok=True)
        if link_path(src, dst):
            linked += 1
    for d in dirs_to_link:
        src = dot_dir / d
        if not src.is_dir():
            continue
        dst = HOME / ("." + d)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if link_path(src, dst):
            linked += 1
    for src_name, dst_dir in ind_dirs:
        src_dir = sec_dots_dir / src_name
        if not src_dir.is_dir():
            continue
        for src in src_dir.rglob("*"):
            if not src.is_file():
                continue
            dst = dst_dir / src.relative_to(src_dir)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if link_path(src, dst):
                linked += 1
    run(["hyprctl", "reload"])
    log.info(f"Linked: {linked}")


############################
# Encryption/Keys
############################
def import_ssh(key_path: Path) -> None:
    socket = f"/run/user/{os.getuid()}/gcr/ssh"
    os.environ["SSH_AUTH_SOCK"] = socket
    if not Path(socket).exists():
        run(["systemctl", "--user", "enable", "gcr-ssh-agent.socket"])
        run(["systemctl", "--user", "start", "gcr-ssh-agent.socket"])
    if run(["ssh-add", str(key_path)], check=True):
        log.info(f"SSH key {key_path} added or already present.")
    else:
        log.error(f"Failed to add SSH key {key_path}.")


def import_gpg(gpg_path: Path) -> None:
    key_data = gpg_path.read_text()
    gpg = gnupg.GPG()
    import_result = gpg.import_keys(
        key_data, passphrase=ask_pass("GPG Password: ", False, 6)
    )
    log.info(import_result.results)


def init_gocrypt(enc_dir: Path) -> None:
    enc_dir.mkdir(parents=True, exist_ok=True)
    while True:
        pw1 = getpass.getpass("Enter new gocryptfs password: ")
        pw2 = getpass.getpass("Confirm password: ")
        if pw1 == pw2 and pw1:
            break
        log.warning("Passwords do not match or empty. Try again.\n")
    cmd = ["gocryptfs", "-init", "--passfile", "/dev/stdin", str(enc_dir)]
    run(cmd, check=True, input_text=pw1)
    log.info(f"gocryptfs initialized at {enc_dir}.")


############################
# MariaDB
############################
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
        result = run(cmd)
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
        scan = run(["ssh-keyscan", "-H", "github.com"])
        if scan and scan.stdout:
            kh.write_text(content + scan.stdout)
            log.info("Added github.com to known_hosts")
        else:
            log.warning("Failed to scan github.com for known_hosts")


def clone_repos(git_user: str, git_repos: list, dest: Path, ssh: bool) -> None:
    def url(repo: str) -> str:
        if ssh:
            return f"git@github.com:{git_user}/{repo}.git"
        return f"https://github.com/{git_user}/{repo}.git"

    dest.mkdir(parents=True, exist_ok=True)
    for repo in git_repos:
        repo_path = dest / repo
        if repo_path.exists():
            log.info(f"{repo_path} exists, skipping.")
            continue
        result = run(["git", "clone", url(repo), str(repo_path)], check=False)
        if result.returncode == 0:
            log.info(f"Cloned {repo}")
        else:
            log.warning(f"Failed to clone {repo}")


def configure_git() -> None:
    result = run(["ssh-add", "-l"])
    lines = result.stdout.strip().splitlines()
    if not lines:
        log.warning("No SSH keys found")
        return
    parts = lines[0].split()
    my_email = parts[2]
    my_name = input("Enter your full real name (git): ").strip()
    run(["git", "config", "--global", "user.email", my_email])
    run(["git", "config", "--global", "user.name", my_name])
    log.info(f"Configured git with email={my_email} and name={my_name}")


############################
# Icons/Folders
############################
def set_folder_icons(
    custom_folder_icons: list[tuple[Path, str]],
    icon_dir="/usr/share/icons/WhiteSur-dark/places/scalable",
) -> None:
    for folder, icon_name in custom_folder_icons:
        icon = f"{icon_dir}/{icon_name}.svg"
        folder.mkdir(parents=True, exist_ok=True)
        if Path(icon).exists():
            icon_uri = f"file://{icon}"
            cmd = ["gio", "set", str(folder), "metadata::custom-icon", icon_uri]
            run(cmd)


############################
# Launch Apps
############################
def pass_and_input(pass_path: Path):
    password = pass_path.read_text().strip()
    os.environ["CLIPBOARD_STATE"] = "sensitive"
    pyperclip.copy(password)
    log.info("Password copied to clipboard.")
    cmd = ["firedragon", "https://addons.mozilla.org/en-US/firefox/addon/proton-pass/"]
    subprocess.Popen(cmd).wait()
    pyperclip.copy("")
    log.info("Clipboard cleared.")
    os.environ.pop("CLIPBOARD_STATE", None)


def launch_apps(apps=[firefox_browser, "protonmail-bridge", "betterbird", "steam"]):
    processes = []
    for app in apps:
        processes.append(subprocess.Popen(app))
    for app, process in zip(apps, processes):
        process.wait()
        log.info(f"{app} closed")


def scrcpy_setup(port=5555) -> None:
    answer = yes_no("Is your Android phone connected?")
    if not answer:
        log.info("Please connect your device via USB first.")
        return
    ip = next(
        (
            line.split("src")[-1].strip()
            for line in run(["adb", "shell", "ip", "route"]).stdout.splitlines()
            if "wlan" in line and "src" in line
        )
    )
    if not ip:
        log.warning("Could not determine device IP.")
        return
    target = f"{ip}:{port}"
    log.info(f"Trying {target}")
    msg = run(["adb", "connect", target])
    log.info((msg.stdout + msg.stderr).lower())


############################
# Main
############################
def main(HOME=Path.home()):
    if shutil.which("zsh"):
        run(["chsh", "-s", "/usr/bin/zsh"], interactive=True)
    if shutil.which("firewalld"):
        run(["sudo", "firewall-cmd", "--set-default-zone=block"])
        fw_cmd = ["sudo", "firewall-cmd", "--permanent", "--zone=block"]
        for service in firewall_services:
            run(fw_cmd + [f"--add-service={service}"])
        for port in firewall_ports:
            run(fw_cmd + [f"--add-port={port}"])
    if shutil.which("iwd") and not ping():
        run(["sudo", "rm", "/etc/resolv.conf"])
        run(["sudo", "resolvconf", "-u"])
        run(["sudo", "systemctl", "restart", "iwd"])
        time.sleep(5)
        iwctl_scan()
        time.sleep(5)
    if shutil.which("tuned"):
        run(["tuned-adm", "profile", "laptop-ac-powersave"])
    if shutil.which("mariadb"):
        enable_mariadb(user_name)
    if ssh_path.exists():
        import_ssh(ssh_path)
        configure_git()
        ensure_github_known_hosts()
        clone_repos(git_user, repos + private_repos, GIT_DIR, ssh=True)
    else:
        clone_repos(git_user, repos, GIT_DIR, ssh=False)
    if gpg_path and not gpg_path.exists():
        import_gpg(gpg_path)
    if ENCRYPTED and not (ENCRYPTED / "gocryptfs.conf").exists():
        if shutil.which("gocryptfs"):
            init_gocrypt(ENCRYPTED)
    if dirs_icons:
        set_folder_icons(dirs_icons)
    for plugin in yazi_plugins:
        run(["ya", "pkg", "add", plugin])
    if any((dots_path).iterdir()):
        deploy_dotfiles(HOME, dots_path, dirs_to_link, ind_dirs, secret_dots)
        run(
            ["uv", "add", "openmeteo-requests"],
            cwd=f"/home/{user_name}/.local/bin/weather",
        )
    if android:
        scrcpy_setup()
    if masterpass_path.is_file():
        pass_and_input(masterpass_path)
        launch_apps()
    run(
        ["gh", "auth", "login", "-h", "github.com", "-s", "delete_repo"],
        interactive=True,
    )
    for d in [(HOME / "archinstall")]:
        if d.exists():
            shutil.rmtree(d)
    if yes_no("Reboot now?", default=False):
        run(["systemctl", "reboot"])
        log.info("Reboot cancelled.")
        return


if __name__ == "__main__":
    main()
