import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import getpass

HOME = Path.home()
GIT_USER = "acctux"
KEYS_DIR = HOME / ".ssh"
SSH_KEY = KEYS_DIR / "id_ed25519"
GPG_KEY = KEYS_DIR / "my_sec_gpg.asc"
ENC_DIR = HOME / "Documents" / "Encrypted"
GIT_DIR = HOME / "Lit"
DOTFILES_DIR = HOME / "Polka"
CUSTOM_FOLDERS = [HOME / "Games", GIT_DIR]
GIT_REPOS = [["Docs", GIT_DIR], ["Noah", GIT_DIR], ["Polka", HOME]]
CUSTOM_ICONS = [
    [HOME / "Games", "folder-games.svg"],
    [GIT_DIR / "Noah", "folder-root.svg"],
    [HOME / "Polka", "folder-html.svg"],
    [GIT_DIR, "folder-github.svg"],
    [ENC_DIR, "folder-locked.svg"],
]
CONFIG_DIR = HOME / ".config"
SHARE_DIR = HOME / ".local" / "share"
DIRECTORIES_TO_LINK = ["config/systemd/user", "config/nvim", "local/bin"]
BASE_DIR = GIT_DIR / "Docs/base"
INDIVIDUAL_DIRS = [
    (BASE_DIR / "fonts", SHARE_DIR / "fonts"),
    (BASE_DIR / "task", CONFIG_DIR / "task"),
    (BASE_DIR / "zsh", CONFIG_DIR / "zsh"),
]

# gh auth login -h github.com -s delete_repo


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


def run_sudo_commands():
    commands = [
        "chsh -s /usr/bin/zsh",
        "sudo mariadb-install-db --user=mysql --basedir=/usr --datadir=/var/lib/mysql",
        "sudo resolvconf -u",
        "sudo firewall-cmd --set-default-zone=block",
    ]
    for cmd in commands:
        result = run_cmd(cmd.split())
        if result and result.returncode != 0:
            log.error(f"Command failed: {cmd}")


def safe_remove(path: Path):
    if path.exists():
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
        log.info(f"Removed: {path}")


def link_path(src: Path, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    rel = os.path.relpath(src, dst.parent)
    if dst.is_symlink() and dst.readlink() == Path(rel):
        return False
    safe_remove(dst)
    dst.symlink_to(rel, target_is_directory=src.is_dir())
    log.info(f"Linked: {dst} → {rel}")
    return True


def dotted_destination(src: Path, source_root: Path, target_root: Path) -> Path:
    parts = src.relative_to(source_root).parts
    return target_root / Path("." + parts[0], *parts[1:])


def should_skip(path: Path, dirs_to_link) -> bool:
    return path.as_posix().startswith(".git") or any(
        path.is_relative_to(Path(d)) for d in dirs_to_link
    )


def link_dotfiles(dotfiles_dir, home_dir, dirs_to_link):
    linked = skipped = 0
    for src in dotfiles_dir.rglob("*"):
        if not src.is_file() or should_skip(
            src.relative_to(dotfiles_dir), dirs_to_link
        ):
            skipped += 1
            continue
        if link_path(src, dotted_destination(src, dotfiles_dir, home_dir)):
            linked += 1
        else:
            skipped += 1
    return linked, skipped


def link_directories(dotfiles_dir, home_dir, dirs_to_link):
    linked = skipped = 0
    for d in dirs_to_link:
        src = dotfiles_dir / d
        if src.is_dir():
            if link_path(src, dotted_destination(src, dotfiles_dir, home_dir)):
                linked += 1
            else:
                skipped += 1
        else:
            skipped += 1
    return linked, skipped


def link_individual_dirs(individual_dirs):
    linked = skipped = 0
    for src_dir, dst_dir in individual_dirs:
        if not src_dir.is_dir():
            log.error(f"Directory does not exist: {src_dir}")
            skipped += 1
            continue
        for src_file in src_dir.rglob("*"):
            if src_file.is_file():
                dst_file = dst_dir / src_file.relative_to(src_dir)
                if link_path(src_file, dst_file):
                    linked += 1
                else:
                    skipped += 1
    return linked, skipped


def deploy_dotfiles(dotfiles_dir, home_dir, dirs_to_link, individual_dirs):
    if not dotfiles_dir.is_dir():
        log.error(f"Dotfiles directory does not exist: {dotfiles_dir}")
        return
    lc, sc = link_dotfiles(dotfiles_dir, home_dir, dirs_to_link)
    lc2, sc2 = link_directories(dotfiles_dir, home_dir, dirs_to_link)
    lc3, sc3 = link_individual_dirs(individual_dirs)
    log.info(f"Linked: {lc + lc2 + lc3} | Skipped: {sc + sc2 + sc3}")
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
    fingerprint = keygen.stdout.strip().split()[1]
    ssh_list = run_cmd(["ssh-add", "-l"])
    if ssh_list and fingerprint in ssh_list.stdout:
        log.info("SSH key already imported.")
        return
    run_cmd(["ssh-add", str(key_path)], True)
    log.info(f"SSH key {fingerprint} added.")


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


def check_knownhosts():
    kh = KEYS_DIR / "known_hosts"
    kh.parent.mkdir(parents=True, exist_ok=True)
    if not kh.exists():
        kh.touch()
    content = kh.read_text(errors="ignore")
    if "github.com" not in content:
        scan = run_cmd(["ssh-keyscan", "-H", "github.com"], True)
        if scan and scan.stdout:
            kh.write_text(content + scan.stdout)


def clone_repos(git_repos):
    for name, path in git_repos:
        repo_dir = path / name / ".git"
        if not repo_dir.exists():
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
    tmp = Path("/tmp/whitesur-icons")
    if tmp.exists():
        shutil.rmtree(tmp)
    run_cmd(["git", "clone", "--depth=1", f"https://github.com/{repo}", str(tmp)], True)
    run_cmd(["bash", str(tmp / "install.sh")], True)
    for svg in [p for p in icon_dir.rglob("*.svg") if "scalable" not in p.parts]:
        text = svg.read_text()
        if old in text:
            svg.write_text(text.replace(old, new))


def set_folder_icons(custom_icons):
    folder_icon_dir = HOME / ".local/share/icons/WhiteSur-dark/places/scalable"
    for folder, icon in custom_icons:
        path = folder_icon_dir / icon
        if path.exists():
            run_cmd(
                ["gio", "set", str(folder), "metadata::custom-icon", f"file://{path}"],
                True,
            )


def main():
    run_sudo_commands()
    for f in CUSTOM_FOLDERS:
        f.mkdir(parents=True, exist_ok=True)
    if SSH_KEY.exists():
        import_ssh_key(SSH_KEY)
    if GPG_KEY.exists():
        import_gpg_key(GPG_KEY)
    initialize_gocrypt(ENC_DIR)
    if not (HOME / ".local/share/icons/WhiteSur-dark").exists():
        install_icon_theme()
    check_knownhosts()
    clone_repos(GIT_REPOS)
    set_folder_icons(CUSTOM_ICONS)
    log.info("Environment setup complete!")
    deploy_dotfiles(DOTFILES_DIR, HOME, DIRECTORIES_TO_LINK, INDIVIDUAL_DIRS)
    if input("Do you want to reboot the system? [y/N]: ").strip().lower() == "y":
        run_cmd(["systemctl", "reboot"], True)
    else:
        log.info("Reboot cancelled.")


if __name__ == "__main__":
    main()
