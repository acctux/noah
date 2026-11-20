#!/usr/bin/env python3

import os
import shutil
import subprocess
import time
import getpass
from pathlib import Path
import gnupg
import pyperclip
from jsonconfig import noah_json
from lib.datahandler import GitReposConfiguration, NoahConfig
from utils import get_logger, run_dmc, yes_no

log = get_logger("Noah")


############################
# USER SETUP HELPERS
############################
def ping(host: str = "8.8.8.8", timeout: int = 2) -> bool:
    # -c 1: Send 1 packet
    # -W 2: Wait 2 seconds
    # Using shell=False (default) for security
    result = subprocess.run(
        ["ping", "-c", "1", "-W", str(timeout), host],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


class PolkaDots:
    def __init__(
        self,
        HOME: Path,
        dotfiles_dirs: list[Path],
        skip_dirs: set[str] | None = None,
        skip_files: set[str] | None = None,
    ) -> None:
        self.home = HOME
        self.dotfiles_dirs = dotfiles_dirs
        self.skip_dirs = skip_dirs or {".git", "__pycache__", ".venv"}
        self.skip_files = skip_files or {".gitignore"}

    def _should_skip(self, relative_path: Path) -> bool:
        return relative_path.name in self.skip_files or any(
            part in self.skip_dirs for part in relative_path.parts
        )

    def _destination_for(self, relative_path: Path) -> Path:
        parts = relative_path.parts
        return self.home / Path(f".{parts[0]}", *parts[1:])

    def _link_file(self, source: Path, destination: Path) -> bool:
        target = os.path.relpath(source, destination.parent)

        if destination.is_symlink() and os.readlink(destination) == target:
            return False

        if destination.exists() or destination.is_symlink():
            destination.unlink()
            log.info("Removed: %s", destination)

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(target)
        log.info("Linked: %s → %s", destination, target)
        return True

    def deploy(self) -> None:
        linked = 0

        for source_dir in self.dotfiles_dirs:
            if not source_dir.is_dir():
                log.warning("%s not found, skipping.", source_dir)
                continue

            for source in source_dir.rglob("*"):
                if not source.is_file():
                    continue

                relative_path = source.relative_to(source_dir)
                if self._should_skip(relative_path):
                    continue

                destination = self._destination_for(relative_path)
                linked += self._link_file(source, destination)

        log.info("Total linked: %d", linked)

        if linked:
            subprocess.run(["hyprctl", "reload"], check=False)
            log.info("Hyprland reloaded")


class NoahUserProcessor:
    data: NoahConfig
    HOME: Path
    encrypted_dir: Path | None
    dotdirs_to_link: list[str] | None
    ssh_paths: list[Path]
    gpg_paths: list[Path]
    masterpass_paths: list[Path]
    dirs_icons: dict[Path, str]

    def __init__(self, data: NoahConfig, HOME: Path) -> None:
        self.data = data
        self.HOME = HOME
        self.encrypted_dir = HOME / data.encrypted_dir if data.encrypted_dir else None
        self.dotdirs_to_link = data.dotdirs_to_link if data.dotdirs_to_link else None

        self.ssh_paths = []
        self.gpg_paths = []
        self.masterpass_paths = []

        if data.copy_config:
            self.ssh_paths = data.copy_config.user_space_resolve_by_type("ssh", HOME)
            self.gpg_paths = data.copy_config.user_space_resolve_by_type("gpg", HOME)
            self.masterpass_paths = data.copy_config.user_space_resolve_by_type(
                "masterpass", HOME
            )

        if data.dirs_icons:
            self.dirs_icons = {
                HOME / path: icon for path, icon in data.dirs_icons.items()
            }

    def dotdirs_paths(self) -> list[Path]:
        return [self.HOME / directory for directory in (self.dotdirs_to_link or [])]


###########################################################
# ENTRY
##########################################
def enter_pass(prompt_str: str) -> str:
    while True:
        password = getpass.getpass(prompt_str)
        confirm_password = getpass.getpass("Confirm password: ")
        if password == confirm_password and password:
            log.info("Password confirmed.")
            return password
        log.warning("Passwords do not match or empty. Try again.\n")


############################
# ENCRYPTION / KEYS
############################
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


class GitManager:
    ssh_socket_dir = Path(f"/run/user/{os.getuid()}/gcr/ssh")

    def __init__(self, HOME: Path):
        self.home_path = HOME
        self.ssh_dir = HOME / ".ssh"
        self.known_hosts_file = self.ssh_dir / "known_hosts"

    def _run(self, cmd: list[str], check: bool = True) -> str:
        result = subprocess.run(
            cmd, text=True, capture_output=True, check=check
        ).stdout.strip()
        return result

    ############################
    # SSH / GitHub
    ############################
    def import_ssh(self, key_path: Path) -> None:
        if not self.ssh_socket_dir.exists():
            self.ssh_socket_dir.mkdir(parents=True, exist_ok=True)
            self._run(["systemctl", "--user", "enable", "gcr-ssh-agent.socket"])
            self._run(["systemctl", "--user", "start", "gcr-ssh-agent.socket"])
        self._run(["ssh-add", str(key_path)], check=True)
        log.info(f"SSH identity processed for: {key_path}")
        result = self._run(["ssh-add", "-l"], check=False)
        lines = result.splitlines()
        if not lines:
            log.error("Cannot scan user metadata without active SSH session.")
            return
        my_email = lines[0].split()[2]
        self._run(["git", "config", "--global", "user.email", my_email])
        my_name = input("Enter your global git user.name profile identity: ").strip()
        self._run(["git", "config", "--global", "user.name", my_name])
        log.info(f"Created Git configuration: {my_name} <{my_email}>")
        self.ssh_dir.mkdir(parents=True, exist_ok=True)
        scan = self._run(["ssh-keyscan", "-H", "github.com"], check=True)
        if scan:
            self.known_hosts_file.write_text(scan)
            log.info("Appended github.com validation signature to known_hosts")
        else:
            log.info("Could not -keyscan to verify GitHub host identity.")

    ############################
    # Clone repositories
    ############################
    def clone_repos(
        self,
        git_repos: GitReposConfiguration,
        dest: Path,
        ssh: bool = True,
    ) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        for git_user in git_repos.repositories:
            for repo_name, local_path in git_user.repos.items():
                repo_dest = dest / local_path
                if any(repo_dest.iterdir()):
                    log.warning(f"Repo destination {repo_dest} exists, skipping.")
                    continue
                try:
                    url = f"https://github.com/{git_user.username}/{repo_name}.git"
                    if ssh:
                        url = f"git@github.com:{git_user.username}/{repo_name}.git"
                    self._run(["git", "clone", url, str(repo_dest)], check=True)
                    log.info(f"Successfully cloned {repo_name} to {repo_dest}")
                except subprocess.CalledProcessError as e:
                    log.info(f"Failed to clone {repo_name}: {e}")


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
# DESKTOP ENVIRONMENT / APPS
############################
def set_folder_icons(custom_folder_icons: dict[Path, str]) -> None:
    run_dmc(
        [
            "gsettings",
            "set",
            "org.gnome.desktop.interface",
            "icon-theme",
            "WhiteSur-dark",
        ]
    )
    icon_dir: str = "/usr/share/icons/WhiteSur-dark/places/scalable"
    for folder, icon_name in custom_folder_icons.items():
        icon = Path(icon_dir) / f"{icon_name}.svg"
        folder.mkdir(parents=True, exist_ok=True)
        if icon.exists():
            run_dmc(
                ["gio", "set", str(folder), "metadata::custom-icon", f"file://{icon}"]
            )


def launch_apps(
    pass_path: Path,
    firefox_browser: str,
) -> None:
    """Copy the password, then launch configured apps and the browser."""
    password = pass_path.read_text().strip()
    pyperclip.copy(password)
    processes = [
        [firefox_browser],
        ["steam"],
        ["kitty", "protonmail-bridge-core", "-c"],
    ]
    for command in processes:
        if shutil.which(command[0]):
            subprocess.Popen(command).wait()


def scrcpy_setup(port: int = 5555) -> None:
    if not yes_no("Is your Android device actively mounted via USB interface?"):
        return
    lines = run_dmc(["adb", "shell", "ip", "route"]).stdout.splitlines()
    print("Route lines:", lines)
    ip = next(
        (
            line.split("src")[-1].strip()
            for line in lines
            if "wlan" in line and "src" in line
        ),
        None,
    )
    if not ip:
        log.warning("Device could not dynamically resolve IP from adb output.")
        return
    target = f"{ip}:{port}"
    log.info(f"Attempting handoff sync targeting interface address: {target}")
    msg = run_dmc(["adb", "connect", target])
    if msg:
        stdout = msg.stdout.strip() if msg.stdout else ""
        stderr = msg.stderr.strip() if msg.stderr else ""
        log.info(f"ADB connect stdout: {stdout.lower()}, stderr: {stderr.lower()}")


############################
# SYSTEM COMPONENT FLOWS
############################
def fix_network_stack() -> None:
    def iwctl_scan():
        result = run_dmc(["sudo", "iwctl", "station", "wlan0", "scan"], check=False)
        time.sleep(10)
        return result.returncode == 0 if result else False

    run_dmc(["rfkill", "unblock", "wlan"])
    run_dmc(["rfkill", "unblock", "bluetooth"])
    if Path("/etc/resolv.conf").is_symlink() and not ping():
        run_dmc(["sudo", "rm", "/etc/resolv.conf"])
        run_dmc(["sudo", "resolvconf", "-u"])
        run_dmc(["sudo", "systemctl", "restart", "iwd"])
        time.sleep(5)
        if not iwctl_scan():
            time.sleep(10)
            iwctl_scan()


############################
# MAIN FLOW
############################
def user_setup() -> None:
    HOME: Path = Path.home()

    run_dmc(["systemctl", "--user", "disable", "user_setup"])
    if shutil.which("zsh"):
        run_dmc(["chsh", "-s", "/usr/bin/zsh"], interactive=True)
        (HOME / ".local" / "share" / "zsh").mkdir(parents=True, exist_ok=True)
    fix_network_stack()
    if shutil.which("mariadb"):
        enable_mariadb()
    nc = NoahConfig.from_config(noah_json)
    nu = NoahUserProcessor(nc, HOME)
    run_dmc(
        ["uv", "add", "openmeteo-requests"],
        cwd=str(nu.HOME / ".local" / "bin" / "weather"),
    )
    if nu.gpg_paths:
        for path in nu.gpg_paths:
            if path.is_file():
                import_gpg(path)
    if nu.encrypted_dir and shutil.which("gocryptfs"):
        if not (nu.encrypted_dir / "gocryptfs.conf").exists():
            init_gocrypt(nu.encrypted_dir)
    if nu.dirs_icons:
        set_folder_icons(nu.dirs_icons)
    if nc.yazi_plugins and shutil.which("yazi"):
        for plugin in nc.yazi_plugins:
            run_dmc(["ya", "pkg", "add", plugin])
    if nc.git_repos_config and shutil.which("git"):
        gm = GitManager(HOME)
        use_ssh = False
        if nu.ssh_paths:
            for path in nu.ssh_paths:
                if path.is_file():
                    gm.import_ssh(path)
                    use_ssh = True
        gm.clone_repos(nc.git_repos_config, nu.HOME, ssh=use_ssh)
    if nc.dotdirs_to_link:
        dotdirs = nu.dotdirs_paths()
        PolkaDots(HOME, dotdirs).deploy()
    if shutil.which("scrcpy") and not (HOME / ".android" / "adbkey").is_file():
        scrcpy_setup()
    if nc.firefox_browser:
        if nu.masterpass_paths:
            if nu.masterpass_paths[0].is_file():
                launch_apps(nu.masterpass_paths[0], nc.firefox_browser)
    if shutil.which("gh"):
        run_dmc(
            ["gh", "auth", "login", "-h", "github.com", "-s", "delete_repo"],
            interactive=True,
        )
    if yes_no("Finished. Reboot system interface now?", default=False):
        run_dmc(["systemctl", "reboot"])
    else:
        log.info("System restart deferred manually.")


if __name__ == "__main__":
    user_setup()
