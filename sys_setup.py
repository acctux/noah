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
from dataclasses import dataclass
from textwrap import dedent
from utils import get_logger, run_cmd, ask_pass, yes_no
from etc_conf import ly_etc, hardware_etc, net_etc, user_dirs_etc, sys_etc


class UsrSrv(BaseModel):
    source: str
    target: str
    services: list[str]


###########################################################
# ARCHINSTALL CONF
###########################################################
@dataclass(frozen=True)
class Config:
    user_name: str = "nick"
    hostname: str = "yulia"
    kernel: list[str] = [
        "linux",
    ]
    timezone: str = "US/Eastern"
    groups: list[str] = ["adm", "games", "realtime", "storage", "video"]
    terminal: str = "kitty"
    dots_git_repo: str = "acctux/polka"
    usb_key_dir: str = "keys"
    wireguard_dir: str = "wireguard"
    my_pass: str = "pass.py"
    usb_cp_files: list[str] = ["id_ed25519", "my_sec_gpg.asc", "pass.txt"]
    to_cp: dict[str, list[str]] = {
        ".ssh": ["id_ed25519"],
        ".gnupg": ["my_sec_gpg.asc"],
        "scripts": ["pass.txt"],
    }
    firefox_browser: str = "floorp"
    firefox_extensions: list[str] = [
        "return-youtube-dislikes",
        "leechblock-ng",
        "proton-pass",
        "firefox-color",
        "darkreader",
        "flagfox",
        "ublock-origin",
    ]
    mkinit_hooks: list[str] = [
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
    reflector_options: list[str] = [
        "--country US",
        "--protocol https",
        "--latest 15",
        "--sort rate",
        "--number 3",
        "--save /etc/pacman.d/mirrorlist",
    ]
    pkgs: dict[str, list[str]] = {
        "base": [
            # pipewire
            "pipewire",
            "pipewire-alsa",
            "pipewire-jack",
            "pipewire-pulse",
            "gst-plugin-pipewire",
            "libpulse",
            "wireplumber",
            #
            "ananicy-cpp",
            "bluetui",
            "bluez-tools",
            "bluez-utils",  # for loggy
            "brightnessctl",
            "btop",
            "cliphist",
            "rocm-smi-lib",  # btop dependency for amd gpu
            "dmidecode",
            "dosfstools",
            "exfatprogs",
            "jolt",
            "kanshi",
            "kitty",
            "less",
            "mcfly",
            "ntfs-3g",
            "nvtop",
            "realtime-privileges",
            "smartmontools",
            "tuned",
            "udisks2-btrfs",
            "usb_modeswitch",
            "powertop",
            "gnome-logs",
            "systemctl-tui",
            "base-devel",
            "logrotate",
            "ly",
            "plymouth",
            "rebuild-detector",
            "reflector",
            "xdg-user-dirs",
            "zsh-autocomplete",
            "zsh-completions",
            "zsh-syntax-highlighting",
            "starship",
            "trash-cli",
            # Network
            "bind",
            "deluge-gtk",
            "firewalld",
            "impala",
            "iw",
            "openresolv",
            "profile-sync-daemon",
            "protonmail-bridge-core",
            "wireguard-tools",
            "networkmanager",
            # media
            "cava",
            "imv",
            "mpd",
            "mpd-mpris",
            "mpv-mpris",
            "pavucontrol",
            "playerctl",
            "rmpc",
            # Hypr
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
            # Python
            "python-dbus-fast",  # loggy
            "python-gnupg",  # noah
            "python-imaplib2",  # emailcheck
            "python-pandas",  # weather
            "python-pydantic",  # noah
            "python-pyperclip",  # noah
            "python-systemd",  # loggy
            "python-wand",  # wallpaper script
            "otf-firamono-nerd",
            "ttf-liberation",
            "inotify-tools",  # nvim
            "npm",
            "neovim-lspconfig",
            "uv",
            "qt5ct",
            "qt6ct",
            "wl-clipboard",
            "wl-clip-persist",
            "yazi",
            "zbar",  # qr codes
            "qrencode",  # qr codes
            "git-delta",
            "taskwarrior-tui",
            "man-pages",
        ],
        "language": [
            "hunspell-en_us",
            "hyphen-en",
            "tesseract-data-eng",
        ],
        "chaotic_repo": [
            "cachyos-ananicy-rules-git",
            "floorp",
            "octopi",
            "paru",
            "systemd-oomd-defaults",
            "ocrmypdf",
        ],
        "extra": [
            "bat-extras",
            "eza",
            "fd",
            "fzf",
            "github-cli",
            "lazygit",
            "ripgrep-all",
            "sd",
            "ugrep",
            "zoxide",
            "anki",
            "authenticator",
            "baobab",
            "bustle",
            "file-roller",
            "gocryptfs",
            "partitionmanager",
            "qalculate-qt",
            "unrar",  # File roller
            "evince",
            "gimp",
            "guvcview",
            "yt-dlp",  # for mpv youtube playback
            "rofimoji",
            "noto-fonts-emoji",
            # coding
            "rust",
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
            "libreoffice-fresh",
            "coin-or-mp",  # LibreOffice Calc Solver
            "zathura-pdf-mupdf",
            "gnucash",
            "kdeconnect",
            "gvfs-mtp",
            "sshfs",
            "scrcpy",
            "gvfs-afc",
            "gvfs-gphoto2",
            "usbmuxd",
            "dbeaver",
            "jdk-openjdk",
            "mariadb",
            "python-pymysql",
        ],
        "extra_chaos": [
            "logiops",
            "neovim-symlinks",
            "ayugram-desktop-git",
            "qt6-imageformats",  # AyuGram missing dependency
            "betterbird-bin",
            "nchat-git",
            "proton-cachyos-slr",
            "rpcs3-git",
            "eden-git",
        ],
        "gaming": [
            "gnome-chess",
            "gnuchess",
            "lib32-mangohud",
            "lutris",
            "mangohud",
            "mgba-qt",
            "steam",
            "umu-launcher",
            "wine-mono",
            "wine-staging",
            "winetricks",
        ],
    }
    aur_pkgs: list[str] = [
        "wvkbd-deskintl",
    ]
    sys_services: list[str] = [
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
    custom_services: list[str] = [
        "loggy",
        "sysinfo",
    ]
    disable_svcs: list[str] = [
        "getty@tty1",
        "systemd-networkd-wait-online",
    ]
    usr_srv: list[UsrSrv] = [
        UsrSrv(
            source="/usr/lib/systemd/user",
            target="default",
            services=["pipewire-pulse.service", "psd.service"],
        ),
        UsrSrv(
            source="/usr/lib/systemd/user",
            target="sockets",
            services=[
                "pipewire-pulse.socket",
                "gnome-keyring-daemon.socket",
                "gcr-ssh-agent.socket",
                "mpd.socket",
            ],
        ),
        UsrSrv(
            source="/usr/lib/systemd/user",
            target="graphical-session",
            services=[
                "cliphist.service",
                "hypridle.service",
                "hyprsunset.service",
                "swaync.service",
                "waybar.service",
            ],
        ),
        UsrSrv(
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
        ),
        UsrSrv(
            source=f"/home/{user_name}/.config/systemd/user",
            target="timers",
            services=[
                "emailcheck.timer",
                "task-reminder.timer",
                "task-schedule.timer",
                "wall.timer",
            ],
        ),
    ]
    apps_to_hide: list[str] = [
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


def write_files(files: dict[str, str], mnt_point: Path | None) -> None:
    for path, content in files.items():
        flush_content = "\n".join(line.lstrip() for line in content.splitlines())
        path_obj = (mnt_point or Path("/")) / path.lstrip("/")
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.write_text(flush_content + "\n")
        log.info(f"Wrote {path_obj}")


###################################
# USB Files
###################################
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


def mnt_cp_keys(
    key_dir: str | None = None,
    key_files: list[str] | None = None,
    wireguard_dir: str | None = None,
    usb_mnt: Path = Path("/mnt/usb"),
    home: Path = Path.home(),
):
    missing = []
    if key_dir and key_files:
        missing += [k for k in key_files if not (home / key_dir / k).exists()]
    if wireguard_dir and not (home / wireguard_dir).is_dir():
        missing.append(wireguard_dir)
    if not missing:
        log.info("All required files present.")
        return
    if usb_mnt.is_mount() and yes_no("USB mounted, unmount?"):
        run_cmd(["umount", str(usb_mnt)], check=True)
    if not yes_no(f"Mount USB to copy {', '.join(missing)}"):
        return
    selected = get_device()
    usb_mnt.mkdir(parents=True, exist_ok=True)
    run_cmd(["mount", "-o", "ro", str(selected), str(usb_mnt)], check=True)
    time.sleep(2)
    if key_dir and key_files:
        (home / key_dir).mkdir(parents=True, exist_ok=True)
        for k in key_files:
            copy_file(usb_mnt / key_dir / k, home / key_dir / k)
    if wireguard_dir:
        copy_dir(usb_mnt / wireguard_dir, home / wireguard_dir)
    time.sleep(2)
    if yes_no("Files copied, unmount?"):
        run_cmd(["umount", str(usb_mnt)], check=True)


def gfx_drivers() -> list[str]:
    try:
        with open("/proc/cpuinfo") as f:
            cpu = f.read().lower()
    except FileNotFoundError:
        cpu = ""
    gpu = run_cmd(["lspci"], check=True).stdout.lower()
    pkgs = ["mesa"]
    if "nvidia" in gpu:
        pkgs += [
            "lib32-nvidia-utils",
            "libva-nvidia-driver",
            "libva-utils",
            "libxnvctrl",
            "nvidia-open",
            "nvidia-prime",
            "opencl-nvidia",
        ]
    if "amd" in cpu or "amd" in gpu or "ati" in gpu:
        pkgs += [
            "xf86-video-amdgpu",
            "xf86-video-ati",
            "vulkan-radeon",
        ]
    if "intel" in cpu or "intel" in gpu:
        pkgs += [
            "vulkan-intel",
            "libva-intel-driver",
            "intel-media-driver",
            "xf86-video-intel",
        ]
    return pkgs


###################################
# PACMAN
###################################
def chaotic_repo(mnt_point: Path):
    def append_repo(path: Path):
        with path.open("a") as f:
            f.write("\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n")

    key_serv = "keyserver.ubuntu.com"
    chaotic_web = "https://cdn-mirror.chaotic.cx/chaotic-aur/"
    cmds = [
        ["pacman-key", "--init"],
        ["pacman-key", "--recv-key", "3056513887B78AEB", "--keyserver", key_serv],
        ["pacman-key", "--lsign-key", "3056513887B78AEB"],
        ["pacman", "-U", "--noconfirm", f"{chaotic_web}chaotic-keyring.pkg.tar.zst"],
        ["pacman", "-U", "--noconfirm", f"{chaotic_web}chaotic-mirrorlist.pkg.tar.zst"],
    ]
    for cmd in cmds:
        run_cmd(cmd, check=True)
    append_repo(Path("/etc/pacman.conf"))
    run_cmd(["pacman", "-Sy"], check=True)
    run_chroot([" ".join(cmd) for cmd in cmds], mnt_point)
    append_repo(mnt_point / "etc/pacman.conf")
    run_chroot(["pacman -Sy"], mnt_point)


###################################
# ETC/BOOT
###################################
def configure_sudo(user_name: str, mnt_point: Path, pless=False):
    sudoers_content = dedent(f"""\
        {user_name} ALL=(ALL:ALL) {"NOPASSWD:ALL" if pless else "ALL"}
        Defaults    insults
        Defaults    passwd_tries=10
        Defaults    lecture=never
        Defaults    passwd_timeout=0
        Defaults    timestamp_timeout=20
        Defaults    timestamp_type=global
        Defaults    editor=/usr/sbin/nvim, !env_editor
    """)
    write_files({f"etc/sudoers.d/00_{user_name}": sudoers_content}, mnt_point)
    log.info(f"{'Removed' if pless else 'Created'} pass requirement for {user_name}")


def sys_dots(mnt_point: Path, script_dir: Path):
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


def plymouth_setup(mnt_point: Path, boot_opts=["quiet", "splash"]) -> None:
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
    # ^(?!#) = ignore comments, .*? = match any characters up to the \option\
    # \bfmask=\d+  → word boundary, then  digits
    content = re.sub(r"^(?!#).*?\bfmask=\d+", "fmask=0077", content, flags=re.MULTILINE)
    content = re.sub(r"^(?!#).*?\bdmask=\d+", "dmask=0077", content, flags=re.MULTILINE)
    fstab_path.write_text(content)


def modify_mkinit(mnt_point: Path, hooks: list[str], plymouth: bool):
    mkinitcpio_conf_path = f"{mnt_point}/etc/mkinitcpio.conf"
    if plymouth and "plymouth" not in hooks:
        hooks.insert(hooks.index("kms") + 1, "plymouth")
    with open(mkinitcpio_conf_path, "r+") as mkinit:
        content = mkinit.read()
        content = re.sub(r"\nHOOKS=.*", f"\nHOOKS=({' '.join(hooks)})", content)
        mkinit.seek(0)
        mkinit.truncate()
        mkinit.write(content)


###################################
# USR_SVC
###################################
def enable_user_serv(units: list[UsrSrv], mnt_point: Path, username: str):
    user_commands: list[str] = []
    base_dir = Path(f"/home/{username}/.config/systemd/user")
    for unit in units:
        for service in unit.services:
            target_dir = base_dir / f"{unit.target}.target.wants"
            user_commands.append(f"mkdir -p {target_dir}")
            user_commands.append(
                f"ln -sf {unit.source}/{service} {target_dir / service}"
            )
    run_chroot([f"chown -R {username}:{username} /home/{username}/"], mnt_point)
    run_chroot(user_commands, mnt_point, username)


def user_service(
    mnt_point: Path,
    username: str,
    terminal: str,
    user_script="user_setup.py",
    script_dir: str = Path(__file__).resolve().parent.name,
):
    if terminal.strip().lower() == "alacritty":
        terminal = "alacritty -e"
    dir_path = f"home/{username}/.config/systemd/user"
    run_script = f"/home/{username}/{script_dir}/{user_script}"
    name = f"{user_script.rsplit('.', 1)[0]}.service"
    write_files(
        {
            f"{dir_path}/{name}": dedent(f"""\
                [Unit]
                Description=Open {terminal} {run_script} on login
                After=graphical-session.target

                [Service]
                Type=oneshot
                ExecStart=/usr/bin/{terminal} python {run_script}
                Restart=no

                [Install]
                WantedBy=graphical-session.target
            """)
        },
        mnt_point,
    )
    unit = UsrSrv(source=f"/{dir_path}", target="graphical-session", services=[name])
    enable_user_serv([unit], mnt_point, username)


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
    user_dir = f"home/{username}/.local/share/applications"
    for app in applications:
        app = f"{app}.desktop"
        files_dict = {f"{user_dir}/{app}": "[Desktop Entry]\nHide=true\n"}
        write_files(files_dict, mnt_point)
    cmd = [f"chown -R {username}:{username} /home/{username}/.local/share/applications"]
    run_chroot(cmd, mnt_point)


def clone_dots_to_skel(mnt_point: Path, git_repo: str) -> None:
    tmp = mnt_point / "tmp" / git_repo
    cmd = ["git", "clone", f"https://github.com/{git_repo}.git", f"{tmp}"]
    run_cmd(cmd, True)
    shutil.rmtree(tmp / ".git")
    for p in tmp.iterdir():
        p.rename(p.parent / ("." + p.name))
    copy_dir(tmp, mnt_point / "etc" / "skel")


def copy_keys(
    mnt_point: Path, usb_key_dir: str, username: str, to_cp: dict[str, list[str]]
) -> None:
    chown_cmds = []
    for folder, files_list in to_cp.items():
        sys_dir = f"home/{username}/{folder}"
        mnt_dir = mnt_point / sys_dir
        mnt_dir.mkdir(parents=True, exist_ok=True)
        mnt_dir.chmod(0o700)
        chown_cmds.append(f"chown {username}:{username} /{sys_dir}")
        for f in files_list:
            dest = mnt_dir / f
            src = Path(f"/root/{usb_key_dir}/{f}")
            copy_file(src, dest)
            chown_cmds.append(f"chown {username}:{username} /{sys_dir}/{f}")
            dest.chmod(0o600)
    if chown_cmds:
        run_chroot(chown_cmds, mnt_point)


def set_firefox_extensions(mnt_point: Path, browser: str, ext_names: list) -> None:
    file_path = mnt_point / "usr" / "lib" / browser / "distribution" / "policies.json"
    if file_path.exists():
        new_exts = [
            f"https://addons.mozilla.org/firefox/downloads/latest/{ext}/latest.xpi"
            for ext in ext_names
        ]
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
    cf: Config,
    pacman_content: str,
) -> None:
    script_d = Path(__file__).resolve().parent
    user_home = f"home/{cf.user_name}"
    start_time = time.monotonic()
    info("Starting installation...")
    config = arch_config_handler.config
    if not config.disk_config:
        error("No disk configuration provided")
        return
    disk_config = config.disk_config
    with Installer(mountpoint, disk_config, kernels=cf.kernel) as installation:
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
            hostname=cf.hostname,
            locale_config=LocaleConfiguration("us", "en_US", "UTF-8"),
        )
        ###############-Install reflector-###############
        mirror_list = "etc/pacman.d/mirrorlist"
        copy_file(Path(f"/{mirror_list}"), mountpoint / mirror_list)
        ####################-Systemd-####################
        installation.setup_swap()
        installation.add_bootloader(Bootloader.Systemd)
        installation.copy_iso_network_config()
        installation.set_timezone(cf.timezone)
        #############-Pkg Management-###############
        write_files({"etc/pacman.conf": pacman_content}, mnt_point=mountpoint)
        pkgs = gfx_drivers()
        installation.add_additional_packages(pkgs)
        chaotic_repo(mountpoint)
        pkgs = cf.pkgs["base"] + cf.pkgs["language"] + cf.pkgs["chaotic_repo"]
        installation.add_additional_packages(pkgs)
        pkgs = cf.pkgs["extra"] + cf.pkgs["extra_chaos"] + cf.pkgs["gaming"]
        installation.add_additional_packages(pkgs)
        #############-Sys Services-###############
        sys_dots(mountpoint, script_d)
        installation.enable_service(cf.sys_services + cf.custom_services)
        run_chroot([f"systemctl disable {' '.join(cf.disable_svcs)}"], mountpoint)
        #############-Plymouth-###############
        modify_mkinit(mountpoint, cf.mkinit_hooks, plymouth=True)
        plymouth_setup(mountpoint)
        #############-Etc Management-###############
        write_files(
            {
                **user_dirs_etc,
                **net_etc,
                **hardware_etc,
                **ly_etc,
                **sys_etc,
                "etc/tmpfiles.d/mpd.conf": dedent(f"""\
                    d /home/{cf.user_name}/.cache/mpd 0755 {cf.user_name} mpd -
                    d /home/{cf.user_name}/.cache/mpd/playlists 0755 {cf.user_name} mpd -
                """),
            },
            mountpoint,
        )
        copy_dir(Path("/root") / cf.wireguard_dir, mountpoint / "etc" / "wireguard")
        refl_opts_str = "\n".join(cf.reflector_options)
        write_files({"etc/xdg/reflector/reflector.conf": refl_opts_str}, mountpoint)
        set_firefox_extensions(mountpoint, cf.firefox_browser, cf.firefox_extensions)
        #############-User and Sudo-###############
        clone_dots_to_skel(mountpoint, cf.dots_git_repo)
        if config.auth_config:
            if config.auth_config.users:
                installation.create_users(config.auth_config.users)
        configure_sudo(cf.user_name, mountpoint, pless=True)
        cmd = [f"paru -S --noconfirm --needed {' '.join(cf.aur_pkgs)}"]
        run_chroot(cmd, mountpoint, cf.user_name)
        run_chroot(["xdg-user-dirs-update"], mountpoint, cf.user_name)
        configure_sudo(cf.user_name, mountpoint)
        #############-Copy Keys and Script Dir-#############
        copy_dir(script_d, (mountpoint / user_home / script_d.name))
        installation.chown(cf.user_name, str(mountpoint / user_home / script_d.name))
        copy_keys(mountpoint, cf.usb_key_dir, cf.user_name, cf.to_cp)
        #############-User Services-#############
        user_service(mountpoint, cf.user_name, cf.terminal)
        enable_user_serv(cf.usr_srv, mountpoint, cf.user_name)
        #############-Apps/Icons-#############
        hide_apps(mountpoint, cf.user_name, cf.apps_to_hide)
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


def main(pw: str, cf: Config) -> None:
    arch_config_handler = ArchConfigHandler()
    user = [
        User(username=cf.user_name, password=Password(pw), sudo=True, groups=cf.groups)
    ]
    arch_config_handler.config.auth_config = AuthenticationConfiguration(users=user)
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
            return main(pw, cf)
    if arch_config_handler.config.disk_config:
        fs_handler = FilesystemHandler(arch_config_handler.config.disk_config)
        if not delayed_warning("Starting device modifications in "):
            return main(pw, cf)
        fs_handler.perform_filesystem_operations()
    run_cmd(
        ["reflector", *(part for opt in cf.reflector_options for part in opt.split())]
    )
    pacman_content: str = dedent("""\
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
    write_files({"etc/pacman.conf": pacman_content}, mnt_point=None)
    perform_installation(arch_config_handler, cf, pacman_content)


if __name__ == "__main__":
    cf = Config()
    mnt_cp_keys(cf.usb_key_dir, cf.usb_cp_files, cf.wireguard_dir)
    if not (pw := src_pass_file(cf.usb_key_dir, cf.my_pass)):
        log.info("No password file found. Please enter Password")
        pw = ask_pass(cf.user_name)
    main(pw, cf)
