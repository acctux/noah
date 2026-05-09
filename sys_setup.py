#!/usr/bin/env python3
from typing import Any
from pathlib import Path
import sys
import time
import subprocess
import json
import re
import shutil
import pwd
import os
import extraconfig as ec
from getpass import getpass
import logging
from textwrap import dedent
from dataclasses import dataclass, field


#########################
# LOG
#########################
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",  # cyan
        logging.INFO: "\033[34m",  # blue
        logging.WARNING: "\033[93m",  # yellow
        logging.ERROR: "\033[31m",  # red
        logging.CRITICAL: "\033[41m",  # red background
    }
    RESET = "\033[0m"
    UNDERLINE = "\033[4m"
    NAME_COLOR = "\033[93m"  # yellow

    def format(self, record):
        colored_name = f"{self.NAME_COLOR}{record.name}{self.RESET}"
        level_color = self.COLORS.get(record.levelno, "")
        colored_message = f"{level_color}{record.getMessage()}{self.RESET}"
        message = f"{colored_name}: {colored_message}"
        if record.levelno == logging.CRITICAL:
            message = f"{self.UNDERLINE}{message}{self.RESET}"
        return message


def get_logger(log_name: str | None = None, level=logging.INFO):
    logger = logging.getLogger(log_name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ColorFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


log = get_logger("Noah")


def parse_list(cls, values):
    return [cls.parse_arg(v) for v in (values or [])]


@dataclass(slots=True)
class GitRepos:
    user: str = ""
    repos: dict = field(default_factory=dict)

    @classmethod
    def parse_arg(cls, data):
        return cls(
            user=data.get("user", ""),
            repos=data.get("repos", {}),
        )


@dataclass(slots=True)
class UsbFileCopy:
    target_dir: str = ""
    files: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CopyGroup:
    source: str = ""
    to_cp_list: list[UsbFileCopy] = field(default_factory=list)

    @classmethod
    def parse_arg(cls, data: dict):
        data = data or {}

        return cls(
            source=data.get("source", ""),
            to_cp_list=[
                UsbFileCopy(
                    target_dir=target_dir,
                    files=files,
                )
                for target_dir, files in data.get(
                    "destinations",
                    {},
                ).items()
            ],
        )


@dataclass(slots=True)
class UsrSrv:
    source: str = ""
    target: str = ""
    services: list = field(default_factory=list)


@dataclass(slots=True)
class UserServices:
    root_owned: list[UsrSrv] = field(default_factory=list)
    user_owned: list[UsrSrv] = field(default_factory=list)

    @classmethod
    def parse_arg(cls, data):
        data = data or {}

        return cls(
            root_owned=[
                UsrSrv(
                    source="root",
                    target=target,
                    services=services,
                )
                for target, services in data.get("root_owned", {}).items()
            ],
            user_owned=[
                UsrSrv(
                    source="user",
                    target=target,
                    services=services,
                )
                for target, services in data.get("user_owned", {}).items()
            ],
        )


# =========================================================
# Main config
# =========================================================
@dataclass(slots=True)
class NoahConfig:
    home: Path = Path.home()
    dots_dir: Path = field(default_factory=lambda: Path.home() / "Lit" / "polka")
    secdots_dir: Path = field(
        default_factory=lambda: Path.home() / "Lit" / "Docs" / "secdots"
    )
    dirs_to_link: list[str] = field(default_factory=lambda: ["local/bin"])

    terminal: str = "kitty"
    firefox_browser: str = "floorp"
    dots_repo: str = ""
    git_user: str = ""
    encrypted_dir: str = "Desktop/Encrypted"

    ssh_key_file: str = "id_ed25519"
    gpg_key_file: str = "my_sec_gpg.asc"
    master_pass_file: str = "pass.txt"
    my_pass: str = "users.json"

    wireguard_dir: str = "wireguard"
    parallel_downloads: int = 10

    groups: list[str] = field(default_factory=list)
    dirs_icons: dict[str, str] = field(default_factory=dict)
    mkinit_hooks: list[str] = field(default_factory=list)
    reflector_options: list[str] = field(default_factory=list)
    custom_services: list[str] = field(default_factory=list)
    disable_svcs: list[str] = field(default_factory=list)
    apps_to_hide: list[str] = field(default_factory=list)
    no_extracts: list[str] = field(default_factory=list)
    yazi_plugins: list[str] = field(default_factory=list)
    git_users: list[str] = field(default_factory=list)

    git_repos: list[GitRepos] = field(default_factory=list)
    to_cp: list[CopyGroup] = field(default_factory=list)
    user_services: UserServices = field(default_factory=UserServices)

    @classmethod
    def from_config(cls, data):
        data = data or {}
        return cls(
            terminal=data.get("terminal", "kitty"),
            firefox_browser=data.get("firefox_browser", "floorp"),
            dots_repo=data.get("dots_repo", ""),
            git_user=data.get("git_user", ""),
            encrypted_dir=data.get("encrypted_dir", "Desktop/Encrypted"),
            ssh_key_file=data.get("ssh_key_file", "id_ed25519"),
            gpg_key_file=data.get("gpg_key_file", "my_sec_gpg.asc"),
            master_pass_file=data.get("master_pass_file", "pass.txt"),
            my_pass=data.get("my_pass", "users.json"),
            wireguard_dir=data.get("wireguard_dir", "wireguard"),
            parallel_downloads=data.get("parallel_downloads", 10),
            groups=data.get("groups", []),
            mkinit_hooks=data.get("mkinit_hooks", []),
            reflector_options=data.get("reflector_options", []),
            custom_services=data.get("custom_services", []),
            disable_svcs=data.get("disable_svcs", []),
            apps_to_hide=data.get("apps_to_hide", []),
            no_extracts=data.get("no_extracts", []),
            yazi_plugins=data.get("yazi_plugins", []),
            git_users=data.get("git_users", []),
            dirs_to_link=data.get("dirs_to_link", ["local/bin"]),
            git_repos=parse_list(GitRepos, data.get("git_repos")),
            to_cp=parse_list(CopyGroup, data.get("to_cp")),
            dirs_icons=data.get("dirs_icons", {}),
            user_services=UserServices.parse_arg(data.get("user_services")),
        )


@dataclass(slots=True)
class NoahUserProcessor:
    data: NoahConfig
    username: str | None = None
    HOME: Path = field(init=False)

    def __post_init__(self):
        self.HOME = (
            Path("/root") if self.username is None else Path("/home") / self.username
        )
        self.ENCRYPTED = self.HOME / self.data.encrypted_dir
        self.GIT_DIR = self.HOME / "Lit"
        self.DOTS = self.GIT_DIR / self.data.dots_repo
        self.ssh_path = self.HOME / ".ssh" / self.data.ssh_key_file
        self.gpg_path = self.HOME / ".gnupg" / self.data.gpg_key_file
        self.masterpass_path = self.HOME / ".ssh" / self.data.master_pass_file
        self.sec_dir = self.GIT_DIR / "Docs" / "base"
        self.dirs_to_link = [self.HOME / path for _, path in self.data.dirs_to_link]
        self.dirs_icons = {
            self.HOME / path: icon for path, icon in self.data.dirs_icons.items()
        }


def run_dmc(
    cmd: list[str],
    check: bool = False,
    input_text: str = "",
    shell: bool = False,
    cwd=None,
    interactive=False,
):
    if interactive:
        return subprocess.Popen(cmd).wait()
    log = get_logger("Run CMD")
    try:
        log.info(" ".join(cmd))
        result = subprocess.run(
            cmd,
            text=True,
            check=check,
            capture_output=True,
            input=input_text,
            shell=shell,
            cwd=cwd,
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


def yes_no(prompt: str, default: bool = True) -> bool:
    while True:
        r = (
            input(f"\033[92m{prompt} {'(Y/n)' if default else '(y/N)'}: \033[0m")
            .strip()
            .lower()
        )
        if r == "":
            return default
        if r in ("y"):
            return True
        if r in ("n"):
            return False


def ping(host: str = "google.com") -> bool:
    cmd = ["ping", "-c", "1", host]
    return (
        subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
        == 0
    )


#########################
# UTILS
#########################
def load_users_json(nc: NoahConfig) -> dict:
    json_file = (
        Path("/root")
        / nc.to_cp[0].to_cp_list[0].target_dir
        / nc.to_cp[0].to_cp_list[0].files[0]
    )
    if not (json_file).exists():
        return {"users": []}
    try:
        with json_file.open() as f:
            data = json.load(f)
            users = data.get("users", [])
            if not users:
                log.warning(f"No users found in {json_file}")
            return {"users": users}
    except Exception as e:
        log.error(f"Failed to read JSON: {e}")
        return {"users": []}


def copy_file(src: Path, dest: Path) -> None:
    if not src.is_file():
        log.error(f"{src} does not exist")
        return
    dest = dest / src.name if dest.is_dir() else dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    log.info(f"Copied file: {src} -> {dest}")


def copy_dir(src: Path, dest: Path) -> None:
    if not src.is_dir():
        log.error(f"{src} does not exist")
        return
    shutil.copytree(src, dest, dirs_exist_ok=True, ignore_dangling_symlinks=True)
    log.info(f"Copied directory: {src} -> {dest}")


###################################
# USB Files
###################################
def get_device(min_gb: int = 20, usb_fs_type: str = "ext4") -> str:
    def recurse(devices):
        for dev in devices:
            if (
                dev["type"] == "part"
                and dev.get("fstype") == usb_fs_type
                and dev.get("mountpoint") is None
                and float(dev["size"][:-1]) > min_gb
            ):
                candidates.append(
                    (
                        dev["name"],
                        dev["size"],
                        dev.get("fstype"),
                    )
                )
            if "children" in dev:
                recurse(dev["children"])

    data = json.loads(
        subprocess.check_output(
            ["lsblk", "-J", "-o", "NAME,SIZE,FSTYPE,MOUNTPOINT,TYPE"]
        )
    )
    candidates = []
    recurse(data["blockdevices"])
    while True:
        print(
            f"\033[91m{'No.':<5}\033[0m "
            f"\033[93m{'Name':<10}\033[0m "
            f"\033[94m{'Size':<10}\033[0m "
            f"\033[96m{'FS Type':>10}\033[0m"
        )
        print("-" * 45)
        for i, (name, size, fstype) in enumerate(candidates, 1):
            print(
                f"\033[91m{i:<5}\033[0m "
                f"\033[93m{name:<10}\033[0m "
                f"\033[94m{size:<10}\033[0m "
                f"\033[96m{fstype:>10}\033[0m"
            )
        choice = input(f"\033[92mEnter 1-{len(candidates)}: \033[0m").strip()
        if not choice.isdigit() or not (1 <= int(choice) <= len(candidates)):
            log.error("Enter valid number.")
            continue
        selected_path = f"/dev/{candidates[int(choice) - 1][0]}"
        break
    return selected_path


def collect_missing_paths(
    groups: list[CopyGroup], wireguard_dir: str = ""
) -> list[tuple[Path, Path]]:
    missing_paths: list[tuple[Path, Path]] = []
    root_home = Path("/root")
    for group in groups:
        source_d = group.source
        for copy_item in group.to_cp_list:
            target_dir = root_home / copy_item.target_dir
            for file_name in copy_item.files:
                dest_file = target_dir / file_name
                if not dest_file.exists():
                    missing_paths.append((Path(source_d) / file_name, dest_file))

    if wireguard_dir:
        dest_dir = root_home / wireguard_dir
        if not dest_dir.is_dir():
            missing_paths.append((Path(source_d) / wireguard_dir, dest_dir))

    return missing_paths


def mnt_cp_keys(
    groups: list[CopyGroup], wireguard_dir: str = "", usb_mnt: Path = Path("/mnt/usb")
) -> None:
    if usb_mnt.is_mount() and yes_no("USB mounted, unmount?"):
        run_dmc(["umount", str(usb_mnt)])
        run_dmc(["udevadm", "settle"])
        time.sleep(1)
    missing_paths = collect_missing_paths(groups, wireguard_dir)
    if not missing_paths:
        log.info("All required files present.")
        return
    if not yes_no(
        f"Mount USB to copy {', '.join(str(dest_path) for _, dest_path in missing_paths)}"
    ):
        return
    selected = get_device()
    run_dmc(["udevadm", "settle"])
    usb_mnt.mkdir(parents=True, exist_ok=True)
    run_dmc(["mount", "-o", "ro", str(selected), str(usb_mnt)], check=True)
    time.sleep(2)
    for src_path, dest_path in missing_paths:
        src = usb_mnt / src_path
        if src.is_file():
            copy_file(src, dest_path)
        elif src.is_dir():
            copy_dir(src, dest_path)
        else:
            log.error(f"{src} does not exist on USB")
    time.sleep(1)
    if yes_no("Files copied, unmount?"):
        run_dmc(["umount", str(usb_mnt)])
        run_dmc(["udevadm", "settle"])
        time.sleep(1)


###################################
# ETC/BOOT
###################################
def generate_pacman_conf(
    mnt_point: Path | None,
    no_extracts: list,
    parallel_downloads: int = 10,
    multilib: bool = True,
) -> None:
    no_extract_lines = "\n        ".join(
        [f"NoExtract = {item}" for item in no_extracts]
    )
    pacman_content = dedent(f"""
        [options]
        HoldPkg = pacman glibc
        Architecture = auto
        Color
        ILoveCandy
        ParallelDownloads = {parallel_downloads}
        DownloadUser = alpm
        SigLevel    = Required DatabaseOptional
        LocalFileSigLevel = Optional
        {no_extract_lines}

        [core]
        Include = /etc/pacman.d/mirrorlist

        [extra]
        Include = /etc/pacman.d/mirrorlist

        {"[multilib]\n        Include = /etc/pacman.d/mirrorlist" if multilib else ""}
    """)
    pacman_p = "etc/pacman.conf"
    pac_p = Path("/") / pacman_p
    if mnt_point:
        pac_p = mnt_point / pacman_p
    pac_p.write_text(pacman_content)


def write_etc_file(mnt_point: Path, files_to_write: dict[str, str]) -> None:
    for filepath, content in files_to_write.items():
        full_path = mnt_point / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with full_path.open("w") as file:
            file.write(content)
            log.info(f"Content: {content}\nWritten to: {full_path}")


def chaotic_repo(installation: Installer) -> None:
    srv = "keyserver.ubuntu.com"
    web = "https://cdn-mirror.chaotic.cx/chaotic-aur/"
    cmds = [
        ["pacman-key", "--init"],
        ["pacman-key", "--recv-key", "3056513887B78AEB", "--keyserver", srv],
        ["pacman-key", "--lsign-key", "3056513887B78AEB"],
        ["pacman", "-U", "--noconfirm", f"{web}chaotic-keyring.pkg.tar.zst"],
        ["pacman", "-U", "--noconfirm", f"{web}chaotic-mirrorlist.pkg.tar.zst"],
    ]
    for cmd in cmds:
        run_dmc(cmd)
        installation.arch_chroot(" ".join(cmd))
    for path in [Path("/etc/pacman.conf"), installation.target / "etc/pacman.conf"]:
        with path.open("a") as f:
            f.write("\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n")
    run_dmc(["pacman", "-Sy"], check=True)
    installation.arch_chroot("pacman -Sy")


def mpd_tmpfiles(installation: Installer, users: list[User]) -> None:
    for user in users:
        cache = f"home/{user.username}/.cache/"
        dir_path = installation.target / cache / "mpd/playlists"
        dir_path.mkdir(parents=True, exist_ok=True)
        dir_path.chmod(0o755)
        installation.arch_chroot(f"chown -R {user.username}:{user.username} /{cache}")


def configure_sudo(mnt_point: Path, user_name: str, pless=False) -> None:
    sudoers_content = dedent(
        f"""\
        {user_name} ALL=(ALL:ALL) {"NOPASSWD:ALL" if pless else "ALL"}
        Defaults    insults
        Defaults    passwd_tries=10
        Defaults    lecture=never
        Defaults    passwd_timeout=0
        Defaults    timestamp_timeout=20
        Defaults    timestamp_type=global
        Defaults    editor=/usr/sbin/nvim, !env_editor
        """
    )
    (mnt_point / f"etc/sudoers.d/00_{user_name}").write_text(sudoers_content)
    log.info(f"{'Removed' if pless else 'Created'} pass requirement for {user_name}")


def sys_dots(mnt_point: Path, script_dir: Path) -> None:
    for dir_name in ["etc", "usr"]:
        source_dir = script_dir / dir_name
        target_dir = mnt_point / dir_name
        log.info("Processing %s -> %s", source_dir, target_dir)
        if not source_dir.exists():
            log.error("Source directory not found: %s", source_dir)
            continue
        shutil.copytree(
            source_dir, target_dir, dirs_exist_ok=True, copy_function=shutil.copy2
        )
        log.info("Copied %s to %s", source_dir, target_dir)


def sysd_plymouth_setup(mnt_point: Path, boot_opts=["quiet", "splash"]) -> None:
    entries_dir = mnt_point / "boot" / "loader" / "entries"
    for entry in entries_dir.iterdir():
        lines = entry.read_text().splitlines()
        new_lines = []
        for line in lines:
            if line.startswith("options "):
                existing_opts = line[len("options ") :].split()
                for opt in boot_opts:
                    if opt not in existing_opts:
                        existing_opts.append(opt)
                line = "options " + " ".join(existing_opts)
            new_lines.append(line)
        entry.write_text("\n".join(new_lines) + "\n")


def modify_fstab(mnt_point: Path) -> None:
    fstab_path = mnt_point / "etc" / "fstab"
    content = fstab_path.read_text()
    content = re.sub(r"^(?!#).*?\bfmask=\d+", "fmask=0077", content, flags=re.MULTILINE)
    content = re.sub(r"^(?!#).*?\bdmask=\d+", "dmask=0077", content, flags=re.MULTILINE)
    fstab_path.write_text(content)


def modify_mkinit(mnt_point: Path, hooks: list[str], plymouth: bool) -> None:
    if plymouth and "plymouth" not in hooks:
        hooks.insert(hooks.index("kms") + 1, "plymouth")
    with open(f"/{mnt_point}/etc/mkinitcpio.conf", "r+") as mkinit:
        content = mkinit.read()
        content = re.sub(r"\nHOOKS=.*", f"\nHOOKS=({' '.join(hooks)})", content)
        mkinit.seek(0)
        mkinit.truncate()
        mkinit.write(content)


def get_gfx_drivers(graphics_devices: dict[str, str]) -> list[GfxDriver]:
    driver_map = {
        "nvidia": GfxDriver.NvidiaOpenKernel,
        "geforce": GfxDriver.NvidiaOpenKernel,
        "amd": GfxDriver.AmdOpenSource,
        "ati": GfxDriver.AmdOpenSource,
        "intel": GfxDriver.IntelOpenSource,
    }
    return [
        driver_map.get(device.lower().split()[0], GfxDriver.VMOpenSource)
        for device in graphics_devices
    ]


###################################
# USR_SVC
###################################
def enable_user_serv(installation, units: list[UsrSrv], username: str) -> None:
    user_base = f"home/{username}/.config/systemd/user"
    for unit in units:
        target_dir = f"/{user_base}/{unit.target}.target.wants"
        mnt_target_dir = installation.target / target_dir
        mnt_target_dir.mkdir(parents=True, exist_ok=True)
        source_dir = unit.source
        if unit.source == "/.config/systemd/user":
            source_dir = f"/home/{username}{unit.source}"
            chown_cmds = True
        for service in unit.services:
            source_path = Path(source_dir) / service
            link_path = mnt_target_dir / service
            if not link_path.exists():
                link_path.symlink_to(source_path)
            if chown_cmds:
                installation.arch_chroot(
                    f"chown {username}:{username} {target_dir}/{service}"
                )
        if chown_cmds:
            installation.arch_chroot(f"chown {username}:{username} {target_dir}")


def user_service(
    installation: Installer,
    users: list[User],
    terminal: str,
    user_script="sys_setup.py",
    script_dir: str = Path(__file__).resolve().parent.name,
) -> None:
    if terminal.strip().lower() == "alacritty":
        terminal = "alacritty -e"
    for user in users:
        dir_path = f"home/{user.username}/.config/systemd/user"
        run_script = f"/home/{user.username}/{script_dir}/{user_script}"
        name = f"{user_script.rsplit('.', 1)[0]}.service"
        content = dedent(
            f"""\
            [Unit]
            Description=Open {terminal} {run_script} on login
            After=graphical-session.target

            [Service]
            Type=oneshot
            ExecStart=/usr/bin/{terminal} python {run_script}
            Restart=no

            [Install]
            WantedBy=graphical-session.target
            """
        )
        (installation.target / dir_path / name).write_text(content)
        unit = UsrSrv(
            source=f"/{dir_path}", target="graphical-session", services=[name]
        )
    for user in users:
        enable_user_serv(installation, [unit], user.username)


def install_icons(installation: Installer):
    git = "https://github.com/vinceliuice/WhiteSur-icon-theme.git"
    installation.arch_chroot(f"git clone {git}")
    installation.arch_chroot("bash ./WhiteSur-icon-theme/install.sh")
    installation.arch_chroot("rm -rf ./WhiteSur-icon-theme")
    icon_path = installation.target / "usr/share/icons"
    white_sur_light = icon_path / "WhiteSur-light"
    if white_sur_light.exists():
        shutil.rmtree(white_sur_light)
        log.info(f"Removed {white_sur_light}")
    themes_to_modify = []
    for folder in icon_path.iterdir():
        if folder.is_dir() and ("-dark" in folder.name or "WhiteSur" in folder.name):
            themes_to_modify.append(folder)
    for theme_dir in themes_to_modify:
        for svg_file in theme_dir.rglob("*.svg"):
            if svg_file.is_file():
                text = svg_file.read_text()
                if "#ffffff" in text:
                    svg_file.write_text(text.replace("#ffffff", "#F4F5F6"))
                    log.info(f"Modified {svg_file}")


###################################
# User Space
###################################
def copy_keys(installation: Installer, username: str, groups: list[CopyGroup]) -> None:
    root_home = Path("/root")
    for group in groups:
        for copy_item in group.to_cp_list:
            sys_path = Path("home") / username / copy_item.target_dir
            target_dir = installation.target / sys_path
            target_dir.mkdir(parents=True, exist_ok=True)
            target_dir.chmod(0o700)
            installation.chown(username, str(sys_path))  # chown the directory
            for name in copy_item.files:
                src = root_home / group.source / name
                dest = target_dir / name
                copy_file(src, dest)
                dest.chmod(0o600)
                installation.chown(username, str(sys_path / name))


def set_extensions(mnt_point: Path, browser: str, new_policies: dict[str, Any]) -> None:
    file_path = mnt_point / "usr" / "lib" / browser / "distribution" / "policies.json"
    data = {}
    if file_path.exists():
        try:
            data = json.loads(file_path.read_text())
        except json.JSONDecodeError:
            log.warning(f"Corrupt JSON in {file_path}, resetting.")
    data.setdefault("policies", {}).update(new_policies)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data, indent=2))
    log.info(f"Policies for {browser} have been set (overwritten).")


def hide_apps(installation: Installer, user: str, apps_to_hide: list[str]):
    user_home = f"home/{user}"
    for app in apps_to_hide:
        file_p = f"{user_home}/.local/share/applications/{app}.desktop"
        (installation.target / file_p).write_text("[Desktop Entry]\nNoDisplay=true\n")
        installation.chown(user, f"/{file_p}")


def copy_skel(mountpoint: Path, nc: NoahConfig):
    tmp = mountpoint / "tmp" / nc.dots_repo
    tmp.mkdir(exist_ok=True)
    git = f"https://github.com/{nc.git_user}/{nc.dots_repo}.git"
    run_dmc(["git", "clone", git, str(tmp)])
    shutil.rmtree(tmp / ".git")
    for p in tmp.iterdir():
        p.rename(p.parent / ("." + p.name))
    copy_dir(tmp, mountpoint / "etc" / "skel")


###################################
# Archinstall
###################################
def show_menu(arch_config_handler: ArchConfigHandler) -> None:
    global_menu = GlobalMenu(arch_config_handler.config)
    global_menu.disable_all()
    global_menu.set_enabled("disk_config", True)
    global_menu.set_enabled("archinstall_language", True)
    global_menu.set_enabled("locale_config", True)
    global_menu.set_enabled("timezone", True)
    global_menu.set_enabled("bootloader_config", True)
    global_menu.set_enabled("ntp", True)
    global_menu.set_enabled("kernels", True)
    global_menu.set_enabled("hostname", True)
    global_menu.set_enabled("auth_config", True)
    global_menu.set_enabled("app_config", True)
    global_menu.set_enabled("packages", True)
    global_menu.set_enabled("__config__", True)
    result: ArchConfig | None = tui.run(global_menu)
    if result is None:
        sys.exit(0)


def perform_installation(
    arch_config_handler: ArchConfigHandler,
    auth_handler: AuthenticationHandler,
    application_handler: ApplicationHandler,
    nc: NoahConfig,
    gfx_drivers: list[GfxDriver],
) -> None:
    script_d = Path(__file__).resolve().parent
    start_time = time.monotonic()
    info("Starting installation...")
    mountpoint = arch_config_handler.args.mountpoint
    config = arch_config_handler.config
    if not config.disk_config:
        error("No disk configuration provided")
        return
    disk_config = config.disk_config
    run_mkinitcpio = not config.bootloader_config or not config.bootloader_config.uki
    locale = config.locale_config
    with Installer(
        mountpoint,
        disk_config,
        base_packages=[],
        kernels=config.kernels,
        silent=arch_config_handler.args.silent,
    ) as installation:
        if disk_config.config_type != DiskLayoutType.Pre_mount:
            installation.mount_ordered_layout()
        installation.sanity_check(
            arch_config_handler.args.offline,
            arch_config_handler.args.skip_ntp,
            arch_config_handler.args.skip_wkd,
        )
        if disk_config.config_type != DiskLayoutType.Pre_mount:
            if (
                disk_config.disk_encryption
                and disk_config.disk_encryption.encryption_type
                != EncryptionType.NO_ENCRYPTION
            ):
                installation.generate_key_files()

        run_dmc(
            [
                "reflector",
                *(part for opt in nc.reflector_options for part in opt.split()),
            ]
        )
        generate_pacman_conf(None, no_extracts=list(nc.no_extracts))
        installation.minimal_installation(
            optional_repositories=[],
            mkinitcpio=run_mkinitcpio,
            hostname=config.hostname,
            locale_config=locale,
            pacman_config=None,
        )
        copy_file(
            Path("/etc/pacman.d/mirrorlist"), mountpoint / "etc/pacman.d/mirrorlist"
        )
        generate_pacman_conf(mountpoint, list(nc.no_extracts))
        installation.add_additional_packages("realtime-privileges")
        copy_skel(mountpoint, nc)
        chaotic_repo(installation)

        if config.swap and config.swap.enabled:
            installation.setup_swap(algo=config.swap.algorithm)
        if (
            config.bootloader_config
            and config.bootloader_config.bootloader != Bootloader.NO_BOOTLOADER
        ):
            installation.add_bootloader(
                config.bootloader_config.bootloader,
                config.bootloader_config.uki,
                config.bootloader_config.removable,
            )

        if config.network_config:
            install_network_config(
                config.network_config, installation, config.profile_config
            )

        users = None
        if config.auth_config:
            if config.auth_config.users:
                users = config.auth_config.users
                installation.create_users(config.auth_config.users)
                auth_handler.setup_auth(
                    installation, config.auth_config, config.hostname
                )

        if app_config := config.app_config:
            application_handler.install_applications(installation, app_config)

        if config.packages and config.packages[0] != "":
            installation.add_additional_packages(config.packages)

        if timezone := config.timezone:
            installation.set_timezone(timezone)

        if config.ntp:
            installation.activate_time_synchronization()

        if config.auth_config and config.auth_config.root_enc_password:
            root_user = User("root", config.auth_config.root_enc_password, False)
            installation.set_user_password(root_user)

        for gfx_driver in gfx_drivers:
            profile_handler.install_gfx_driver(installation, gfx_driver)
        profile_handler.install_greeter(installation, GreeterType.Ly)
        write_etc_file(mountpoint, ec.etc_files_to_write)
        reflector_timer_conf = mountpoint / "etc/xdg/reflector/reflector.conf"
        reflector_timer_conf.write_text("\n".join(nc.reflector_options))
        copy_dir(Path("/root") / nc.wireguard_dir, mountpoint / "etc" / "wireguard")
        set_extensions(mountpoint, nc.firefox_browser, ec.new_policies)
        sys_dots(mountpoint, script_d)
        install_icons(installation)
        modify_mkinit(mountpoint, list(nc.mkinit_hooks), plymouth=True)
        if config.auth_config:
            if users:
                for user in users:
                    installation.arch_chroot("xdg-user-dirs-update", user.username)
                    enable_user_serv(
                        installation, nc.user_services.root_owned, user.username
                    )
                    enable_user_serv(
                        installation, nc.user_services.user_owned, user.username
                    )
                    hide_apps(installation, user.username, nc.apps_to_hide)
                user_1 = users[0].username
                mpd_tmpfiles(installation, users)
                configure_sudo(mountpoint, user_1, pless=True)
                cmd = f"paru -S --noconfirm --needed {' '.join(ec.aur_pkgs)}"
                installation.arch_chroot(cmd, user_1)
                configure_sudo(mountpoint, user_1)
                copy_dir(script_d, (mountpoint / f"home/{user_1}" / script_d.name))
                cmd = f"paru -S --noconfirm --needed {' '.join(ec.aur_pkgs)}"
                installation.arch_chroot(cmd, user_1)
                copy_keys(installation, user_1, nc.to_cp)
                user_service(installation, users, nc.terminal)
        if config.bootloader_config:
            if config.bootloader_config.bootloader == Bootloader.Systemd:
                if config.bootloader_config.uki:
                    print("Nope")
                else:
                    sysd_plymouth_setup(mountpoint)

        if services := config.services:
            installation.enable_service(services)

        installation.disable_service(list(nc.disable_svcs))

        if disk_config.has_default_btrfs_vols():
            btrfs_options = disk_config.btrfs_options
            snapshot_config = btrfs_options.snapshot_config if btrfs_options else None
            snapshot_type = snapshot_config.snapshot_type if snapshot_config else None
            if snapshot_type:
                bootloader = (
                    config.bootloader_config.bootloader
                    if config.bootloader_config
                    else None
                )
                installation.setup_btrfs_snapshot(snapshot_type, bootloader)

        if cc := config.custom_commands:
            run_custom_user_commands(cc, installation)

        installation.genfstab()
        modify_fstab(mountpoint)

        debug(f"Disk states after installing:\n{disk_layouts()}")
        if not arch_config_handler.args.silent:
            elapsed_time = time.monotonic() - start_time
            action: PostInstallationAction = tui.run(
                lambda: select_post_installation(elapsed_time)
            )
            match action:
                case PostInstallationAction.EXIT:
                    pass
                case PostInstallationAction.REBOOT:
                    _ = subprocess.run(["sudo", "reboot"], check=True)
                case PostInstallationAction.CHROOT:
                    try:
                        installation.drop_to_shell()
                    except Exception:
                        pass


def sys_setup() -> None:
    nc = NoahConfig.from_config(ec.json_config)
    mnt_cp_keys(nc.to_cp, nc.wireguard_dir)
    arch_config_handler = ArchConfigHandler()
    users_json = load_users_json(nc)
    if user_list := users_json.get("users", []):
        arch_config_handler.config.auth_config = AuthenticationConfiguration(
            None,
            [
                User(
                    username=user_list[0]["username"],
                    password=Password(enc_password=user_list[0]["enc_password"]),
                    sudo=True,
                    groups=list(nc.groups),
                )
            ],
            None,
        )
    arch_config_handler.config.hostname = ec.arch_config.hostname
    arch_config_handler.config.ntp = ec.arch_config.ntp
    arch_config_handler.config.swap = ec.arch_config.swap
    arch_config_handler.config.profile_config = ec.arch_config.profile_config
    arch_config_handler.config.timezone = ec.arch_config.timezone
    arch_config_handler.config.bootloader_config = ec.arch_config.bootloader_config
    arch_config_handler.config.ntp = True
    arch_config_handler.config.kernels = ec.arch_config.kernels
    arch_config_handler.config.services = ec.arch_config.services + list(
        nc.custom_services
    )
    arch_config_handler.config.app_config = ec.arch_config.app_config
    gfx_drivers = get_gfx_drivers(_sys_info.graphics_devices)
    base_pkgs = ec.pkgs["base"] + ec.pkgs["language"] + ec.pkgs["chaotic_repo"]
    if GfxDriver.VMOpenSource not in gfx_drivers:
        base_pkgs.extend(ec.pkgs["extra"] + ec.pkgs["extra_chaos"])
    arch_config_handler.config.packages = base_pkgs
    show_menu(arch_config_handler)
    config = ConfigurationOutput(arch_config_handler.config)
    config.write_debug()
    config.save()
    if not arch_config_handler.args.silent:
        aborted = False
        res: bool = tui.run(config.confirm_config)
        if not res:
            debug("Installation aborted")
            aborted = True
        if aborted:
            return sys_setup()
    if arch_config_handler.config.disk_config:
        fs_handler = FilesystemHandler(arch_config_handler.config.disk_config)
        if not delayed_warning("Starting device modifications in "):
            return sys_setup()
        fs_handler.perform_filesystem_operations()
    perform_installation(
        arch_config_handler,
        AuthenticationHandler(),
        ApplicationHandler(),
        nc,
        gfx_drivers,
    )


############################
# USER SETUP
############################
def iwctl_scan() -> bool:
    result = run_dmc(["sudo", "iwctl", "station", "wlan0", "scan"], check=False)
    time.sleep(10)
    if result.returncode == 0:
        return True
    return False


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
    candidates.extend(collect_candidates(nc.dots_dir, nu.HOME, nc.dirs_to_link))
    candidates.extend(collect_candidates(nc.secdots_dir, nu.HOME, nc.dirs_to_link))
    for d in nc.dirs_to_link:
        src = nu.HOME / nc.dots_dir / d
        if src.is_dir():
            candidates.append((src, dotted_destination(src, nc.dots_dir, nu.HOME)))
    return candidates


##########################################
# MAIN
##########################################
def deploy_dotfiles(nc: NoahConfig, nu: NoahUserProcessor):
    if not (nu.HOME / nc.dots_dir).is_dir():
        log.error(f"Dotfiles directory not found: {nu.HOME / nc.dots_dir}")
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
    pwd = getpass("Enter GPG Password:")
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


def clone_repos(
    git_repos: list[GitRepos],
    dest: Path,
    ssh: bool,
) -> None:
    def url(user: str, repo: str) -> str:
        if ssh:
            return f"git@github.com:{user}/{repo}.git"
        return f"https://github.com/{user}/{repo}.git"

    dest.mkdir(parents=True, exist_ok=True)

    for git_user in git_repos:
        for remote_repo, local_dir in git_user.repos.items():
            repo_path = dest / Path(local_dir).name
            if repo_path.exists():
                log.info(f"{repo_path} exists, skipping.")
                continue

            result = subprocess.run(
                ["git", "clone", url(git_user.user, remote_repo), str(repo_path)],
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
    nc = NoahConfig()
    nu = NoahUserProcessor(nc)
    if shutil.which("mariadb"):
        user = pwd.getpwuid(os.getuid()).pw_name
        enable_mariadb(user)
    if nu.ssh_path.exists():
        import_ssh(nu.ssh_path)
        configure_git()
        ensure_github_known_hosts(nu.HOME)
        clone_repos(nc.git_repos, nu.HOME, ssh=False)
    else:
        clone_repos(nc.git_repos, nu.HOME, ssh=False)
    if nu.gpg_path and not nu.gpg_path.exists():
        import_gpg(nu.gpg_path)
    if nu.ENCRYPTED and not (nu.ENCRYPTED / "gocryptfs.conf").exists():
        if shutil.which("gocryptfs"):
            init_gocrypt(nu.ENCRYPTED)
    if nu.dirs_icons:
        set_folder_icons(nu.dirs_icons)
    for plugin in nc.yazi_plugins:
        run_dmc(["ya", "pkg", "add", plugin])
    if any((nu.DOTS).iterdir()):
        deploy_dotfiles(nc, nu)
        run_dmc(
            ["uv", "add", "openmeteo-requests"],
            cwd=f"{nu.HOME}/.local/bin/weather",
        )
    if shutil.which("scrcpy"):
        scrcpy_setup()
    if nu.masterpass_path.is_file():
        pass_and_input(nu.masterpass_path)
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
    if os.geteuid() == 0:
        from archinstall.default_profiles.profile import GreeterType
        from archinstall.lib.authentication.authentication_handler import (
            AuthenticationHandler,
        )
        from archinstall.lib.applications.application_handler import ApplicationHandler
        from archinstall.lib.hardware import _sys_info, GfxDriver
        from archinstall.lib.args import (
            ArchConfig,
            ArchConfigHandler,
            AuthenticationConfiguration,
        )
        from archinstall.lib.configuration import ConfigurationOutput
        from archinstall.lib.disk.filesystem import FilesystemHandler
        from archinstall.lib.disk.utils import disk_layouts
        from archinstall.lib.general.general_menu import (
            PostInstallationAction,
            select_post_installation,
        )
        from archinstall.lib.global_menu import GlobalMenu
        from archinstall.lib.installer import Installer, run_custom_user_commands
        from archinstall.lib.menu.util import delayed_warning
        from archinstall.lib.models import Bootloader
        from archinstall.lib.models.device import DiskLayoutType, EncryptionType
        from archinstall.lib.models.users import User
        from archinstall.lib.output import debug, error, info
        from archinstall.tui.ui.components import tui
        from archinstall.lib.models.users import Password
        from archinstall.lib.network.network_handler import install_network_config
        from archinstall.lib.profile.profiles_handler import profile_handler

        sys_setup()
    else:
        user_setup()
        import gnupg
        import pyperclip
