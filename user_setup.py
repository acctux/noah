#!/usr/bin/env python3
from utils import get_logger, run_dmc, yes_no
import pwd
from jsonconfig import noah_json
from getpass import getpass
import os
from pathlib import Path
import time
import gnupg
import shutil
import subprocess
from lib.datahandler import NoahConfig, KeyCopyConfiguration, GitReposConfiguration
from dataclasses import dataclass, field
import pyperclip


log = get_logger("Noah")


############################
# USER SETUP
############################
def iwctl_scan() -> bool:
    result = run_dmc(["sudo", "iwctl", "station", "wlan0", "scan"], check=False)
    time.sleep(10)
    if result.returncode == 0:
        return True
    return False


def ping(host: str = "google.com") -> bool:
    cmd = ["ping", "-c", "1", host]
    return (
        subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
        == 0
    )


@dataclass(slots=True)
class NoahUserProcessor:
    data: NoahConfig
    username: str | None = None

    HOME: Path = field(init=False)
    ENCRYPTED: Path | None = field(init=False)
    DOTS: Path | None = field(init=False)
    SEC_DOTS: Path = field(init=False)

    ssh_path: Path | None = field(init=False, default=None)
    gpg_path: Path | None = field(init=False, default=None)
    masterpass_path: Path | None = field(init=False, default=None)

    dirs_icons: dict[Path, str] = field(init=False, default_factory=dict)
    key_copy_config: KeyCopyConfiguration | None = None

    def __post_init__(self):
        # ---------- base home ----------
        self.HOME = (
            Path.home() if self.username is None else Path("/home") / self.username
        )
        # ---------- optional config-based paths ----------
        encrypted_dir = self.data.encrypted_dir
        self.ENCRYPTED = self.HOME / encrypted_dir if encrypted_dir else None
        dots_repo = self.data.dots_repo
        self.DOTS = self.HOME / "Lit" / dots_repo if dots_repo else None
        self.SEC_DOTS = self.HOME / "Lit" / "Docs" / "secdots"
        # ---------- flattened key-based paths (safe fallback) ----------
        key_cfg = self.data.key_copy_config
        if key_cfg:
            target = key_cfg.target_dir
            k = key_cfg.keys

            self.ssh_path = self.HOME / target / k["ssh_key"]
            self.gpg_path = self.HOME / target / k["gpg_key"]
            self.masterpass_path = self.HOME / target / k["master_pass"]
        else:
            self.ssh_path = None
            self.gpg_path = None
            self.masterpass_path = None

        self.dirs_icons = {
            self.HOME / Path(path): icon
            for path, icon in (self.data.dirs_icons or {}).items()
        }


##########################################
# HELPERS
##########################################
def link_path(src: Path, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    rel = os.path.relpath(src, dst.parent)
    if dst.is_symlink() and os.readlink(dst) == rel:
        return False
    if dst.exists() or dst.is_symlink():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
        log.info(f"Removed: {dst}")
    dst.symlink_to(rel, target_is_directory=src.is_dir())
    log.info(f"Linked: {dst} → {rel}")
    return True


def enter_pass():
    while True:
        password = input("Enter a password: ")
        confirm_password = input("Confirm your password: ")
        if password == confirm_password:
            log.info("Password set successfully!")
            return password
        else:
            log.info("Passwords do not match. Please try again.\n")


def dotted_destination(src: Path, source_dir: Path, target_dir: Path) -> Path:
    parts = src.relative_to(source_dir).parts
    return target_dir / Path("." + parts[0], *parts[1:])


def collect_candidates(
    base_dir: Path, home: Path, dirs_to_skip: list[str]
) -> list[tuple[Path, Path]]:
    """Return list of (src, dst) tuples for all files in base_dir, skipping certain dirs."""
    candidates = []
    for src in base_dir.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(base_dir)
        if rel.parts[0] == ".git":
            continue
        if any(rel.parts[0] == d.split("/")[0] for d in dirs_to_skip):
            continue
        candidates.append((src, dotted_destination(src, base_dir, home)))
    return candidates


def file_candidates(nc: NoahConfig, nu: NoahUserProcessor) -> list[tuple[Path, Path]]:
    """Return list of (src, dst) tuples to link."""
    candidates = []
    if nu.DOTS:
        candidates.extend(collect_candidates(nu.DOTS, nu.HOME, nc.dirs_to_link))
        candidates.extend(collect_candidates(nu.SEC_DOTS, nu.HOME, nc.dirs_to_link))
        for d in nc.dirs_to_link:
            src = nu.HOME / nu.DOTS / d
            if src.is_dir():
                candidates.append((src, dotted_destination(src, nu.DOTS, nu.HOME)))
    return candidates


##########################################
# MAIN
##########################################
def deploy_dotfiles(nc: NoahConfig, nu: NoahUserProcessor):
    if nu.DOTS and not nu.DOTS.is_dir():
        log.error(f"Dotfiles directory not found: {nu.DOTS}")
        return
    linked = 0
    for src, dst in file_candidates(nc, nu):
        if link_path(src, dst):
            linked += 1
    if shutil.which("hyprctl"):
        subprocess.run(["hyprctl", "reload"], check=False)
        log.info("Hyprland reloaded")
    log.info(f"Total linked:\033[0m {linked}")


############################
# Encryption/Keys
############################
def import_ssh(key_path: Path) -> None:
    if not Path(f"/run/user/{os.getuid()}/gcr/ssh").exists():
        run_dmc(["systemctl", "--user", "enable", "gcr-ssh-agent.socket"])
        run_dmc(["systemctl", "--user", "start", "gcr-ssh-agent.socket"])
    run_dmc(["ssh-add", str(key_path)], check=False)
    log.info(f"SSH key {key_path} added or already present.")


def import_gpg(gpg_path: Path) -> None:
    key_data = gpg_path.read_text()
    gpg = gnupg.GPG()
    pwd = enter_pass()
    import_result = gpg.import_keys(key_data, pwd)
    log.info(import_result.results)


def init_gocrypt(enc_dir: Path) -> None:
    enc_dir.mkdir(parents=True, exist_ok=True)
    while True:
        pw1 = getpass("Enter new gocryptfs password: ")
        pw2 = getpass("Confirm password: ")
        if pw1 == pw2 and pw1:
            break
        log.warning("Passwords do not match or empty. Try again.\n")
    cmd = ["gocryptfs", "-init", "--passfile", "/dev/stdin", str(enc_dir)]
    run_dmc(cmd, check=True, input_text=pw1)
    log.info(f"gocryptfs initialized at {enc_dir}.")


############################
# MariaDB
############################
def enable_mariadb(user_name) -> None:
    while True:
        p1 = getpass("Mariadb password: ")
        p2 = getpass("Confirm: ")
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
        result = run_dmc(cmd)
        if result and result.returncode != 0:
            log.error(f"Command failed: {cmd}")


############################
# Git/Repos
############################
def ensure_github_known_hosts(HOME: Path) -> None:
    kh = HOME / ".ssh" / "known_hosts"
    kh.parent.mkdir(parents=True, exist_ok=True)
    if not kh.exists():
        kh.touch()
    content = kh.read_text(errors="ignore")
    if "github.com" not in content:
        scan = run_dmc(["ssh-keyscan", "-H", "github.com"])
        if scan and scan.stdout:
            kh.write_text(content + scan.stdout)
            log.info("Added github.com to known_hosts")
        else:
            log.warning("Failed to scan github.com for known_hosts")


def clone_repos(git_repos: GitReposConfiguration, dest: Path, ssh: bool) -> None:
    def url(user: str, repo: str) -> str:
        if ssh:
            return f"git@github.com:{user}/{repo}.git"
        return f"https://github.com/{user}/{repo}.git"

    dest.mkdir(parents=True, exist_ok=True)
    for git_user in git_repos.repositories:
        for remote_repo, local_dir in git_user.repos.items():
            repo_path = dest / Path(local_dir).name
            if repo_path.exists():
                log.info(f"{repo_path} exists, skipping.")
                continue
            result = subprocess.run(
                ["git", "clone", url(git_user.username, remote_repo), str(repo_path)],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                log.info(f"Cloned {remote_repo} to {repo_path}")
            else:
                log.warning(
                    f"Failed to clone {remote_repo}. Error: {result.stderr.strip()}"
                )


def configure_git() -> None:
    def git_config_check(key: str):
        result = run_dmc(["git", "config", "--global", "--get", key], check=False)
        value = result.stdout.strip() if result and result.stdout else ""
        return value or None

    existing_email = git_config_check("user.email")
    existing_name = git_config_check("user.name")
    if existing_email and existing_name:
        log.info(f"Git already configured: {existing_name} <{existing_email}>")
        return
    result = run_dmc(["ssh-add", "-l"])
    lines = result.stdout.strip().splitlines()
    if not lines:
        log.warning("No SSH keys found")
        return
    parts = lines[0].split()
    my_email = parts[2]
    my_name = input("Enter your full real name (git): ").strip()
    run_dmc(["git", "config", "--global", "user.email", my_email])
    run_dmc(["git", "config", "--global", "user.name", my_name])
    log.info(f"Configured git with email={my_email} and name={my_name}")


############################
# Icons/Folders
############################
def set_folder_icons(
    custom_folder_icons: dict[Path, str],
    icon_dir="/usr/share/icons/WhiteSur-dark/places/scalable",
) -> None:
    for folder, icon_name in custom_folder_icons.items():
        icon = f"{icon_dir}/{icon_name}.svg"
        folder.mkdir(parents=True, exist_ok=True)
        if Path(icon).exists():
            icon_uri = f"file://{icon}"
            cmd = ["gio", "set", str(folder), "metadata::custom-icon", icon_uri]
            run_dmc(cmd)


############################
# Launch Apps
############################
def pass_and_input(pass_path: Path, firefox_browser: str):
    password = pass_path.read_text().strip()
    os.environ["CLIPBOARD_STATE"] = "sensitive"
    pyperclip.copy(password)
    log.info("Password copied to clipboard.")
    cmd = [
        firefox_browser,
        "https://addons.mozilla.org/en-US/firefox/addon/proton-pass/",
    ]
    subprocess.Popen(cmd).wait()
    pyperclip.copy("")
    log.info("Clipboard cleared.")
    os.environ.pop("CLIPBOARD_STATE", None)


def launch_apps(apps=["protonmail-bridge", "betterbird", "steam"]):
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
            for line in run_dmc(["adb", "shell", "ip", "route"]).stdout.splitlines()
            if "wlan" in line and "src" in line
        )
    )
    if not ip:
        log.warning("Could not determine device IP.")
        return
    target = f"{ip}:{port}"
    log.info(f"Trying {target}")
    msg = run_dmc(["adb", "connect", target])
    log.info((msg.stdout + msg.stderr).lower())


############################
# Main
############################
def user_setup():
    if shutil.which("zsh"):
        run_dmc(["chsh", "-s", "/usr/bin/zsh"], interactive=True)
    if Path("/etc/resolv.conf").is_symlink() and not ping():
        run_dmc(["sudo", "rm", "/etc/resolv.conf"])
        run_dmc(["sudo", "resolvconf", "-u"])
        run_dmc(["sudo", "systemctl", "restart", "iwd"])
        time.sleep(5)
        iwctl_scan()
        time.sleep(5)
    if shutil.which("tuned"):
        run_dmc(["tuned-adm", "profile", "laptop-ac-powersave"])
    nc = NoahConfig.from_config(noah_json)
    nu = NoahUserProcessor(nc)
    if shutil.which("mariadb"):
        user = pwd.getpwuid(os.getuid()).pw_name
        enable_mariadb(user)
    log.info(nu.ssh_path)
    if ssh_path := nu.ssh_path:
        if ssh_path.is_file():
            import_ssh(ssh_path)
            configure_git()
            ensure_github_known_hosts(nu.HOME)
            if git_conf := nc.git_repos_config:
                clone_repos(git_conf, nu.HOME, ssh=True)
    else:
        if git_conf := nc.git_repos_config:
            clone_repos(git_conf, nu.HOME, ssh=False)
    if gpg_path := nu.gpg_path:
        if gpg_path.is_file():
            import_gpg(gpg_path)
    if nu.ENCRYPTED and not (nu.ENCRYPTED / "gocryptfs.conf").exists():
        if shutil.which("gocryptfs"):
            init_gocrypt(nu.ENCRYPTED)
    if nu.dirs_icons:
        set_folder_icons(nu.dirs_icons)
    for plugin in nc.yazi_plugins:
        run_dmc(["ya", "pkg", "add", plugin])
    if nu.DOTS:
        if any((nu.DOTS).iterdir()):
            deploy_dotfiles(nc, nu)
            run_dmc(
                ["uv", "add", "openmeteo-requests"],
                cwd=f"{nu.HOME}/.local/bin/weather",
            )
    if shutil.which("scrcpy"):
        scrcpy_setup()
    if masterpass := nu.masterpass_path:
        if masterpass.is_file() and nc.firefox_browser:
            pass_and_input(masterpass, nc.firefox_browser)
            launch_apps()
    run_dmc(
        ["gh", "auth", "login", "-h", "github.com", "-s", "delete_repo"],
        interactive=True,
    )
    for d in [(nu.HOME / "archinstall")]:
        if d.exists():
            shutil.rmtree(d)
    if yes_no("Reboot now?", default=False):
        run_dmc(["systemctl", "reboot"])
        log.info("Reboot cancelled.")
        return


if __name__ == "__main__":
    user_setup()
