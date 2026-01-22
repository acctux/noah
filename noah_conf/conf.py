from pathlib import Path
from noah_lib.sys_files import UserSrv


###########################################################
# FOLDER DECLARATIONS
###########################################################
HOME = Path.home()
SHARE = HOME / ".local" / "share"
CONF = HOME / ".config"
SSH_DIR = HOME / ".ssh"
GPG_DIR = HOME / ".gnupg"
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
groups = [
    "adm",
    "games",
    "realtime",
    "storage",
    "video",
]
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
disable_svcs = [
    "getty@tty1",
    "systemd-networkd-wait-online",
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
# USER SERVICES
###########################################################
user_services = [
    UserSrv(
        target="default.target.wants",
        services=["pipewire-pulse.service"],
    ),
    UserSrv(
        target="sockets.target.wants",
        services=["pipewire-pulse.socket"],
    ),
]
###########################################################
# FOLDERS TO COPY FROM SCRIPT DIR TO /mnt
###########################################################
sys_dir_to_cp = [
    "etc",
    "usr",
]
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
usb_cp_files = [
    ssh_key,
    gpg_key,
    pass_manager_pass,
    user_pass_file,
]
###########################################################
# GIT
###########################################################
git_user = "acctux"
GIT_REPOS = [
    (GIT_DIR, "Docs"),
    (GIT_DIR, "noah"),
    (HOME, "Polka"),
]
###########################################################
# ICONS
###########################################################
custom_dir_icons = [
    [GAMES_DIR, "folder-games.svg"],
    [GIT_DIR, "folder-github.svg"],
    [GIT_DIR / "Noah", "folder-root.svg"],
    [DOCS, "folder-bookmark.svg"],
    [DOTS_DIR, "folder-html.svg"],
    [ENC_DIR, "folder-locked.svg"],
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
    "bvnc.desktop",
    "com.github.FontManager.FontViewer.desktop",
    "jshell-java-openjdk.desktop",
    "jconsole-java-openjdk.desktop",
    "khal.desktop",
    "nvtop.desktop",
    "octopi-cachecleaner.desktop",
    "octopi-notifier.desktop",
    "octopi-repoeditor.desktop",
    "org.gnome.Nautilus.desktop",
    "org.gnome.baobab.desktop",
    "org.kde.kdeconnect.nonplasma.desktop",
    "qv4l2.desktop",
    "qvidcap.desktop",
    "taskwarrior-tui.desktop",
    "uuctl.desktop",
    "xgps.desktop",
    "xgpsspeed.desktop",
]
