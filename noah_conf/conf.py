from pathlib import Path
from utils import UserSrv


user_name = "nick"
host = "yulia"
refl_opts = [
    "--country US",
    "--protocol https",
    "--latest 15",
    "--sort rate",
    "--number 3",
]
user_script = "user_setup.py"
sys_cp = ["etc", "usr"]
groups = ["audio", "games", "gamemode", "log", "realtime", "storage", "video"]
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
user_services = [
    UserSrv(target="default.target.wants", services=["pipewire-pulse.service"]),
    UserSrv(
        target="sockets.target.wants",
        services=[
            "pipewire-pulse.socket",
            "gnome-keyring-daemon.socket",
            "gcr-ssh-agent.socket",
        ],
    ),
    UserSrv(
        target="graphical-session.target.wants",
        services=["waybar.service", "swaync.service"],
    ),
]
###########-USB FILES-###########
usb_key_dir = "keys"
wireguard_dir = "wireguard"
key_files = ["id_ed25519", "my_sec_gpg.asc", "pass.txt", "pass.py"]
usb_fs_type = "exfat"
min_usb_size = "20G"
###########-USER CONF-############
HOME = Path.home()
git_dir = HOME / "Lit"
dot_dir = HOME / "Polka"
docs_dir = git_dir / "Docs"
enc_dir = HOME / "Desktop" / "Encrypted"
git_user = "acctux"
ssh_dir = ".ssh"
ssh_key = HOME / ssh_dir / key_files[0]
gpg_key = f"{ssh_dir}/{key_files[1]}"
git_repos = [(git_dir, "Docs"), (git_dir, "noah"), (HOME, "Polka")]
dir_icons = [
    [HOME / "Desktop" / "Games", "folder-games.svg"],
    [git_dir, "folder-github.svg"],
    [git_dir / "Noah", "folder-root.svg"],
    [docs_dir, "folder-bookmark.svg"],
    [dot_dir, "folder-html.svg"],
    [enc_dir, "folder-locked.svg"],
]
hide_apps = [
    "avahi-discover.desktop",
    "bssh.desktop",
    "bvnc.desktop",
    "com.github.FontManager.FontViewer.desktop",
    "jconsole-java-openjdk.desktop",
    "khal.desktop",
    "octopi-cachecleaner.desktop",
    "octopi-notifier.desktop",
    "octopi-repoeditor.desktop",
    "org.gnome.Nautilus.desktop",
    "org.gnome.baobab.desktop",
    "org.kde.kdeconnect.nonplasma.desktop",
    "qv4l2.desktop",
    "qvidcap.desktop",
    "xgps.desktop",
    "xgpsspeed.desktop",
]
