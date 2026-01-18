import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import getpass
import pyperclip

HOME = Path.home()
DESK_DIR = HOME / "Desktop"
GIT_USER = "acctux"
KEYS_DIR = HOME / ".ssh"
SSH_KEY = KEYS_DIR / "id_ed25519"
GPG_KEY = KEYS_DIR / "my_sec_gpg.asc"
ENC_DIR = DESK_DIR / "Encrypted"
GIT_DIR = HOME / "Lit"
DOT_DIR = HOME / "Polka"
GIT_REPOS = [["Docs", GIT_DIR], ["Noah", GIT_DIR], ["Polka", HOME]]
CUSTOM_ICONS = [
    [DESK_DIR / "Games", "folder-games.svg"],
    [GIT_DIR, "folder-github.svg"],
    [GIT_DIR / "Noah", "folder-root.svg"],
    [GIT_DIR / "Docs", "folder-bookmark.svg"],
    [DOT_DIR, "folder-html.svg"],
    [ENC_DIR, "folder-locked.svg"],
]
CONFIG_DIR = HOME / ".config"
SHARE_DIR = HOME / ".local" / "share"
DIR_TO_LINK = ["config/systemd/user", "config/nvim", "local/bin"]
BASE_DIR = GIT_DIR / "Docs/base"
SEC_DOTS = [
    (BASE_DIR / "fonts", SHARE_DIR / "fonts"),
    (BASE_DIR / "task", CONFIG_DIR / "task"),
    (BASE_DIR / "zsh", CONFIG_DIR / "zsh"),
]
PASSWORD_FILE = KEYS_DIR / "pass.txt"
CACHE_FILE = HOME / ".cache" / "first_done"


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.INFO: "\033[34m",
        logging.ERROR: "\033[31m",
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        return f"{color}{super().format(record)}{self.RESET}"


def get_logger(name):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ColorFormatter("%(name)s %(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


log = get_logger("Noah")


def run_cmd(cmd: list[str], check=False, input_text: str | None = None):
    try:
        log.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            text=True,
            check=check,
            capture_output=True,
            input=input_text,
        )
        if result.stdout:
            log.info(f"stdout: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        log.error(f"Command failed: {' '.join(cmd)} (exit {e.returncode})")
        if e.stdout:
            log.info(f"stdout: {e.stdout.strip()}")
        if e.stderr:
            log.error(f"stderr: {e.stderr.strip()}")
        return e


def run_cmd_interactive(cmd: list[str], check: bool = True) -> int:
    log.info(f"Running (interactive): {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
        text=True,
    )
    returncode = proc.wait()
    if check and returncode != 0:
        raise subprocess.CalledProcessError(returncode, cmd)
    return returncode


def run_sudo_commands():
    commands = [
        "sudo mariadb-install-db --user=mysql --basedir=/usr --datadir=/var/lib/mysql",
        "sudo resolvconf -u",
        "sudo firewall-cmd --set-default-zone=block",
    ]
    for cmd in commands:
        result = run_cmd(cmd.split(), True)
        if result and result.returncode != 0:
            log.error(f"Command failed: {cmd}")


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


def dotted_destination(src: Path, source_root: Path, target_root: Path) -> Path:
    parts = src.relative_to(source_root).parts
    return target_root / Path("." + parts[0], *parts[1:])


def deploy_dotfiles(dotfiles_dir, home_dir, dirs_to_link, individual_dirs):
    linked = skipped = 0
    if not dotfiles_dir.is_dir():
        log.error(f"Dotfiles directory does not exist: {dotfiles_dir}")
        return
    for src in dotfiles_dir.rglob("*"):
        if not src.is_file():
            skipped += 1
            continue
        if src.relative_to(dotfiles_dir).as_posix().startswith(".git") or any(
            src.relative_to(dotfiles_dir).is_relative_to(Path(d)) for d in dirs_to_link
        ):
            skipped += 1
            continue
        dst = dotted_destination(src, dotfiles_dir, home_dir)
        if link_path(src, dst):
            linked += 1
        else:
            skipped += 1
    for d in dirs_to_link:
        src = dotfiles_dir / d
        if not src.is_dir():
            log.error(f"{src} not found.")
            continue
        dst = dotted_destination(src, dotfiles_dir, home_dir)
        if link_path(src, dst):
            linked += 1
        else:
            skipped += 1
    for src_dir, dst_dir in individual_dirs:
        if not src_dir.is_dir():
            log.error(f"Directory does not exist: {src_dir}")
            continue
        for src_file in src_dir.rglob("*"):
            if not src_file.is_file():
                continue
            dst_file = dst_dir / src_file.relative_to(src_dir)
            if link_path(src_file, dst_file):
                linked += 1
            else:
                skipped += 1
    log.info(f"Linked:{linked} | Skipped:{skipped}")
    if shutil.which("hyprctl"):
        run_cmd(["hyprctl", "reload"])


def import_ssh_key(key_path: Path):
    if key_path.stat().st_mode & 0o777 != 0o600:
        os.chmod(key_path, 0o600)
    socket = f"/run/user/{os.getuid()}/gcr/ssh"
    os.environ["SSH_AUTH_SOCK"] = socket
    if not Path(socket).exists():
        run_cmd(["systemctl", "--user", "enable", "gcr-ssh-agent.socket"])
        run_cmd(["systemctl", "--user", "start", "gcr-ssh-agent.socket"])
    keygen = run_cmd(["ssh-keygen", "-lf", str(key_path)])
    if not keygen or not keygen.stdout:
        log.error("Failed to read SSH key fingerprint.")
        return
    ssh_list = run_cmd(["ssh-add", "-l"])
    if ssh_list and keygen.stdout.strip().split()[1] in ssh_list.stdout:
        log.info("SSH key already imported.")
        return
    run_cmd(["ssh-add", str(key_path)], True)
    log.info("SSH key added.")


def import_gpg_key(gpg_key):
    show = run_cmd(
        [
            "gpg",
            "--import-options",
            "show-only",
            "--import",
            "--with-colons",
            str(gpg_key),
        ]
    )
    fingerprint = next(
        (
            line.split(":")[9]
            for line in show.stdout.splitlines()
            if line.startswith("fpr")
        ),
        None,
    )
    if not fingerprint:
        log.error("Could not extract GPG fingerprint.")
        return
    if run_cmd(["gpg", "--list-keys", fingerprint]).returncode == 0:
        log.info(f"GPG key {fingerprint} already imported.")
        return
    if run_cmd(["gpg", "--import", str(gpg_key)], check=True) is None:
        log.error("Failed to import GPG key.")
        return
    trust = run_cmd(
        ["gpg", "--import-ownertrust"],
        input_text=f"{fingerprint}:6:\n",
    )
    if not trust or trust.returncode != 0:
        log.error("Failed to set trust for GPG key.")
        return
    log.info(f"GPG key imported and trusted (ultimate): {fingerprint}")


def initialize_gocrypt(enc_dir: Path):
    enc_dir.mkdir(parents=True, exist_ok=True)
    while True:
        pw1 = getpass.getpass("Enter new gocryptfs password: ")
        pw2 = getpass.getpass("Confirm password: ")
        if pw1 == pw2 and pw1:
            break
        print("Passwords do not match or empty. Try again.\n")
    run_cmd(
        ["gocryptfs", "-init", "--passfile", "/dev/stdin", str(enc_dir)],
        check=True,
        input_text=pw1,
    )


def clone_repos(git_repos, keys_dir):
    kh = keys_dir / "known_hosts"
    kh.parent.mkdir(parents=True, exist_ok=True)
    if not kh.exists():
        kh.touch()
    content = kh.read_text(errors="ignore")
    if "github.com" not in content:
        scan = run_cmd(["ssh-keyscan", "-H", "github.com"], True)
        if scan and scan.stdout:
            kh.write_text(content + scan.stdout)
    for name, path in git_repos:
        if not (path / name / ".git").exists():
            path.mkdir(parents=True, exist_ok=True)
            run_cmd(
                [
                    "git",
                    "clone",
                    f"git@github.com:{GIT_USER}/{name}.git",
                    str(path / name),
                ],
                True,
            )


def install_icon_theme(
    old="#ffffff", new="#F4F5F6", repo="vinceliuice/WhiteSur-icon-theme.git"
):
    icon_dir = HOME / ".local/share/icons/WhiteSur-dark"
    tmp = "/tmp/whitesur-icons"
    if Path(tmp).exists():
        shutil.rmtree(tmp)
    run_cmd(["git", "clone", "--depth=1", f"https://github.com/{repo}", tmp], True)
    run_cmd(["bash", f"{tmp}/install.sh"], True)
    for svg in [p for p in icon_dir.rglob("*.svg") if "scalable" not in p.parts]:
        text = svg.read_text()
        if old in text:
            svg.write_text(text.replace(old, new))


def set_folder_icons(custom_icons):
    folder_icon_dir = HOME / ".local/share/icons/WhiteSur-dark/places/scalable"
    for folder, icon in custom_icons:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder_icon_dir / icon
        if path.exists():
            run_cmd(
                ["gio", "set", str(folder), "metadata::custom-icon", f"file://{path}"],
                True,
            )


def setup_service(
    user_script: str = "d.py",
) -> None:
    run_script = HOME / user_script
    service_dir = HOME / ".config/systemd/user"
    service_name = f"{run_script.stem}.service"
    service_path = service_dir / service_name
    service_path.write_text(
        f"""[Unit]
Description=Open Alacritty running {user_script} on login
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/usr/bin/alacritty -e python {run_script}
Restart=no

[Install]
WantedBy=graphical-session.target
"""
    )
    run_cmd(["systemctl", "--user", "enable", service_name])


def pass_and_input():
    password = PASSWORD_FILE.read_text().strip()
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


def main():
    if not CACHE_FILE.exists():
        cmd = ["chsh", "-s", "/usr/bin/zsh"]
        run_cmd_interactive(cmd)
        run_sudo_commands()
        if SSH_KEY.exists():
            import_ssh_key(SSH_KEY)
        if GPG_KEY.exists():
            import_gpg_key(GPG_KEY)
        initialize_gocrypt(ENC_DIR)
        if not (HOME / ".local/share/icons/WhiteSur-dark").exists():
            install_icon_theme()
        set_folder_icons(CUSTOM_ICONS)
        clone_repos(GIT_REPOS, KEYS_DIR)
        deploy_dotfiles(DOT_DIR, HOME, DIR_TO_LINK, SEC_DOTS)
        setup_service()
        CACHE_FILE.touch()
        if input("Do you want to reboot the system? [Y/n]: ").strip().lower() == "n":
            log.info("Reboot cancelled.")
        else:
            run_cmd(["systemctl", "reboot"], True)
    else:
        pass_and_input()
        launch_apps()
        cmd = ["gh", "auth", "login", "-h", "github.com", "-s", "delete_repo"]
        run_cmd_interactive(cmd)


if __name__ == "__main__":
    main()
