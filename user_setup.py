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


class PolkaConfiguration:
    def __init__(
        self,
        dotfiles_dir_str: str,
        dirs_to_link: list[str],
        secdots_dir_str: str | None = None,
        HOME: Path = Path.home(),
    ):
        self.HOME = HOME
        self.dotfiles_dir_str = dotfiles_dir_str
        self.secdots_dir_str = secdots_dir_str
        self.dirs_to_link = dirs_to_link
        self.dotfile_path = self.HOME / dotfiles_dir_str
        if secdots_dir_str:
            self.secdot_path = self.HOME / secdots_dir_str

    def link_path(self, src: Path, dst: Path) -> bool:
        """Create a symlink, replacing existing files/folders if necessary."""
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

    def dotted_destination(self, src: Path, source_dir: Path) -> Path:
        """Return the destination path with a dot-prefixed top-level folder."""
        parts = src.relative_to(source_dir).parts
        return self.HOME / Path("." + parts[0], *parts[1:])

    def collect_candidates(
        self, base_dir: Path, skip_base=[".git", "__pycache__", ".venv"]
    ) -> list[tuple[Path, Path]]:
        """Collect all files in base_dir, skipping unwanted dirs."""
        candidates = []
        for src in base_dir.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(base_dir)
            if rel.parts[0] in skip_base:
                continue
            if any(rel.parts[0] == d.split("/")[0] for d in self.dirs_to_link):
                continue
            candidates.append((src, self.dotted_destination(src, base_dir)))
        return candidates

    def file_candidates(self) -> list[tuple[Path, Path]]:
        """Get all candidate files and directories for linking from dotfiles and secdots."""
        candidates: list[tuple[Path, Path]] = []
        candidates.extend(self.collect_candidates(self.dotfile_path))
        if self.secdot_path:
            candidates.extend(self.collect_candidates(self.secdot_path))
        for base in [self.dotfile_path, self.secdot_path]:
            for d in self.dirs_to_link:
                src = base / d
                if src.exists():
                    candidates.append((src, self.dotted_destination(src, base)))
        return candidates

    def deploy(self):
        """Automate the linking of all dotfiles."""
        if not self.dotfile_path.is_dir():
            log.error(f"Dotfiles directory not found: {self.dotfile_path}")
            return

        linked = 0
        for src, dst in self.file_candidates():
            if self.link_path(src, dst):
                linked += 1

        if shutil.which("hyprctl"):
            subprocess.run(["hyprctl", "reload"], check=False)
            log.info("Hyprland reloaded")

        log.info(f"Total linked: {linked}")


@dataclass(slots=True)
class NoahUserProcessor:
    data: NoahConfig
    username: str | None = None
    HOME = Path.home()
    ENCRYPTED: Path | None = None
    DOTS: Path | None = None
    SEC_DOTS: Path | None = None
    ssh_path: Path | None = None
    gpg_path: Path | None = None
    masterpass_path: Path | None = None
    dirs_icons: dict[Path, str] = field(init=False, default_factory=dict)
    key_copy_config: KeyCopyConfiguration | None = None

    def __post_init__(self):
        self.username = self.username or pwd.getpwuid(os.getuid()).pw_name
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


###########################################################
# ENTRY
##########################################
def enter_pass(prompt_str: str) -> str:
    """Secure masked entry utility for credential setting."""
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
    def __init__(self, home_path: Path, ssh_socket_dir: Path | None = None):
        self.home_path = home_path
        self.ssh_dir = home_path / ".ssh"
        self.known_hosts_file = self.ssh_dir / "known_hosts"
        self.ssh_socket_dir = ssh_socket_dir or Path(f"/run/user/{os.getuid()}/gcr/ssh")

    def _run(self, cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
        """Wrapper around subprocess.run with logging."""
        return subprocess.run(cmd, text=True, capture_output=True, check=check)

    ############################
    # SSH / GitHub
    ############################
    def import_ssh(self, key_path: Path) -> None:
        def git_config_get(key: str) -> str | None:
            result = self._run(["git", "config", "--global", "--get", key], check=False)
            return result.stdout.strip() if result.stdout else None

        if git_config_get("user.email") and git_config_get("user.name"):
            print("Global Git profile already configured.")
            return
        if not self.ssh_socket_dir.exists():
            self.ssh_socket_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(self.ssh_socket_dir, 0o700)
            self._run(["systemctl", "--user", "enable", "gcr-ssh-agent.socket"])
            self._run(["systemctl", "--user", "start", "gcr-ssh-agent.socket"])

        if key_path.exists():
            os.chmod(key_path, 0o600)

        self._run(["ssh-add", str(key_path)], check=True)
        print(f"SSH identity processed for: {key_path}")

        result = self._run(["ssh-add", "-l"], check=False)
        lines = result.stdout.strip().splitlines() if result.stdout else []
        if not lines:
            print("Cannot scan user metadata without active SSH session.")
            return

        my_email = lines[0].split()[2]
        my_name = input("Enter your global git user.name profile identity: ").strip()
        self._run(["git", "config", "--global", "user.email", my_email])
        self._run(["git", "config", "--global", "user.name", my_name])
        print(f"Created Git configuration: {my_name} <{my_email}>")
        self.ssh_dir.mkdir(parents=True, exist_ok=True)
        self.known_hosts_file.touch(exist_ok=True)
        content = self.known_hosts_file.read_text(errors="ignore")
        if "github.com" not in content:
            scan = self._run(["ssh-keyscan", "-H", "github.com"], check=True)
            if scan.stdout:
                self.known_hosts_file.write_text(content + scan.stdout)
                print("Appended github.com validation signature to known_hosts")
            else:
                print("Could not -keyscan to verify GitHub host identity.")

    ############################
    # Clone repositories
    ############################
    def clone_repos(
        self, git_repos: GitReposConfiguration, dest: Path, ssh: bool = True
    ) -> None:
        def get_url(user: str, repo: str) -> str:
            return (
                f"git@github.com:{user}/{repo}.git"
                if ssh
                else f"https://github.com/{user}/{repo}.git"
            )

        dest.mkdir(parents=True, exist_ok=True)
        for git_user in git_repos.repositories:
            for repo_name, local_path in git_user.repos.items():
                repo_dest = dest / local_path
                if any(repo_dest.iterdir()):
                    print(f"Repository destination '{repo_dest}' exists, skipping.")
                    continue
                try:
                    self._run(
                        [
                            "git",
                            "clone",
                            get_url(git_user.username, repo_name),
                            str(repo_dest),
                        ],
                        check=True,
                    )
                    print(f"Successfully cloned {repo_name} to {repo_dest}")
                except subprocess.CalledProcessError as e:
                    print(f"Failed to clone {repo_name}: {e}")


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
def set_folder_icons(
    custom_folder_icons: dict[Path, str],
    icon_dir: str = "/usr/share/icons/WhiteSur-dark/places/scalable",
) -> None:
    run_dmc(
        [
            "gsettings",
            "set",
            "org.gnome.desktop.interface",
            "icon-theme",
            "'WhiteSur-dark'",
        ]
    )
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
        log.info(
            "Please assert active connectivity via hardwire link lines before running network bridge."
        )
        return

    route_output = run_dmc(["adb", "shell", "ip", "route"])
    lines = (
        route_output.stdout.splitlines() if route_output and route_output.stdout else []
    )
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
    if shutil.which("tuned"):
        run_dmc(["tuned-adm", "profile", "laptop-ac-powersave"])
    if shutil.which("mariadb"):
        enable_mariadb()
    nc = NoahConfig.from_config(noah_json)
    nu = NoahUserProcessor(nc)
    run_dmc(
        ["uv", "add", "openmeteo-requests"],
        cwd=str(nu.HOME / ".local" / "bin" / "weather"),
    )
    if nu.gpg_path and nu.gpg_path.is_file():
        import_gpg(nu.gpg_path)
    if nu.ENCRYPTED and shutil.which("gocryptfs"):
        if not (nu.ENCRYPTED / "gocryptfs.conf").exists():
            init_gocrypt(nu.ENCRYPTED)
    set_folder_icons(nu.dirs_icons)
    if nc.yazi_plugins:
        for plugin in nc.yazi_plugins:
            run_dmc(["ya", "pkg", "add", plugin])
    if nc.git_repos_config:
        gm = GitManager(HOME)
        use_ssh = False
        if nu.ssh_path and nu.ssh_path.is_file():
            gm.import_ssh(nu.ssh_path)
            use_ssh = True
        gm.clone_repos(nc.git_repos_config, nu.HOME, ssh=use_ssh)
    if nu.DOTS and any(nu.DOTS.iterdir()):
        if nc.dotfiles_config and nc.dotfiles_config.dotfiles_dir:
            if nc.dotfiles_config.secret_dotfiles_dir:
                polka = PolkaConfiguration(
                    dotfiles_dir_str=nc.dotfiles_config.dotfiles_dir,
                    secdots_dir_str=nc.dotfiles_config.secret_dotfiles_dir,
                    dirs_to_link=nc.dotfiles_config.dirs_to_link,
                )
                polka.deploy()
    if shutil.which("scrcpy") and not (HOME / ".android" / "adbkey").is_file():
        scrcpy_setup()
    if nu.masterpass_path and nc.firefox_browser:
        launch_apps(nu.masterpass_path, nc.firefox_browser)
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
