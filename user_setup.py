#!/usr/bin/env python3
import os
import pwd
import shutil
import subprocess
import time
from dataclasses import dataclass
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
    try:
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
    except Exception:
        return False


class PolkaDots:
    HOME = Path.home()

    def __init__(self, dotfiles_dirs: list[Path]):
        self.dotfiles_paths = dotfiles_dirs
        self.skip_base = {".git", "__pycache__", ".venv"}
        self.skip_name = {".gitignore"}

    def deploy(self):
        linked = 0
        for src_dir in self.dotfiles_paths:
            if not src_dir.is_dir():
                log.warning(f"{src_dir} not found, skipping.")
                continue
            for src in src_dir.rglob("*"):
                if not src.is_file():
                    continue
                parts = src.relative_to(src_dir).parts
                for part in parts:
                    if part in self.skip_base:
                        continue
                if parts[-1] in self.skip_name:
                    continue
                dst = self.HOME / Path("." + parts[0], *parts[1:])
                dst.parent.mkdir(parents=True, exist_ok=True)
                rel = os.path.relpath(src, dst.parent)
                if dst.is_symlink() and os.readlink(dst) == rel:
                    continue
                if dst.exists() or dst.is_symlink():
                    dst.unlink()
                    log.info(f"Removed: {dst}")
                dst.symlink_to(rel)
                log.info(f"Linked: {dst} → {rel}")
                linked += 1
        log.info(f"Total linked: {linked}")
        subprocess.run(["hyprctl", "reload"], check=False)
        log.info("Hyprland reloaded")


@dataclass(slots=True)
class NoahUserProcessor:
    HOME: Path = Path.home()
    username = pwd.getpwuid(os.getuid()).pw_name

    def __init__(self, data: NoahConfig) -> None:
        self.data = data
        self.encrypted_dir = self._path(self.HOME, data.encrypted_dir)
        self.dotdirs_to_link = data.dotdirs_to_link
        self.ssh_paths: list[Path]
        self.gpg_paths: list[Path]
        self.masterpass_paths: list[Path]
        self.dirs_icons = self._dirs_icons()
        if cc := data.copy_config:
            self.ssh_paths = cc.user_space_resolve_by_type("ssh", self.HOME)
            self.gpg_paths = cc.user_space_resolve_by_type("gpg", self.HOME)
            self.masterpass_paths = cc.user_space_resolve_by_type(
                "masterpass", self.HOME
            )

    def _path(self, base: Path, value: str | None) -> Path | None:
        if value is None:
            return None
        return base / value

    def _dirs_icons(self) -> dict[Path, str]:
        result: dict[Path, str] = {}
        config = self.data.dirs_icons
        if not config:
            return result
        for path, icon in config.items():
            resolved = self._path(self.HOME, path)
            if resolved:
                result[resolved] = icon
        return result

    def dotdirs_paths(self) -> list[Path]:
        if not self.dotdirs_to_link:
            return []
        return [self.HOME / d for d in self.dotdirs_to_link]


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
def import_ssh(key_path: Path) -> None:
    socket_path = Path(f"/run/user/{os.getuid()}/gcr/ssh")
    if not socket_path.exists():
        socket_path.mkdir(parents=True, exist_ok=True)
        os.chmod(socket_path, 0o700)  # Owner only
        run_dmc(["systemctl", "--user", "enable", "gcr-ssh-agent.socket"])
        run_dmc(["systemctl", "--user", "start", "gcr-ssh-agent.socket"])
    if key_path.exists():
        os.chmod(key_path, 0o600)  # Owner read/write only
    run_dmc(["ssh-add", str(key_path)], check=True)
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


class GitManager:
    def __init__(self, home_path: Path):
        self.home_path = home_path
        self.ssh_dir = home_path / ".ssh"
        self.known_hosts_file = self.ssh_dir / "known_hosts"
        self.ssh_socket_dir = Path(f"/run/user/{os.getuid()}/gcr/ssh")

    def _run(self, cmd: list[str], check: bool = True) -> str:
        result = subprocess.run(
            cmd, text=True, capture_output=True, check=check
        ).stdout.strip()
        return result

    ############################
    # SSH / GitHub
    ############################
    def import_ssh(self, key_path: Path) -> None:
        def git_config_get(key: str) -> str | None:
            result = self._run(["git", "config", "--global", "--get", key], check=False)
            return result

        if git_config_get("user.email") and git_config_get("user.name"):
            log.info("Global Git profile already configured.")
            return
        if not self.ssh_socket_dir.exists():
            self.ssh_socket_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(self.ssh_socket_dir, 0o700)
            self._run(["systemctl", "--user", "enable", "gcr-ssh-agent.socket"])
            self._run(["systemctl", "--user", "start", "gcr-ssh-agent.socket"])
        if key_path.exists():
            os.chmod(key_path, 0o600)
        self._run(["ssh-add", str(key_path)], check=True)
        log.info(f"SSH identity processed for: {key_path}")
        result = self._run(["ssh-add", "-l"], check=False)
        lines = result.splitlines()
        if not lines:
            log.error("Cannot scan user metadata without active SSH session.")
            return
        my_email = lines[0].split()[2]
        my_name = input("Enter your global git user.name profile identity: ").strip()
        self._run(["git", "config", "--global", "user.email", my_email])
        self._run(["git", "config", "--global", "user.name", my_name])
        log.info(f"Created Git configuration: {my_name} <{my_email}>")
        self.ssh_dir.mkdir(parents=True, exist_ok=True)
        self.known_hosts_file.touch(exist_ok=True)
        content = self.known_hosts_file.read_text(errors="ignore")
        if "github.com" not in content:
            scan = self._run(["ssh-keyscan", "-H", "github.com"], check=True)
            if scan:
                self.known_hosts_file.write_text(content + scan)
                log.info("Appended github.com validation signature to known_hosts")
            else:
                log.info("Could not -keyscan to verify GitHub host identity.")

    ############################
    # Clone repositories
    ############################
    def clone_repos(
        self, git_repos: GitReposConfiguration, dest: Path, ssh: bool = True
    ) -> None:
        def get_url(user: str, repo: str) -> str:
            url = f"https://github.com/{user}/{repo}.git"
            if ssh:
                url = f"git@github.com:{user}/{repo}.git"
            return url

        dest.mkdir(parents=True, exist_ok=True)
        for git_user in git_repos.repositories:
            for repo_name, local_path in git_user.repos.items():
                repo_dest = dest / local_path
                if any(repo_dest.iterdir()):
                    log.warning(f"Repo destination {repo_dest} exists, skipping.")
                    continue
                url = get_url(git_user.username, repo_name)
                try:
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
    cmd = [
        "gsettings",
        "set",
        "org.gnome.desktop.interface",
        "icon-theme",
        "'WhiteSur-dark'",
    ]
    run_dmc(cmd)
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
    apps: list[list[str]] = [["steam"], ["kitty", "protonmail-bridge-core", "--cli"]],
) -> None:
    password = pass_path.read_text().strip()
    pyperclip.copy(password)
    apps.append(
        [
            firefox_browser,
            "https://addons.mozilla.org/en-US/firefox/addon/proton-pass/",
        ]
    )
    for process in apps:
        if shutil.which(process[0]):
            subprocess.Popen(process).wait()


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
def user_setup(HOME: Path = Path.home()) -> None:
    run_dmc(["systemctl", "--user", "disable", "user_setup"])
    if shutil.which("zsh"):
        run_dmc(["chsh", "-s", "/usr/bin/zsh"], interactive=True)
    fix_network_stack()
    if shutil.which("mariadb"):
        enable_mariadb()
    nc = NoahConfig.from_config(noah_json)
    nu = NoahUserProcessor(nc)
    run_dmc(
        ["uv", "add", "openmeteo-requests"],
        cwd=str(nu.HOME / ".local" / "bin" / "weather"),
    )
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
        for path in nu.ssh_paths:
            if path.is_file():
                gm.import_ssh(path)
                use_ssh = True
        gm.clone_repos(nc.git_repos_config, nu.HOME, ssh=use_ssh)
    if nc.dotdirs_to_link:
        dotdirs = nu.dotdirs_paths()
        PolkaDots(dotdirs).deploy()
    if shutil.which("scrcpy") and not (HOME / ".android" / "adbkey").is_file():
        scrcpy_setup()
    if nc.firefox_browser:
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
