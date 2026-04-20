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
from archinstall.lib.installer import Installer, SysCommand
from archinstall.lib.menu.util import delayed_warning
from archinstall.lib.models import Bootloader
from archinstall.lib.models.device import DiskLayoutType, EncryptionType
from archinstall.lib.models.users import User
from archinstall.lib.output import debug, error, info
from archinstall.tui.ui.components import tui
from archinstall.lib.models.locale import LocaleConfiguration
from archinstall.lib.models.users import Password
from pydantic import BaseModel
from pathlib import Path
import sys
import time
import subprocess
import json
import re
import shlex
import shutil
import textwrap
from utils import get_logger, run_cmd, ask_pass


###########################################################
# ARCHINSTALL CONF
###########################################################
user_name = "nick"
hostname = "yulia"
kernel = ["linux"]
timezone = "US/Eastern"
groups = ["adm", "games", "realtime", "storage", "video"]
git_name = "acctux"
dots_git = "polka"
script_pwd_to_cp = ["etc", "usr"]
###########################################################
# USB PASSED FILES CONF
###########################################################
usb_key_dir = "keys"
ssh_key = "id_ed25519"
gpg_key = "my_sec_gpg.asc"
pass_pass = "pass.txt"
my_pass = "pass.py"
wireguard_dir = "wireguard"
usb_cp_files = [ssh_key, gpg_key, pass_pass, my_pass]
###########################################################
# REFLECTOR OPTIONS
###########################################################
refl_options = [
    "--country US",
    "--protocol https",
    "--latest 15",
    "--sort rate",
    "--number 3",
]
###########################################################
# MKINITCPIO HOOKS
###########################################################
mkinit_hooks = [
    "base",
    "systemd",
    "autodetect",
    "microcode",
    "modconf",
    "kms",
    "sd-vconsole",
    "block",
    "filesystems",
    "fsck",
]
###########################################################
# PACMAN CONF
###########################################################
noextract_lines = [
    "NoExtract = etc/xdg/autostart/firewall-applet.desktop",
    "NoExtract = usr/share/icons/capitaine-cursors/*",
]
###########################################################
# PKGS
###########################################################
amd_pkgs = [
    "mesa",
    "xf86-video-amdgpu",
    "xf86-video-ati",
    "vulkan-radeon",
]
nvidia_pkgs = [
    "lib32-nvidia-utils",
    "libva-nvidia-driver",
    "libva-utils",
    "libxnvctrl",
    "nvidia-open",
    "nvidia-prime",
    "opencl-nvidia",
]
pipewire_pkgs = [
    "pipewire",
    "pipewire-alsa",
    "pipewire-jack",
    "pipewire-pulse",
    "gst-plugin-pipewire",
    "libpulse",
    "wireplumber",
]
hardware_pkgs = [
    "ananicy-cpp",
    "bluetui",
    "bluez-tools",
    "bluez-utils",  # for loggy
    "brightnessctl",
    "cpupower",
    "dosfstools",
    "exfatprogs",
    "kanshi",
    "ntfs-3g",
    "realtime-privileges",
    "smartmontools",
    "tuned",
    "udisks2-btrfs",
    "usb_modeswitch",
]
monitor_pkgs = [
    "btop",
    "rocm-smi-lib",  # btop dependency for amd gpu
    "nvtop",
    "powertop",
    "gnome-logs",
    "systemctl-tui",
]
base_pkgs = [
    "base-devel",
    "logrotate",
    "ly",
    "pkgfile",
    "plymouth",
    "rebuild-detector",
    "xdg-user-dirs",
]
cli_pkgs = [
    "bat-extras",
    "eza",
    "fd",
    "fzf",
    "git-delta",
    "github-cli",
    "kitty",
    "lazygit",
    "less",
    "man-pages",
    "mcfly",
    "ripgrep-all",
    "sd",
    "starship",
    "trash-cli",
    "ugrep",
    "zoxide",
    "zsh-autocomplete",
    "zsh-completions",
    "zsh-syntax-highlighting",
]
basic_pkgs = [
    "anki",
    "authenticator",
    "baobab",
    "bustle",
    "cliphist",
    "featherpad",
    "file-roller",
    "gocryptfs",
    "khal",
    "partitionmanager",
    "qalculate-qt",
    "qt5ct",
    "qt6ct",
    "taskwarrior-tui",
    "unrar",  # File roller
    "wl-clipboard",
    "wl-clip-persist",
    "yazi",
    "zbar",  # qr codes
]
android_pkgs = [
    "kdeconnect",
    "gvfs-mtp",
    "sshfs",
    "scrcpy",
]
apple_pkgs = [
    "gvfs-afc",
    "gvfs-gphoto2",
    "usbmuxd",
]
network_pkgs = [
    "bind",
    "deluge-gtk",
    "firewalld",
    "impala",
    "iw",
    "iwd",
    "openresolv",
    "profile-sync-daemon",
    "protonmail-bridge-core",
    "wireguard-tools",
]
lang_pkgs = [
    "hunspell-en_us",
    "hyphen-en",
    "noto-fonts-emoji",
    "otf-firamono-nerd",
    "rofimoji",
    "tesseract-data-eng",
    "ttf-liberation",
]
media_pkgs = [
    "cava",
    "evince",
    "gimp",
    "guvcview",
    "imv",
    "mpd",
    "mpd-mpris",
    "mpv-mpris",
    "pavucontrol",
    "playerctl",
    "rmpc",
    "yt-dlp",
]
hyprland_pkgs = [
    "capitaine-cursors",
    "fuzzel",
    "gnome-keyring",
    "gsimplecal",
    "hypridle",
    "hyprland",
    "hyprlock",
    "hyprshot",
    "hyprsunset",
    "kvantum",
    "kvantum-qt5",
    "polkit-gnome",
    "qt5-wayland",
    "qt6-wayland",
    "satty",
    "seahorse",
    "snixembed",
    "swaync",
    "swayosd",
    "awww",
    "uwsm",
    "waybar",
    "xdg-desktop-portal-gnome",
    "xdg-desktop-portal-hyprland",
]
office_pkgs = [
    "gnucash",
    "libreoffice-fresh",
    "coin-or-mp",  # LibreOffice Calc Solver
    "zathura-pdf-mupdf",
]
coding_pkgs = [
    "inotify-tools",  # nvim
    "npm",
    "neovim-lspconfig",
    "rust",
    "uv",
    # Language Servers
    "bash-language-server",
    "lua-language-server",
    "rust-analyzer",
    "tailwindcss-language-server",
    "tombi",
    "ty",
    "vscode-json-languageserver",
    "yaml-language-server",
    # Formatters
    "prettier",
    "ruff",
    "shfmt",
    "stylua",
    # Tree sitter
    "tree-sitter-bash",
    "tree-sitter-cli",
    "tree-sitter-python",
    "tree-sitter-rust",
]
mariadb_pkgs = [
    "dbeaver",
    "jdk-openjdk",
    "mariadb",
    "python-pymysql",
]
pydep_pkgs = [
    "python-dbus-fast",  # loggy
    "python-gnupg",  # noah
    "python-imaplib2",  # emailcheck
    "python-pandas",  # weather
    "python-pydantic",  # noah
    "python-pyperclip",  # noah
    "python-systemd",  # loggy
    "python-wand",  # wallpaper script
]
gaming_pkgs = [
    "gnome-chess",
    "gnuchess",
    "lib32-mangohud",
    "lutris",
    "mangohud",
    "mgba-qt",
    "steam",
    "umu-launcher",
    "vkd3d",
    "wine-mono",
    "wine-staging",
    "winetricks",
]
# --CHAOTIC PKGS--
chaotic_pkgs = [
    "ayugram-desktop-git",
    "qt6-imageformats",  # AyuGram missing dependency
    "betterbird-bin",
    "cachyos-ananicy-rules-git",
    "dxvk-mingw-git",
    "eden-git",
    "firedragon",
    "logiops",
    "nchat-git",
    "neovim-symlinks",
    "ocrmypdf",
    "octopi",
    "paru",
    "proton-cachyos",
    "rpcs3-git",
]
###########################################################
# AUR PKGS
###########################################################
aur_pkgs = ["wvkbd-deskintl"]
###########################################################
# SYS SERVICES
###########################################################
sys_services = [
    "ananicy-cpp",
    "bluetooth",
    "cpupower",
    "firewalld",
    "iwd",
    "ly@tty1",
    "named",
    "swayosd-libinput-backend",
    "systemd-networkd",
    "systemd-oomd",
    "systemd-timesyncd",
    "tuned",
    "btrfs-scrub@-.timer",
    "btrfs-scrub@home.timer",
    "fstrim.timer",
    "logrotate.timer",
    "man-db.timer",
    "paccache.timer",
    "reflector.timer",
]
custom_services = ["loggy", "wireguard-list"]
disable_svcs = ["getty@tty1", "systemd-networkd-wait-online"]
###########################################################
# HIDE APPS
###########################################################
apps_to_hide = [
    "avahi-discover",
    "bssh",
    "btop",
    "bvnc",
    "jshell-java-openjdk",
    "jconsole-java-openjdk",
    "khal",
    "kvantummanager",
    "nvtop",
    "octopi-cachecleaner",
    "octopi-notifier",
    "octopi-repoeditor",
    "org.gnome.baobab",
    "org.kde.kdeconnect.nonplasma",
    "qt5ct",
    "qt6ct",
    "qv4l2",
    "qvidcap",
    "scrcpy-console",
    "taskwarrior-tui",
    "tuned-gui",
    "uuctl",
    "xgps",
    "xgpsspeed",
]


###########################################################
# USER SERVICES
###########################################################
class UserSrv(BaseModel):
    source: str = "/usr/lib/systemd/user"
    services: list[str]
    target: str


class CustUserSrv(BaseModel):
    services: list[str]
    target: str


usr_srv_default = UserSrv(
    source="/usr/lib/systemd/user",
    target="default",
    services=["pipewire-pulse.service", "psd.service"],
)
usr_srv_sockets = UserSrv(
    source="/usr/lib/systemd/user",
    target="sockets",
    services=[
        "pipewire-pulse.socket",
        "gnome-keyring-daemon.socket",
        "gcr-ssh-agent.socket",
        "mpd.socket",
    ],
)
usr_srv_graphical = UserSrv(
    source="/usr/lib/systemd/user",
    target="graphical-session",
    services=[
        "cliphist.service",
        "hypridle.service",
        "hyprsunset.service",
        "swaync.service",
        "waybar.service",
    ],
)
cust_graphic = UserSrv(
    source=f"/home/{user_name}/.config/systemd/user",
    target="graphical-session",
    services=[
        "ayugram.service",
        "clip-persist.service",
        "kdeconnectd.service",
        "playerctld.service",
        "polkit-gnome.service",
        "snixembed.service",
        "swayosd.service",
        "awww-daemon.service",
    ],
)
cust_timer = UserSrv(
    source=f"/home/{user_name}/.config/systemd/user",
    target="timers",
    services=[
        "emailcheck.timer",
        "task-reminder.timer",
        "task-schedule.timer",
        "wall.timer",
    ],
)


###########################################################
# CONSTANTS
###########################################################
script_d = Path(__file__).resolve().parent
user_home = f"home/{user_name}"
HOME = Path.home()
mountpoint = Path("/mnt/arch")
log = get_logger("Noah")


#########################
# UTILS
#########################
def src_pass_file(usb_key_dir: str, pass_file: str):
    key_path = Path("/root") / usb_key_dir / pass_file
    if key_path.exists():
        try:
            pw = key_path.read_text().strip()
            log.info(f"{key_path} loaded ")
            return pw
        except Exception as e:
            log.error(f"{e}")
    log.warning(f"{key_path} not found or unreadable.")


def copy_file(file: Path, dest: Path) -> None:
    if not file.is_file():
        log.error(f"{file} does not exist")
        return
    if dest.is_dir():
        dest = dest / file.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file, dest)
    log.info(f"Copied file: {file} to {dest}")


def copy_dir(dir: Path, dest: Path) -> None:
    src = Path("/root") / dir
    if not src.is_dir():
        log.error(f"{src} does not exist")
        return
    shutil.copytree(src, dest, dirs_exist_ok=True, ignore_dangling_symlinks=True)
    log.info(f"Copied directory: {src} to {dest}")


def ind_key_permission(path: Path, f_mode=0o600, d_mode=0o700):
    if path.exists():
        if path.is_file():
            path.chmod(f_mode)
        path.chmod(d_mode)
    else:
        log.warning(f"{path} not found.")


def yes_no(prompt: str) -> bool:
    while True:
        response = input(f"{prompt} (y/n): ").strip().lower()
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'.")


###################################
# UTILS
###################################
def check_missing(
    key_dir: str | None = None,
    key_files: list[str] | None = None,
    wireguard_dir: str | None = None,
) -> list[str]:
    log = get_logger("Needed")
    missing_files = []
    if key_files:
        for key in key_files:
            key_path = HOME / f"{key_dir}/{key}"
            if not key_path.exists():
                missing_files.append(key)
    if wireguard_dir and not (HOME / wireguard_dir).is_dir():
        missing_files.append(wireguard_dir)
    if missing_files:
        log.warning(", ".join(missing_files))
    return missing_files


def get_device(min_gb=20, usb_fs_type="ext4") -> str:
    data = json.loads(
        subprocess.check_output(
            ["lsblk", "-J", "-o", "NAME,SIZE,FSTYPE,MOUNTPOINT,TYPE"], text=True
        )
    )
    candidates = []
    selected_path = ""

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

    recurse(data["blockdevices"])
    while True:
        get_logger("").info(f"{'No.':<5} {'Name':<8} {'Size':<8} {'FS Type':>8}")
        get_logger("").info("-" * 45)
        for i, (name, size, fstype) in enumerate(candidates, 1):
            get_logger("").info(f"{i:<5} {name:<8} {size:<8} {fstype:>8}")
        choice = input(f"Enter 1-{len(candidates)}: ").strip()
        if not choice.isdigit() or not (1 <= int(choice) <= len(candidates)):
            log.error("Out of range.")
            continue
        selected_path = f"/dev/{candidates[int(choice) - 1][0]}"
        break
    return selected_path


def usb_cp_keys(usb_mount: Path, key_dir: str, key_files: list[str]):
    (HOME / key_dir).mkdir(parents=True, exist_ok=True)
    for key in key_files:
        copy_file(usb_mount / key_dir / key, HOME / key_dir / key)


def umount_usb(usb_mount: Path):
    cmd = ["umount", str(usb_mount)]
    run_cmd(cmd, check=True, shell=True)
    log.info(f"Unmounted USB from {usb_mount}.")
    if usb_mount.exists():
        try:
            shutil.rmtree(usb_mount)
            usb_mount.unlink(missing_ok=True)
        except OSError:
            pass


def mnt_cp_keys(
    key_dir: str | None = None,
    key_files: list[str] | None = None,
    wireguard_dir: str | None = None,
    usb_mnt=Path("/mnt/usb"),
):
    if usb_mnt.is_mount():
        if yes_no("Found /mnt/usb, try unmount?"):
            umount_usb(usb_mnt)
    if key_dir and key_files or wireguard_dir:
        if check_missing(key_dir, key_files, wireguard_dir):
            if yes_no("Mount USB to copy missing files?"):
                selected_path = get_device()
                usb_mnt.mkdir(parents=True, exist_ok=True)
                cmd = [f"mount -t ext4 -o ro {selected_path} {usb_mnt}"]
                run_cmd(cmd, check=True, shell=True)
                time.sleep(1)
                if key_dir and key_files:
                    usb_cp_keys(usb_mnt, key_dir, key_files)
                if wireguard_dir:
                    if not (HOME / wireguard_dir).exists():
                        copy_dir(usb_mnt / wireguard_dir, HOME / wireguard_dir)
                if yes_no("Unmount USB?"):
                    umount_usb(usb_mnt)
    else:
        log.info("All required files present.")


###################################
# GNUPG
###################################
def run_chroot(
    commands: list[str], mnt_point: Path, user_name: str | None = None, peek=True
):
    script_path = "var/tmp/user-commands.sh"
    chroot_path = mnt_point / script_path
    chroot_path.parent.mkdir(parents=True, exist_ok=True)
    with open(chroot_path, "w") as script:
        script.write("#!/bin/bash\n")
        if peek:
            script.write("set -e\n")
        for cmd in commands:
            script.write(cmd + "\n")
    chroot_path.chmod(0o755)
    cmd = f"bash /{script_path}"
    if user_name:
        cmd = f"su - {user_name} -c {shlex.quote(cmd)}"
    SysCommand(f"arch-chroot -S {mnt_point} {cmd}")
    chroot_path.unlink()


###################################
# USR_SVC
###################################
def enable_user_serv(units: UserSrv | list[UserSrv], mnt_point: Path, user_name: str):
    if isinstance(units, UserSrv):
        units = [units]
    user_commands: list[str] = []
    base_dir = Path(f"/home/{user_name}/.config/systemd/user")
    for unit in units:
        for service in unit.services:
            target_dir = base_dir / f"{unit.target}.target.wants"
            user_commands.append(f"mkdir -p {target_dir}")
            src = Path(unit.source) / service
            dst = target_dir / service
            user_commands.append(f"ln -sf {src} {dst}")
    run_chroot([f"chown -R {user_name}:{user_name} /home/{user_name}/"], mnt_point)
    run_chroot(user_commands, mnt_point, user_name)


def user_service(
    mnt_point: Path,
    user_name: str,
    user_script="user_setup.py",
    script_dir: str = Path(__file__).resolve().parent.name,
):
    dir = f"home/{user_name}/.config/systemd/user"
    (mnt_point / dir).mkdir(parents=True, exist_ok=True)
    run_script = f"/home/{user_name}/{script_dir}/{user_script}"
    name = f"{user_script.rsplit('.', 1)[0]}.service"
    service_content = textwrap.dedent(f"""
    [Unit]
    Description=Open kitty {run_script} on login
    After=graphical-session.target

    [Service]
    Type=oneshot
    ExecStart=/usr/bin/kitty python {run_script}
    Restart=no

    [Install]
    WantedBy=graphical-session.target
    """)
    (mnt_point / dir / name).write_text(service_content)
    unit = UserSrv(source=f"/{dir}", target="graphical-session", services=[name])
    enable_user_serv(unit, mnt_point, user_name)


###################################
# PACMAN
###################################
def chaotic_repo(mnt_point: Path | None = None):
    log.info("Setting up Chaotic-AUR repository.")
    key_serv = "keyserver.ubuntu.com"
    chaotic_web = "https://cdn-mirror.chaotic.cx/chaotic-aur/"
    cmds_setup = [
        ["pacman-key", "--init"],
        ["pacman-key", "--recv-key", "3056513887B78AEB", "--keyserver", key_serv],
        ["pacman-key", "--lsign-key", "3056513887B78AEB"],
        ["pacman", "-U", "--noconfirm", f"{chaotic_web}chaotic-keyring.pkg.tar.zst"],
        ["pacman", "-U", "--noconfirm", f"{chaotic_web}chaotic-mirrorlist.pkg.tar.zst"],
    ]
    if mnt_point:
        for cmd in cmds_setup:
            run_chroot([" ".join(cmd)], mnt_point)
        pacman_conf = mnt_point / "etc/pacman.conf"
        run_chroot(["pacman -Sy"], mnt_point)
    else:
        for cmd in cmds_setup:
            run_cmd(cmd, check=True)
        pacman_conf = Path("/etc/pacman.conf")
        run_cmd(["pacman", "-Sy"], check=True)
    section = "[chaotic-aur]"
    content = pacman_conf.read_text()
    if section not in content:
        with pacman_conf.open("a") as f:
            f.write("\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n")


def config_pac_conf(mnt_point: Path | None, parallel_downloads=10, noextract_lines=[]):
    pacman_content = textwrap.dedent(f"""
        [options]
        HoldPkg = pacman glibc
        Architecture = auto
        Color
        ILoveCandy
        ParallelDownloads = {parallel_downloads}
        DownloadUser = alpm
        SigLevel    = Required DatabaseOptional
        LocalFileSigLevel = Optional
        {"\n".join(noextract_lines)}

        [core]
        Include = /etc/pacman.d/mirrorlist

        [extra]
        Include = /etc/pacman.d/mirrorlist

        [multilib]
        Include = /etc/pacman.d/mirrorlist
    """)
    if mnt_point:
        (mnt_point / "etc/pacman.conf").write_text(pacman_content.strip())
        run_chroot(["pacman -Sy"], mnt_point)
    else:
        Path("/etc/pacman.conf").write_text(pacman_content.strip())
        run_cmd(["pacman", "-Sy"], True)


###################################
# ETC/BOOT
###################################
def sys_dots(mnt_point: Path, script_dir: Path, sys_dir_cp: list[str]):
    for dir_name in sys_dir_cp:
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


def write_mpd_tmpfiles(mnt_point: Path, username: str) -> None:
    base_path = mnt_point / "etc" / "tmpfiles.d" / "mpd.conf"
    base_path.parent.mkdir(parents=True, exist_ok=True)
    base_path.write_text(
        f"d /home/{username}/.cache/mpd 0755 {username} mpd -\n"
        f"d /home/{username}/.cache/mpd/playlists 0755 {username} mpd -\n"
    )
    log.info(f"Wrote config to: {base_path}")


def configure_sudo(user_name: str, mnt_point: Path, passwordless_sudo=True):
    sudoers_file = mnt_point / f"etc/sudoers.d/00_{user_name}"
    if passwordless_sudo:
        sudoers_line = f"{user_name} ALL=(ALL:ALL) NOPASSWD:ALL"
        prt_val = "without password requirement"
    else:
        sudoers_line = f"{user_name} ALL=(ALL:ALL) ALL"
        prt_val = "with password requirement"
    sudoers_content = textwrap.dedent(f"""\
        {sudoers_line}
        Defaults    insults
        Defaults    passwd_tries=10
        Defaults    lecture=never
        Defaults    passwd_timeout=0
        Defaults    timestamp_timeout=20
        Defaults    timestamp_type=global
        Defaults    editor=/usr/sbin/nvim, !env_editor
    """)
    sudoers_file.write_text(sudoers_content.strip())
    sudoers_file.chmod(0o440)
    log.info(f"Created {sudoers_file} {prt_val} for {user_name}")


def modify_systemd(mnt_point: Path, boot_opts=["quiet", "splash"]) -> None:
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
    loader_file = mnt_point / "boot" / "loader" / "loader.conf"
    loader_file.write_text("default @saved\ntimeout 1\neditor no\n")
    loader_file.chmod(0o644)
    log.info(f"Modified {loader_file}")


def modify_fstab(mnt_point: Path) -> None:
    fstab_path = mnt_point / "etc" / "fstab"
    content = fstab_path.read_text()
    # ^(?!#) = ignore comments, .*? = match any characters up to the \option\
    # \bfmask=\d+  → word boundary, then  digits
    content = re.sub(r"^(?!#).*?\bfmask=\d+", "fmask=0077", content, flags=re.MULTILINE)
    content = re.sub(r"^(?!#).*?\bdmask=\d+", "dmask=0077", content, flags=re.MULTILINE)
    fstab_path.write_text(content)


def modify_mkinit(mnt_point: Path, hooks: list[str]):
    mkinitcpio_conf_path = f"{mnt_point}/etc/mkinitcpio.conf"
    with open(mkinitcpio_conf_path, "r+") as mkinit:
        content = mkinit.read()
        content = re.sub(r"\nHOOKS=.*", f"\nHOOKS=({' '.join(hooks)})", content)
        mkinit.seek(0)
        mkinit.truncate()
        mkinit.write(content)


def install_icon_theme(
    mnt_point: Path, old="#ffffff", new="#F4F5F6", icon_dir="/usr/share/icons"
):
    tmp = "/tmp/icons"
    run_chroot(
        [
            f"git clone https://github.com/vinceliuice/WhiteSur-icon-theme.git {tmp}",
            f"bash {tmp}/install.sh",
        ],
        mnt_point,
        peek=True,
    )
    icon_path = mnt_point / icon_dir
    for svg in [p for p in icon_path.rglob("*.svg") if "scalable" not in p.parts]:
        text = svg.read_text()
        if old in text:
            svg.write_text(text.replace(old, new))
    if (icon_path / "WhiteSur-light").exists():
        shutil.rmtree(icon_path / "WhiteSur-light")


def hide_apps(mnt_point: Path, username: str, applications: list[str]) -> None:
    system_dir = mnt_point / "usr/share/applications"
    user_dir = mnt_point / "home" / username / ".local" / "share" / "applications"
    user_dir.mkdir(parents=True, exist_ok=True)
    for app in applications:
        if not app.endswith(".desktop"):
            app = f"{app}.desktop"
        system_file = system_dir / app
        user_file = user_dir / app
        if system_file.exists() and not user_file.exists():
            user_file.write_text("[Desktop Entry]\nHidden=true\nNoDisplay=true\n")
            log.info(f"{user_file} created")
        else:
            if yes_no(f"{system_file} not found, create anyway?"):
                user_file.write_text("[Desktop Entry]\nHidden=true\nNoDisplay=true\n")
                log.info(f"{user_file} created")
    cmd = [
        f"sudo chown -R {username}:{username} /home/{username}/.local/share/applications"
    ]
    run_chroot(cmd, mountpoint, username)


def clone_dots_to_skel(mnt_point: Path, git_name: str, dots_git: str):
    skel_tmp = Path.home() / dots_git
    cmd = [
        "git",
        "clone",
        f"https://github.com/{git_name}/{dots_git}.git",
        f"{skel_tmp}",
    ]
    if not skel_tmp.exists():
        run_cmd(cmd, True)
        shutil.rmtree(skel_tmp / ".git")
        for p in skel_tmp.iterdir():
            p.rename(p.parent / ("." + p.name))
    copy_dir(skel_tmp, mnt_point / "etc" / "skel")


def process_copy(mnt_point, usb_key_dir: str, user_name: str, to_cp):
    chown_ls = []
    for folder, files_list in to_cp:
        mnt_dir = mnt_point / "home" / user_name / folder
        for f in files_list:
            dest = mnt_dir / f
            copy_file(Path(f"/root/{usb_key_dir}/{f}"), dest)
            chown_line = f"chown {user_name}:{user_name} {dest.relative_to(mnt_point)}"
            chown_ls.append(chown_line)
            ind_key_permission(dest)
        ind_key_permission(mnt_dir)
    return chown_ls


def show_menu(arch_config_handler: ArchConfigHandler) -> None:
    global_menu = GlobalMenu(arch_config_handler.config)
    global_menu.disable_all()
    global_menu.set_enabled("disk_config", True)
    global_menu.set_enabled("__config__", True)
    result: ArchConfig | None = tui.run(global_menu)
    if result is None:
        sys.exit(0)


# ApplicationHandler
def perform_installation(
    arch_config_handler: ArchConfigHandler,
) -> None:
    start_time = time.monotonic()
    info("Starting installation...")
    config = arch_config_handler.config
    if not config.disk_config:
        error("No disk configuration provided")
        return
    disk_config = config.disk_config
    with Installer(mountpoint, disk_config, kernels=["linux"]) as installation:
        if disk_config.config_type != DiskLayoutType.Pre_mount:
            installation.mount_ordered_layout()
        if disk_config.config_type != DiskLayoutType.Pre_mount:
            if (
                disk_config.disk_encryption
                and disk_config.disk_encryption.encryption_type
                != EncryptionType.NoEncryption
            ):
                installation.generate_key_files()
        installation.minimal_installation(
            hostname=hostname, locale_config=LocaleConfiguration("us", "en_US", "UTF-8")
        )
        ###############-Install reflector-###############
        installation.add_additional_packages("reflector")
        log.info("Updating mirror list.")
        options = refl_options + ["--save /etc/pacman.d/mirrorlist"]
        run_chroot([f"reflector {' '.join(options)}"], mountpoint)
        ####################-Systemd-####################
        installation.setup_swap()
        installation.add_bootloader(Bootloader.Systemd)
        modify_systemd(mountpoint)
        installation.copy_iso_network_config()
        installation.set_timezone(timezone)
        #############-Pkg Management-###############
        config_pac_conf(mountpoint, 10, noextract_lines)
        chaotic_repo(mountpoint)
        installation.add_additional_packages(
            amd_pkgs
            + nvidia_pkgs
            + pipewire_pkgs
            + hardware_pkgs
            + base_pkgs
            + cli_pkgs
            + basic_pkgs
            + android_pkgs
            + monitor_pkgs
            + network_pkgs
            + lang_pkgs
            + media_pkgs
            + hyprland_pkgs
            + office_pkgs
            + apple_pkgs
            + coding_pkgs
            + mariadb_pkgs
            + pydep_pkgs
            + gaming_pkgs
            + chaotic_pkgs
        )
        #############-Etc Management-###############
        modify_mkinit(mountpoint, mkinit_hooks)
        sys_dots(mountpoint, script_d, script_pwd_to_cp)
        copy_dir(Path("/root") / wireguard_dir, mountpoint / "etc" / "wireguard")
        installation.enable_service(sys_services + custom_services)
        run_chroot([f"systemctl disable {' '.join(disable_svcs)}"], mountpoint)
        #############-User and Sudo-###############
        clone_dots_to_skel(mountpoint, git_name, dots_git)
        if config.auth_config:
            if config.auth_config.users:
                installation.create_users(config.auth_config.users)
        configure_sudo(user_name, mountpoint, passwordless_sudo=True)
        write_mpd_tmpfiles(mountpoint, user_name)
        run_chroot(
            [
                f"paru -S --noconfirm --needed {' '.join(aur_pkgs)}",
                "xdg-user-dirs-update",
            ],
            mountpoint,
            user_name,
        )
        hide_apps(mountpoint, user_name, apps_to_hide)
        #############-Copy Keys and Script Dir-#############
        copy_dir(script_d, (mountpoint / user_home / script_d.name))
        installation.chown(user_name, str(mountpoint / user_home / script_d.name))
        to_cp = (
            (".ssh", [ssh_key]),
            (".gnupg", [gpg_key]),
            (f"{script_d.name}", [pass_pass]),
        )
        process_copy(mountpoint, usb_key_dir, user_name, to_cp)
        user_service(mountpoint, user_name)
        enable_user_serv(
            [usr_srv_default, usr_srv_sockets, usr_srv_graphical], mountpoint, user_name
        )
        install_icon_theme(mountpoint)
        configure_sudo(user_name, mountpoint, passwordless_sudo=False)
        #############-Own Everything and User Services-###############
        installation.genfstab()
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


def main(pw: str, arch_config_handler: ArchConfigHandler | None = None) -> None:
    arch_config_handler = ArchConfigHandler()
    arch_config_handler.config.auth_config = AuthenticationConfiguration(
        users=[
            User(username=user_name, password=Password(pw), sudo=True, groups=groups)
        ]
    )
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
            return main(pw, arch_config_handler)
    if arch_config_handler.config.disk_config:
        fs_handler = FilesystemHandler(arch_config_handler.config.disk_config)
        if not delayed_warning("Starting device modifications in "):
            return main(pw)
        fs_handler.perform_filesystem_operations()
    ref_cmd = ["reflector", *refl_options, "--save", "/etc/pacman.d/mirrorlist"]
    run_cmd(ref_cmd)
    config_pac_conf(None, 10, noextract_lines)
    chaotic_repo()
    perform_installation(arch_config_handler)


if __name__ == "__main__":
    mnt_cp_keys(usb_key_dir, usb_cp_files, wireguard_dir)
    if not (pw := src_pass_file(usb_key_dir, my_pass)):
        pw = ask_pass(user_name)
    main(pw)
