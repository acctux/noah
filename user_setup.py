#!/usr/bin/env python3
import os
import pwd
import shutil
import subprocess
import time
from dataclasses import dataclass, field
import getpass
from pathlib import Path

import gnupg
import pyperclip
from jsonconfig import noah_json
from lib.datahandler import GitReposConfiguration, KeyCopyConfiguration, NoahConfig
from utils import get_logger, run_dmc, yes_no

log = get_logger("Noah")


############################
# USER SETUP HELPERS
############################
def iwctl_scan() -> bool:
    """Trigger a background station scan via iwctl."""
    result = run_dmc(["sudo", "iwctl", "station", "wlan0", "scan"], check=False)
    time.sleep(10)
    return result.returncode == 0 if result else False


def ping(host: str = "google.com") -> bool:
    """Check network connectivity via single ping."""
    try:
        res = subprocess.run(
            ["ping", "-c", "1", "-W", "2", host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return res.returncode == 0
    except Exception:
        return False


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
        self.username = self.username or pwd.getpwuid(os.getuid()).pw_name
        self.HOME = (
            Path.home()
            if self.username == pwd.getpwuid(os.getuid()).pw_name
            else Path("/home") / self.username
        )
        self.ENCRYPTED = (
            self.HOME / self.data.encrypted_dir if self.data.encrypted_dir else None
        )
        self.DOTS = (
            self.HOME / "Lit" / self.data.dots_repo if self.data.dots_repo else None
        )
        self.SEC_DOTS = self.HOME / "Lit" / "Docs" / "secdots"
        if key_cfg := self.data.key_copy_config:
            target = key_cfg.target_dir
            k = key_cfg.keys
            self.ssh_path = self.HOME / target / k.get("ssh_key", "")
            self.gpg_path = self.HOME / target / k.get("gpg_key", "")
            self.masterpass_path = self.HOME / target / k.get("master_pass", "")
        self.dirs_icons = {
            self.HOME / Path(path): icon
            for path, icon in (self.data.dirs_icons or {}).items()
        }


##########################################
# SYMLINK & FILE CANDIDATE HELPERS
##########################################
def link_path(src: Path, dst: Path) -> bool:
    """Safely create relative atomic symlinks."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    rel = os.path.relpath(src, dst.parent)
    if dst.is_symlink() and os.readlink(dst) == rel:
        return False
    if dst.exists() or dst.is_symlink():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
        log.info(f"Removed old target destination: {dst}")
    dst.symlink_to(rel, target_is_directory=src.is_dir())
    log.info(f"Linked: {dst} → {rel}")
    return True


def enter_pass(prompt_str: str) -> str:
    """Secure masked entry utility for credential setting."""
    while True:
        password = getpass.getpass(prompt_str)
        confirm_password = getpass.getpass("Confirm password: ")
        if password == confirm_password and password:
            log.info("Password confirmed.")
            return password
        log.warning("Passwords do not match or empty. Try again.\n")


def dotted_destination(src: Path, source_dir: Path, target_dir: Path) -> Path:
    parts = src.relative_to(source_dir).parts
    return target_dir / Path("." + parts[0], *parts[1:])


def collect_candidates(
    base_dir: Path, home: Path, dirs_to_skip: list[str]
) -> list[tuple[Path, Path]]:
    """Return filtered list of (src, dst) mapping tuples for directory files."""
    candidates = []
    skip_roots = {d.split("/")[0] for d in dirs_to_skip} | {".git"}
    for src in base_dir.rglob("*"):
        if not src.is_file():
            continue
        rel_parts = src.relative_to(base_dir).parts
        if rel_parts and rel_parts[0] in skip_roots:
            continue
        candidates.append((src, dotted_destination(src, base_dir, home)))
    return candidates


def file_candidates(nc: NoahConfig, nu: NoahUserProcessor) -> list[tuple[Path, Path]]:
    """Generate master stack of all expected files and folders to target link."""
    if not nu.DOTS:
        return []
    candidates = []
    candidates.extend(collect_candidates(nu.DOTS, nu.HOME, nc.dirs_to_link))
    candidates.extend(collect_candidates(nu.SEC_DOTS, nu.HOME, nc.dirs_to_link))
    for d in nc.dirs_to_link:
        src = nu.DOTS / d
        if src.is_dir():
            candidates.append((src, dotted_destination(src, nu.DOTS, nu.HOME)))
    return candidates


def deploy_dotfiles(nc: NoahConfig, nu: NoahUserProcessor) -> None:
    if nu.DOTS and not nu.DOTS.is_dir():
        log.error(f"Dotfiles directory missing: {nu.DOTS}")
        return
    linked = sum(1 for src, dst in file_candidates(nc, nu) if link_path(src, dst))
    if shutil.which("hyprctl"):
        subprocess.run(["hyprctl", "reload"], check=False)
        log.info("Hyprland reloaded configuration.")
    log.info(f"Total files synchronized and linked: {linked}")


############################
# ENCRYPTION / KEYS
############################
def import_ssh(key_path: Path) -> None:
    socket_path = Path(f"/run/user/{os.getuid()}/gcr/ssh")
    if not socket_path.exists():
        run_dmc(["systemctl", "--user", "enable", "gcr-ssh-agent.socket"])
        run_dmc(["systemctl", "--user", "start", "gcr-ssh-agent.socket"])
    run_dmc(["ssh-add", str(key_path)], check=False)
    log.info(f"SSH identity processed for: {key_path}")


def import_gpg(gpg_path: Path) -> None:
    key_data = gpg_path.read_text()
    gpg = gnupg.GPG()
    import_result = gpg.import_keys(key_data)
    log.info(f"GPG import status results: {import_result.results}")


def init_gocrypt(enc_dir: Path) -> None:
    enc_dir.mkdir(parents=True, exist_ok=True)
    pw = enter_pass("Enter new gocryptfs password: ")
    cmd = ["gocryptfs", "-init", "--passfile", "/dev/stdin", str(enc_dir)]
    run_dmc(cmd, check=True, input_text=pw)
    log.info(f"gocryptfs cleanly initialized at {enc_dir}.")


############################
# MARIADB
############################
def enable_mariadb() -> None:
    user_name = getpass.getuser()
    password = enter_pass("Configure MariaDB user password: ")
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
            f"CREATE USER '{user_name}'@'localhost' IDENTIFIED BY '{password}'; "
            f"GRANT ALL PRIVILEGES ON mydb.* TO '{user_name}'@'localhost'; "
            f"FLUSH PRIVILEGES;",
        ],
    ]
    for cmd in commands:
        result = run_dmc(cmd)
        if result and result.returncode != 0:
            log.error(f"Database initialization step failed: {cmd}")


############################
# GIT / REPOS
############################
def ensure_github_known_hosts(home_path: Path) -> None:
    kh = home_path / ".ssh" / "known_hosts"
    kh.parent.mkdir(parents=True, exist_ok=True)
    kh.touch(exist_ok=True)
    content = kh.read_text(errors="ignore")
    if "github.com" not in content:
        scan = run_dmc(["ssh-keyscan", "-H", "github.com"], check=True)
        if scan and scan.stdout:
            kh.write_text(content + scan.stdout)
            log.info("Appended github.com validation signature to known_hosts")
        else:
            log.warning("Could not -keyscan to verify GitHub host identity.")


def clone_repos(git_repos: GitReposConfiguration, dest: Path, ssh: bool) -> None:
    def get_url(user: str, repo: str) -> str:
        return (
            f"git@github.com:{user}/{repo}.git"
            if ssh
            else f"https://github.com/{user}/{repo}.git"
        )

    dest.mkdir(parents=True, exist_ok=True)
    for git_user in git_repos.repositories:
        for remote_repo, local_dir in git_user.repos.items():
            repo_path = dest / Path(local_dir).name
            if repo_path.exists():
                log.info(f"Repository destination '{repo_path}' exists, skipping.")
                continue
            result = subprocess.run(
                [
                    "git",
                    "clone",
                    get_url(git_user.username, remote_repo),
                    str(repo_path),
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                log.info(f"Successfully cloned {remote_repo}")
            else:
                log.warning(f"Aborted {remote_repo}: {result.stderr.strip()}")


def configure_git() -> None:
    def git_config_get(key: str) -> str | None:
        result = run_dmc(["git", "config", "--global", "--get", key], check=False)
        return result.stdout.strip() if result and result.stdout else None

    if git_config_get("user.email") and git_config_get("user.name"):
        log.info("Global profile environment for Git already generated.")
        return
    result = run_dmc(["ssh-add", "-l"])
    lines = result.stdout.strip().splitlines() if result and result.stdout else []
    if not lines:
        log.warning("Cannot scan user metadata without active SSH session.")
        return
    my_email = lines[0].split()[2]
    my_name = input("Enter your global git user.name profile identity: ").strip()
    run_dmc(["git", "config", "--global", "user.email", my_email])
    run_dmc(["git", "config", "--global", "user.name", my_name])
    log.info(f"Created configuration footprint parameters: {my_name} <{my_email}>")


############################
# DESKTOP ENVIRONMENT / APPS
############################
def set_folder_icons(
    custom_folder_icons: dict[Path, str],
    icon_dir: str = "/usr/share/icons/WhiteSur-dark/places/scalable",
) -> None:
    for folder, icon_name in custom_folder_icons.items():
        icon = Path(icon_dir) / f"{icon_name}.svg"
        folder.mkdir(parents=True, exist_ok=True)
        if icon.exists():
            run_dmc(
                ["gio", "set", str(folder), "metadata::custom-icon", f"file://{icon}"]
            )


def pass_and_input(pass_path: Path, firefox_browser: str) -> None:
    """Loads master pass into clipboard, launches extension URL, and flushes clipboard after 15s delay."""
    password = pass_path.read_text().strip()
    os.environ["CLIPBOARD_STATE"] = "sensitive"
    pyperclip.copy(password)
    log.info("Master password copied to system volatile clipboard buffer.")
    cmd = [
        firefox_browser,
        "https://addons.mozilla.org/en-US/firefox/addon/proton-pass/",
    ]
    subprocess.Popen(cmd)
    log.info("Waiting 15 seconds  before purge.")
    time.sleep(15)
    pyperclip.copy("")
    os.environ.pop("CLIPBOARD_STATE", None)
    log.info("Sensitive clipboard stack cleared completely.")


def launch_apps(apps: list[str] | None = None) -> None:
    if apps is None:
        apps = ["protonmail-bridge", "betterbird", "steam"]
    processes = [subprocess.Popen(app) for app in apps if shutil.which(app)]
    for process in processes:
        process.wait()


def scrcpy_setup(port: int = 5555) -> None:
    if not yes_no("Is your Android device actively mounted via USB interface?"):
        log.info(
            "Please assert active connectivity via hardwire link lines before running network bridge."
        )
        return
    route_output = run_dmc(["adb", "shell", "ip", "route"])
    lines = (
        route_output.stdout.splitlines() if route_output and route_output.stdout else []
    )
    ip = next(
        (
            line.split("src")[-1].strip()
            for line in lines
            if "wlan" in line and "src" in line
        ),
        None,
    )
    if not ip:
        log.warning("Device could not dynamically resolve ip.")
        return
    target = f"{ip}:{port}"
    log.info(f"Attempting handoff sync targeting interface address: {target}")
    if msg := run_dmc(["adb", "connect", target]):
        log.info((msg.stdout + msg.stderr).lower())


############################
# SYSTEM COMPONENT FLOWS
############################
def fix_network_stack() -> None:
    if Path("/etc/resolv.conf").is_symlink() and not ping():
        run_dmc(["sudo", "rm", "/etc/resolv.conf"])
        run_dmc(["sudo", "resolvconf", "-u"])
        run_dmc(["sudo", "systemctl", "restart", "iwd"])
        time.sleep(5)
        iwctl_scan()
        time.sleep(5)


def handle_identities(nc: NoahConfig, nu: NoahUserProcessor) -> None:
    if nu.ssh_path and nu.ssh_path.is_file():
        # import_ssh(nu.ssh_path)
        # configure_git()
        ensure_github_known_hosts(nu.HOME)
        if nc.git_repos_config:
            clone_repos(nc.git_repos_config, nu.HOME, ssh=True)
    elif nc.git_repos_config:
        clone_repos(nc.git_repos_config, nu.HOME, ssh=False)
    if nu.gpg_path and nu.gpg_path.is_file():
        import_gpg(nu.gpg_path)


############################
# MAIN FLOW
############################
def user_setup() -> None:
    # if shutil.which("zsh"):
    #     run_dmc(["chsh", "-s", "/usr/bin/zsh"], interactive=True)
    # fix_network_stack()
    # if shutil.which("tuned"):
    #     run_dmc(["tuned-adm", "profile", "laptop-ac-powersave"])
    nc = NoahConfig.from_config(noah_json)
    nu = NoahUserProcessor(nc)
    # if shutil.which("mariadb"):
    #     enable_mariadb()
    handle_identities(nc, nu)
    if nu.ENCRYPTED and shutil.which("gocryptfs"):
        if not (nu.ENCRYPTED / "gocryptfs.conf").exists():
            init_gocrypt(nu.ENCRYPTED)
    if nu.dirs_icons:
        set_folder_icons(nu.dirs_icons)
    for plugin in nc.yazi_plugins:
        run_dmc(["ya", "pkg", "add", plugin])
    if nu.DOTS and any(nu.DOTS.iterdir()):
        deploy_dotfiles(nc, nu)
        run_dmc(
            ["uv", "add", "openmeteo-requests"],
            cwd=str(nu.HOME / ".local" / "bin" / "weather"),
        )
    if shutil.which("scrcpy"):
        scrcpy_setup()
    if nu.masterpass_path and nu.masterpass_path.is_file() and nc.firefox_browser:
        pass_and_input(nu.masterpass_path, nc.firefox_browser)
        launch_apps()
    if shutil.which("gh"):
        run_dmc(
            ["gh", "auth", "login", "-h", "github.com", "-s", "delete_repo"],
            interactive=True,
        )
    archinstall_dir = nu.HOME / "archinstall"
    if archinstall_dir.exists():
        shutil.rmtree(archinstall_dir)
    if yes_no("Finished. Reboot system interface now?", default=False):
        run_dmc(["systemctl", "reboot"])
    else:
        log.info("System restart deferred manually.")


if __name__ == "__main__":
    user_setup()
