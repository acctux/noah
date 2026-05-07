#!/usr/bin/env python3
from getpass import getpass
import os
from pathlib import Path
import time
import gnupg
import shutil
import subprocess
import pyperclip
from utils import log, ping, ask_pass, yes_no, run_dmc


from dataclasses import dataclass, field


@dataclass
class UserConfig:
    ###########################################################
    # USER CONFIG
    ###########################################################
    android: bool = True
    firewalld: bool = True
    firefox_browser: str = "floorp"
    ###########################################################
    # HOME & PATHS
    ###########################################################
    HOME: Path = field(default_factory=Path.home)
    DESKTOP: Path = field(init=False)
    ENCRYPTED: Path = field(init=False)
    GIT_DIR: Path = field(init=False)
    dots_path: Path = field(init=False)
    DOCS: Path = field(init=False)
    ssh_path: Path = field(init=False)
    gpg_path: Path = field(init=False)
    masterpass_path: Path = field(init=False)
    ###########################################################
    # REPOSITORIES
    ###########################################################
    repos: list[str] = field(default_factory=lambda: ["noah", "polka"])
    private_repos: list[str] = field(default_factory=lambda: ["Docs"])
    ###########################################################
    # DOTFILES
    ###########################################################
    dirs_to_link: list[str] = field(default_factory=lambda: ["local/bin"])
    sec_dir: Path = field(init=False)
    ind_dirs: dict[str, Path] = field(init=False)
    ###########################################################
    # ICONS
    ###########################################################
    dirs_icons: dict[Path, str] = field(init=False)
    ###########################################################
    # YAZI PLUGINS
    ###########################################################
    yazi_plugins: list[str] = field(
        default_factory=lambda: [
            "yazi-rs/plugins:jump-to-char",
            "uhs-robert/sshfs",
            "boydaihungst/gvfs",
            "uhs-robert/recycle-bin",
            "h-hg/yamb",
        ]
    )

    def __post_init__(self):
        # Dependent paths
        self.DESKTOP = self.HOME / "Desktop"
        self.ENCRYPTED = self.DESKTOP / "Encrypted"
        self.GIT_DIR = self.HOME / "Lit"
        self.DOTS = self.GIT_DIR / "polka"
        self.DOCS = self.GIT_DIR / "Docs"

        self.ssh_path = self.HOME / ".ssh" / "id_ed25519"
        self.gpg_path = self.HOME / ".gnupg" / "my_sec_gpg.asc"
        self.masterpass_path = self.HOME / ".ssh" / "pass.txt"

        self.sec_dir = self.DOCS / "base"
        self.ind_dirs = {
            "fonts": self.HOME / ".local" / "share",
            "task": self.HOME / ".config",
            "zsh": self.HOME / ".config",
            "git": self.HOME / ".config",
            "gh": self.HOME / ".config",
        }
        self.dirs_icons = {
            self.DESKTOP / "Games": "folder-games",
            self.ENCRYPTED: "folder-locked",
            self.GIT_DIR: "folder-github",
            self.GIT_DIR / "noah": "folder-root",
            self.DOCS: "folder-bookmark",
            self.dots_path: "folder-html",
        }

    ###########################################################
    # HELPER METHODS
    ###########################################################
    def get_ind_dir(self, name: str) -> Path | None:
        return self.ind_dirs.get(name)

    def repo_path(self, repo_name: str) -> Path:
        return self.GIT_DIR / repo_name


def iwctl_scan() -> bool:
    result = run_dmc(["sudo", "iwctl", "station", "wlan0", "scan"], check=False)
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
    ind_dirs: dict[str, Path],
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
    for src_name, dst_dir in ind_dirs.items():
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
    run_dmc(["hyprctl", "reload"])
    log.info(f"Linked: {linked}")


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
    import_result = gpg.import_keys(
        key_data, passphrase=ask_pass("GPG Password: ", False, 6)
    )
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
        result = run_dmc(["git", "clone", url(repo), str(repo_path)], check=False)
        if result.returncode == 0:
            log.info(f"Cloned {repo}")
        else:
            log.warning(f"Failed to clone {repo}")


def configure_git() -> None:
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


def launch_apps(apps=["floorp", "protonmail-bridge", "betterbird", "steam"]):
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
def main():
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
    uc = UserConfig
    if shutil.which("mariadb"):
        enable_mariadb(uc.user_name)
    if uc.ssh_path.exists():
        import_ssh(uc.ssh_path)
        configure_git()
        ensure_github_known_hosts(uc.HOME)
        clone_repos(uc.git_user, uc.repos + uc.private_repos, uc.GIT_DIR, ssh=True)
    else:
        clone_repos(uc.git_user, uc.repos, uc.GIT_DIR, ssh=False)
    if uc.gpg_path and not uc.gpg_path.exists():
        import_gpg(uc.gpg_path)
    if uc.ENCRYPTED and not (uc.ENCRYPTED / "gocryptfs.conf").exists():
        if shutil.which("gocryptfs"):
            init_gocrypt(uc.ENCRYPTED)
    if uc.dirs_icons:
        set_folder_icons(uc.dirs_icons)
    for plugin in uc.yazi_plugins:
        run_dmc(["ya", "pkg", "add", plugin])
    if any((uc.dots_path).iterdir()):
        deploy_dotfiles(uc.HOME, uc.dots_path, uc.dirs_to_link, uc.ind_dirs, uc.sec_dir)
        run_dmc(
            ["uv", "add", "openmeteo-requests"],
            cwd=f"/home/{uc.user_name}/.local/bin/weather",
        )
    if uc.android:
        scrcpy_setup()
    if uc.masterpass_path.is_file():
        pass_and_input(uc.masterpass_path)
        launch_apps()
    run_dmc(
        ["gh", "auth", "login", "-h", "github.com", "-s", "delete_repo"],
        interactive=True,
    )
    for d in [(uc.HOME / "archinstall")]:
        if d.exists():
            shutil.rmtree(d)
    if yes_no("Reboot now?", default=False):
        run_dmc(["systemctl", "reboot"])
        log.info("Reboot cancelled.")
        return


if __name__ == "__main__":
    main()
