from pathlib import Path
from utils import UserSrv


###########################################################
# FOLDER DECLARATIONS
###########################################################
HOME = Path.home()
SHARE = HOME / ".local" / "share"
CONF = HOME / ".config"
BASE = HOME / "Lit" / "Docs" / "base"
DESKTOP = HOME / "Desktop"
GIT_DIR = HOME / "Lit"
DOTS_DIR = HOME / "Polka"
DOCS = GIT_DIR / "Docs"
ENC_DIR = DESKTOP / "Encrypted"
GAMES_DIR = DESKTOP / "Games"
###########################################################
# ARCHINSTALL CONF
###########################################################
user_name = "nick"
hostname = "yulia"
kernel = ["linux"]
kb_layout = "us"
sys_lang = "en_US"
sys_enc = "UTF-8"
timezone = "US/Eastern"
###########################################################
# GROUPS
###########################################################
groups = ["adm", "games", "realtime", "storage", "video"]
###########################################################
# SYS SERVICES
###########################################################
sys_services = [
    "ananicy-cpp",
    "bluetooth",
    "tlp",
    "iwd",
    "ly@tty1",
    "named",
    "firewalld",
    "swayosd-libinput-backend",
    "systemd-networkd",
    "systemd-oomd",
    "systemd-timesyncd",
    "btrfs-scrub@-.timer",
    "btrfs-scrub@home.timer",
    "fstrim.timer",
    "logrotate.timer",
    "man-db.timer",
    "paccache.timer",
    "reflector.timer",
    #####-Custom-####
    "loggy",
    "wireguard-list",
]
disable_svcs = ["getty@tty1", "systemd-networkd-wait-online"]
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
# USER SERVICES
###########################################################
user_services = [
    UserSrv(
        target="default.target.wants",
        services=["pipewire-pulse.service"],
        source_dir=Path("/usr/lib/systemd/user"),
    ),
    UserSrv(
        target="sockets.target.wants",
        services=["pipewire-pulse.socket"],
        source_dir=Path("/usr/lib/systemd/user"),
    ),
]
###########################################################
# FOLDERS TO COPY FROM SCRIPT DIR TO /mnt
###########################################################
script_pwd_to_cp = ["etc", "usr"]
###########################################################
# REFLECTOR OPTIONS
###########################################################
refl_options = [
    "--country US",
    "--protocol https",
    "--latest 10",
    "--sort rate",
    "--number 3",
]
###########################################################
# USB PASSED FILES CONF
###########################################################
usb_fs_type = "exfat"
min_usb_size = "20G"
usb_key_dir = "keys"
ssh_key = "id_ed25519"
gpg_key = "my_sec_gpg.asc"
pass_manager_pass = "pass.txt"
user_pass_file = "pass.py"
wireguard_dir = "wireguard"
usb_cp_files = [ssh_key, gpg_key, pass_manager_pass]
###########################################################
# GIT
###########################################################
git_user = "acctux"
GIT_REPOS = [(GIT_DIR, "Docs"), (GIT_DIR, "noah"), (HOME, "Polka")]
###########################################################
# ICONS
###########################################################
custom_dir_icons = [
    (GAMES_DIR, "folder-games.svg"),
    (GIT_DIR, "folder-github.svg"),
    (GIT_DIR / "Noah", "folder-root.svg"),
    (DOCS, "folder-bookmark.svg"),
    (DOTS_DIR, "folder-html.svg"),
    (ENC_DIR, "folder-locked.svg"),
]
###########################################################
# SYMLINK/DOT FILE
############################################################
dirs_to_link = ["config/systemd/user", "config/nvim", "local/bin"]
ind_dirs = [
    ((BASE / "fonts"), (SHARE / "fonts")),
    ((BASE / "task"), (CONF / "task")),
    ((BASE / "zsh"), (CONF / "zsh")),
]
###########################################################
# HIDE APPS
###########################################################
hide_apps = [
    "avahi-discover.desktop",
    "bssh.desktop",
    "btop.desktop",
    "bvnc.desktop",
    "com.github.FontManager.FontViewer.desktop",
    "jshell-java-openjdk.desktop",
    "jconsole-java-openjdk.desktop",
    "khal.desktop",
    "libreoffice-base.desktop",
    "libreoffice-draw.desktop",
    "libreoffice-math.desktop",
    "nvtop.desktop",
    "octopi-cachecleaner.desktop",
    "octopi-notifier.desktop",
    "octopi-repoeditor.desktop",
    "org.gnome.Nautilus.desktop",
    "org.gnome.baobab.desktop",
    "org.kde.kdeconnect.nonplasma.desktop",
    "qt5ct.desktop",
    "qt6ct.desktop",
    "qv4l2.desktop",
    "qvidcap.desktop",
    "taskwarrior-tui.desktop",
    "uuctl.desktop",
    "xgps.desktop",
    "xgpsspeed.desktop",
]
