from pathlib import Path
from utils import UserSrv


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
git_dir = "Lit"
git_repos = [(git_dir, "Docs"), (git_dir, "noah"), (git_dir, "Polka")]
dots_dir = f"{git_dir}/Polka"
###########################################################
# ICONS
###########################################################
dirs_icons = [
    ("Desktop/Games", "folder-games.svg"),
    (git_dir, "folder-github.svg"),
    (f"{git_dir}/Noah", "folder-root.svg"),
    (f"{git_dir}/Docs", "folder-bookmark.svg"),
    (dots_dir, "folder-html.svg"),
    ("Desktop/Encrypted", "folder-locked.svg"),
]
###########################################################
# SYMLINK/DOT FILE
############################################################
dirs_to_link = ["config/systemd/user", "config/nvim", "local/bin"]
ind_dirs = [
    ((f"{git_dir}/Docs/fonts"), (".local/share/fonts")),
    ((f"{git_dir}/Docs/task"), (".config/task")),
    ((f"{git_dir}/Docs/zsh"), (".config/zsh")),
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
