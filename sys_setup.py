#!/usr/bin/env python3
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
from textwrap import dedent
from utils import get_logger, run_cmd, ask_pass
from etc_conf import ly_etc, logid_etc, hardware_etc, maria_etc, net_etc, user_dirs_etc


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
# Browser
###########################################################
firefox_extensions = [
    "return-youtube-dislikes",
    "leechblock-ng",
    "proton-pass",
    "firefox-color",
]
firefox_browser = "firedragon"
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
pacman_content = dedent("""\
        [options]
        HoldPkg = pacman glibc
        Architecture = auto
        Color
        ILoveCandy
        ParallelDownloads = 10
        DownloadUser = alpm
        SigLevel    = Required DatabaseOptional
        LocalFileSigLevel = Optional
        NoExtract = etc/xdg/autostart/firewall-applet.desktop
        NoExtract = usr/share/icons/capitaine-cursors/*

        [core]
        Include = /etc/pacman.d/mirrorlist

        [extra]
        Include = /etc/pacman.d/mirrorlist

        [multilib]
        Include = /etc/pacman.d/mirrorlist
    """)
reflector_options = [
    "--country US",
    "--protocol https",
    "--latest 15",
    "--sort rate",
    "--number 3",
    "--save /etc/pacman.d/mirrorlist",
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
    "dmidecode",
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
    "jolt",
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
    "reflectorxdg-user-dirs",
]
cli_pkgs = [
    "bat-extras",
    "eza",
    "cliphist",
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
    "featherpad",
    "file-roller",
    "gocryptfs",
    "khal",
    "partitionmanager",
    "qalculate-qt",
    "qrencode",  # qr codes
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
    "wpa_supplicant",
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
    "yt-dlp",  # for mpv youtube playback
]
hyprland_pkgs = [
    "capitaine-cursors",
    "fuzzel",
    "gnome-keyring",
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
    "tombi",
    "ty",
    "vscode-css-languageserver",
    "vscode-json-languageserver",
    "yaml-language-server",
    # Formatters
    "ruff",
    "shfmt",
    "stylua",
    "yamlfmt",
    # Lint
    "shellcheck",
    "biome",
    "luacheck",
    "yamllint",
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
chaotic_pkgs = [
    "ayugram-desktop-git",
    "qt6-imageformats",  # AyuGram missing dependency
    "betterbird-bin",
    "cachyos-ananicy-rules-git",
    "eden-git",
    "firedragon",
    "logiops",
    "nchat-git",
    "neovim-symlinks",
    "ocrmypdf",
    "octopi",
    "paru",
    "proton-cachyos-slr",
    "rpcs3-git",
    "systemd-oomd-defaults",
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
custom_services = ["loggy", "sysinfo"]
disable_svcs = ["getty@tty1", "systemd-networkd-wait-online"]
###########################################################
# USER SERVICES
###########################################################


class UserSrv(BaseModel):
    source: str = "/usr/lib/systemd/user"
    services: list[str]
    target: str


usr_srv = UserSrv(
    source="/usr/lib/systemd/user",
    target="default",
    services=["pipewire-pulse.service", "psd.service"],
)
usr_sockets = UserSrv(
    source="/usr/lib/systemd/user",
    target="sockets",
    services=[
        "pipewire-pulse.socket",
        "gnome-keyring-daemon.socket",
        "gcr-ssh-agent.socket",
        "mpd.socket",
    ],
)
usr_graphical = UserSrv(
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
        "kanshi.service",
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
# HIDE APPS
###########################################################
apps_to_hide = [
    "avahi-discover",
    "bssh",
    "btop",
    "bvnc",
    "jshell-java-openjdk",
    "jconsole-java-openjdk",
    "libreoffice-base",
    "libreoffice-draw",
    "libreoffice-impress",
    "libreoffice-math",
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
# CONSTANTS
###########################################################
user_home = f"home/{user_name}"
HOME = Path.home()
mountpoint = Path("/mnt/arch")
log = get_logger("Noah")


#########################
# UTILS
#########################
def run_chroot(
    commands: list[str], mnt_point: Path, username: str | None = None, peek=True
):
    script_path = "var/tmp/user-commands.sh"
    chroot_path = mnt_point / script_path
    chroot_path.parent.mkdir(parents=True, exist_ok=True)
    with open(chroot_path, "w") as script:
        script.write("#!/bin/bash\n")
        if peek:
            script.write("set -e\n")
        for cmd in commands:
            if username:
                log.info(f"Will run as {username}: {cmd}")
                cmd = f"su - {username} -c {shlex.quote(cmd)}"
            log.info(f"Chroot run: {cmd}")
            script.write(cmd + "\n")
    chroot_path.chmod(0o755)
    SysCommand(f"arch-chroot -S {mnt_point} /{script_path}")
    chroot_path.unlink()


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


def write_files(files: dict[str, str], mnt_point: Path | None) -> None:
    for path, content in files.items():
        flush_content = "\n".join(line.lstrip() for line in content.splitlines())
        path_obj = (mnt_point or Path("/")) / path.lstrip("/")
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.write_text(flush_content + "\n")
        log.info(f"Wrote {path_obj}")


def ind_key_permission(path: Path, f_permissions=0o600, d_permissions=0o700) -> None:
    if path.exists():
        if path.is_file():
            path.chmod(f_permissions)
        else:
            path.chmod(d_permissions)
    else:
        log.warning(f"{path} not found.")


def yes_no(prompt: str, default: bool = True) -> bool:
    while True:
        suffix = "(Y/n)" if default else "(y/N)"
        response = input(f"{prompt} {suffix}: ").strip().lower()
        if response == "":
            return default
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        log.warning("Please enter 'y' or 'n'.")


###################################
# UTILS
###################################
def check_missing(
    key_dir: str | None = None,
    key_files: list[str] | None = None,
    wireguard_dir: str | None = None,
) -> list[str]:
    missing_files = []
    if key_files:
        for key in key_files:
            if not (HOME / f"{key_dir}/{key}").exists():
                missing_files.append(key)
    if wireguard_dir and not (HOME / wireguard_dir).is_dir():
        missing_files.append(wireguard_dir)
    return missing_files


def get_device(min_gb=20, usb_fs_type="ext4") -> str:
    data = json.loads(
        subprocess.check_output(
            ["lsblk", "-J", "-o", "NAME,SIZE,FSTYPE,MOUNTPOINT,TYPE"], text=True
        )
    )
    candidates = []

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
    run_cmd(cmd, check=True)
    log.info(f"Unmounted USB from {usb_mount}.")


def mnt_cp_keys(
    key_dir: str | None = None,
    key_files: list[str] | None = None,
    wireguard_dir: str | None = None,
    usb_mnt=Path("/mnt/usb"),
):
    if usb_mnt.is_mount():
        umount_usb(usb_mnt)
    if (key_dir and key_files) or wireguard_dir:
        missing = check_missing(key_dir, key_files, wireguard_dir)
        if missing:
            if yes_no(f"Mount USB to copy {', '.join(missing)}"):
                selected_path = get_device()
                usb_mnt.mkdir(parents=True, exist_ok=True)
                cmd = ["mount", "-o", "ro", str(selected_path), str(usb_mnt)]
                run_cmd(cmd, check=True)
                time.sleep(2)
                if key_dir and key_files:
                    usb_cp_keys(usb_mnt, key_dir, key_files)
                if wireguard_dir:
                    if not (HOME / wireguard_dir).exists():
                        copy_dir(usb_mnt / wireguard_dir, HOME / wireguard_dir)
                time.sleep(2)
                umount_usb(usb_mnt)
    else:
        log.info("All required files present.")


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
    dir_path = f"home/{user_name}/.config/systemd/user"
    run_script = f"/home/{user_name}/{script_dir}/{user_script}"
    name = f"{user_script.rsplit('.', 1)[0]}.service"
    write_files(
        {
            f"{dir_path}/{name}": dedent(f"""\
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
        },
        mnt_point,
    )
    unit = UserSrv(source=f"/{dir_path}", target="graphical-session", services=[name])
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
    else:
        for cmd in cmds_setup:
            run_cmd(cmd, check=True)
        pacman_conf = Path("/etc/pacman.conf")
    with pacman_conf.open("a") as f:
        f.write("\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n")
    if mnt_point:
        run_chroot(["pacman -Sy"], mnt_point)
    else:
        run_cmd(["pacman", "-Sy"], check=True)


###################################
# ETC/BOOT
###################################
def configure_sudo(user_name: str, mnt_point: Path, passwordless_sudo=True):
    sudoers_file = f"etc/sudoers.d/00_{user_name}"
    if passwordless_sudo:
        sudoers_line = f"{user_name} ALL=(ALL:ALL) NOPASSWD:ALL"
        prt_val = "without password requirement"
    else:
        sudoers_line = f"{user_name} ALL=(ALL:ALL) ALL"
        prt_val = "with password requirement"
    sudoers_content = dedent(f"""\
        {sudoers_line}
        Defaults    insults
        Defaults    passwd_tries=10
        Defaults    lecture=never
        Defaults    passwd_timeout=0
        Defaults    timestamp_timeout=20
        Defaults    timestamp_type=global
        Defaults    editor=/usr/sbin/nvim, !env_editor
    """)
    write_files({sudoers_file: sudoers_content}, mnt_point)
    log.info(f"Created {sudoers_file} {prt_val} for {user_name}")


def sys_dots(mnt_point: Path, script_dir: Path):
    sys_dir_cp = ["etc", "usr"]
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


def systemd_post(mnt_point: Path, boot_opts=["quiet", "splash"]) -> None:
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
    write_files(
        {
            "boot/loader/loader.conf": dedent("""\
                default @saved
                timeout 1
                editor no
            """),
            "etc/pacman.d/hooks/95-systemd-boot.hook": dedent("""\
                [Trigger]
                Type = Package
                Operation = Upgrade
                Target = systemd

                [Action]
                Description = Gracefully upgrading systemd-boot...
                When = PostTransaction
                Exec = /usr/bin/systemctl restart systemd-boot-update.service
            """),
            "etc/systemd/journald.conf.d/00-journal-size.conf": dedent("""\
                [Journal]
                SystemMaxUse=50M
            """),
        },
        mnt_point,
    )


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


###################################
# User Space
###################################
def install_icon_theme(
    mnt_point: Path,
    git="vinceliuice/WhiteSur-icon-theme",
    old="#ffffff",
    new="#F4F5F6",
    icon_dir="/usr/share/icons",
):
    tmp = "/tmp/icons"
    log.info("Installing {")
    cmd = [f"git clone https://github.com/{git}.git {tmp}", f"bash {tmp}/install.sh"]
    run_chroot(cmd, mnt_point)
    icon_path = mnt_point / icon_dir
    for svg in [p for p in icon_path.rglob("*.svg") if "scalable" not in p.parts]:
        text = svg.read_text()
        if old in text:
            svg.write_text(text.replace(old, new))
    if (icon_path / "WhiteSur-light").exists():
        shutil.rmtree(icon_path / "WhiteSur-light")


def hide_apps(mnt_point: Path, username: str, applications: list[str]) -> None:
    user_dir = mnt_point / "home" / username / ".local" / "share" / "applications"
    files_to_write = {}
    for app in applications:
        if not app.endswith(".desktop"):
            app = f"{app}.desktop"
        files_to_write[str(user_dir / app)] = (
            "[Desktop Entry]\nHidden=true\nNoDisplay=true\n"
        )
    write_files(files_to_write, mnt_point)
    cmd = [f"chown -R {username}:{username} /home/{username}/.local/share/applications"]
    run_chroot(cmd, mnt_point)


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


def process_copy(
    mnt_point: Path, usb_key_dir: str, user_name: str, to_cp: dict[str, list[str]]
) -> None:
    chown_cmds = []
    for folder, files_list in to_cp.items():
        mnt_dir = mnt_point / "home" / user_name / folder
        mnt_dir.mkdir(parents=True, exist_ok=True)
        for f in files_list:
            dest = mnt_dir / f
            src = Path(f"/root/{usb_key_dir}/{f}")
            copy_file(src, dest)
            rel_path = dest.relative_to(mnt_point)
            chown_cmds.append(f"chown {user_name}:{user_name} /{rel_path}")
            ind_key_permission(dest)
        rel_dir = mnt_dir.relative_to(mnt_point)
        chown_cmds.append(f"chown {user_name}:{user_name} /{rel_dir}")
        ind_key_permission(mnt_dir)
    if chown_cmds:
        run_chroot(chown_cmds, mnt_point)


def set_firefox_extensions(mnt_point: Path, browser: str, ext_names: list):
    file_path = mnt_point / "usr" / "lib" / browser / "distribution" / "policies.json"
    new_exts = [
        f"https://addons.mozilla.org/firefox/downloads/latest/{ext}/latest.xpi"
        for ext in ext_names
    ]
    data = {"policies": {"Extensions": {"Install": []}}}
    if file_path.exists():
        data = json.loads(file_path.read_text())
    install = data["policies"]["Extensions"]["Install"]
    for ext in new_exts:
        if ext not in install:
            install.append(ext)
    file_path.write_text(json.dumps(data, indent=2))
    log.info("Firefox extensions updated successfully.")


###################################
# Archinstall
###################################
def show_menu(arch_config_handler: ArchConfigHandler) -> None:
    global_menu = GlobalMenu(arch_config_handler.config)
    global_menu.disable_all()
    global_menu.set_enabled("disk_config", True)
    global_menu.set_enabled("__config__", True)
    result: ArchConfig | None = tui.run(global_menu)
    if result is None:
        sys.exit(0)


def perform_installation(
    arch_config_handler: ArchConfigHandler,
) -> None:
    script_d = Path(__file__).resolve().parent
    start_time = time.monotonic()
    info("Starting installation...")
    config = arch_config_handler.config
    if not config.disk_config:
        error("No disk configuration provided")
        return
    disk_config = config.disk_config
    with Installer(mountpoint, disk_config, kernels=kernel) as installation:
        if disk_config.config_type != DiskLayoutType.Pre_mount:
            installation.mount_ordered_layout()
        if disk_config.config_type != DiskLayoutType.Pre_mount:
            if (
                disk_config.disk_encryption
                and disk_config.disk_encryption.encryption_type
                != EncryptionType.NO_ENCRYPTION
            ):
                installation.generate_key_files()
        installation.minimal_installation(
            hostname=hostname, locale_config=LocaleConfiguration("us", "en_US", "UTF-8")
        )
        ###############-Install reflector-###############
        mirror_list = "etc/pacman.d/mirrorlist"
        copy_file(Path(f"/{mirror_list}"), mountpoint / mirror_list)
        refl_opts_str = "\n".join(reflector_options)
        write_files({"etc/xdg/reflector/reflector.conf": refl_opts_str}, mountpoint)
        ####################-Systemd-####################
        installation.setup_swap()
        installation.add_bootloader(Bootloader.Systemd)
        systemd_post(mountpoint)
        installation.copy_iso_network_config()
        installation.set_timezone(timezone)
        #############-Pkg Management-###############
        write_files({"etc/pacman.conf": pacman_content}, mnt_point=mountpoint)
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
        sys_dots(mountpoint, script_d)
        write_files(
            {
                **user_dirs_etc,
                **net_etc,
                **maria_etc,
                **hardware_etc,
                **logid_etc,
                **ly_etc,
            },
            mountpoint,
        )
        copy_dir(Path("/root") / wireguard_dir, mountpoint / "etc" / "wireguard")
        installation.enable_service(sys_services + custom_services)
        run_chroot([f"systemctl disable {' '.join(disable_svcs)}"], mountpoint)
        set_firefox_extensions(mountpoint, firefox_browser, firefox_extensions)
        #############-User and Sudo-###############
        clone_dots_to_skel(mountpoint, git_name, dots_git)
        if config.auth_config:
            if config.auth_config.users:
                installation.create_users(config.auth_config.users)
        configure_sudo(user_name, mountpoint, passwordless_sudo=True)
        log.info(f"Installing {aur_pkgs}")
        run_chroot(
            [
                f"paru -S --noconfirm --needed {' '.join(aur_pkgs)}",
                "xdg-user-dirs-update",
            ],
            mountpoint,
            user_name,
        )
        configure_sudo(user_name, mountpoint, passwordless_sudo=False)
        #############-Copy Keys and Script Dir-#############
        copy_dir(script_d, (mountpoint / user_home / script_d.name))
        installation.chown(user_name, str(mountpoint / user_home / script_d.name))
        to_cp = {".ssh": [ssh_key], ".gnupg": [gpg_key], "scripts": [pass_pass]}
        process_copy(mountpoint, usb_key_dir, user_name, to_cp)
        #############-User Services-#############
        user_service(mountpoint, user_name)
        enable_user_serv(
            [usr_srv, usr_sockets, usr_graphical, cust_graphic, cust_timer],
            mountpoint,
            user_name,
        )
        #############-Apps/Icons-#############
        hide_apps(mountpoint, user_name, apps_to_hide)
        log.info("Installing icon theme.")
        install_icon_theme(mountpoint)
        #############-Fstab-###############
        installation.genfstab()
        modify_fstab(mountpoint)
        #############-Menu-###############
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


def main(pw: str) -> None:
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
            return main(pw)
    if arch_config_handler.config.disk_config:
        fs_handler = FilesystemHandler(arch_config_handler.config.disk_config)
        if not delayed_warning("Starting device modifications in "):
            return main(pw)
        fs_handler.perform_filesystem_operations()
    cmd = ["reflector", *(part for opt in reflector_options for part in opt.split())]
    run_cmd(cmd)
    write_files({"etc/pacman.conf": pacman_content}, mnt_point=None)
    chaotic_repo()
    perform_installation(arch_config_handler)


if __name__ == "__main__":
    mnt_cp_keys(usb_key_dir, usb_cp_files, wireguard_dir)
    if not (pw := src_pass_file(usb_key_dir, my_pass)):
        log.info("No password file found. Please enter Password")
        pw = ask_pass(user_name)
    main(pw)
