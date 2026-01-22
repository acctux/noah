from pathlib import Path


HOME = Path.home()
###########################################################
# SYSTEM CONF
###########################################################
user_name = "nick"
hostname = "yulia"
refl_options = [
    "--country US",
    "--protocol https",
    "--latest 15",
    "--sort rate",
    "--number 3",
]
sys_dir_to_cp = [
    "etc",
    "usr",
]
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
groups = [
    "adm",
    "games",
    "realtime",
    "storage",
    "video",
]
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
# USB PASSED FILES CONF
###########################################################
usb_key_dir = "keys"
wireguard_dir = "wireguard"
ssh_key = "id_ed25519"
gpg_key = "my_sec_gpg.asc"
pass_manager_pass_path = HOME / ".ssh" / "pass.txt"
user_pass_file = "pass.py"
usb_cp_files = [ssh_key, gpg_key, pass_manager_pass_path.name, user_pass_file]
usb_fs_type = "exfat"
min_usb_size = "20G"

###########################################################
# USER CONF
###########################################################
git_dir = HOME / "Lit"
dot_dir = HOME / "Polka"
docs_dir = git_dir / "Docs"

enc_dir = HOME / "Desktop" / "Encrypted"
git_user = "acctux"
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
