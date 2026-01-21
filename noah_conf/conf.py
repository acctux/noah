from pathlib import Path
from archinstall.lib.args import LocaleConfiguration

user_name = "nick"
host = "yulia"
my_locale = LocaleConfiguration("us", "en_US", "UTF-8")
refl_opts = [
    "--country US",
    "--protocol https",
    "--latest 15",
    "--sort rate",
    "--number 3",
]
user_script = "user_setup.py"
sys_cp = ["etc", "usr"]
###########-USB FILES-###########
usb_key_dir = "keys"
wireguard_dir = "wireguard"
key_files = ["id_ed25519", "my_sec_gpg.asc", "pass.txt", "pass.py"]
usb_fs_type = "exfat"
min_usb_size = "20G"
###########-USER CONF-############
HOME = Path.home()
desk_dir = HOME / "Desktop"
git_dir = HOME / "Lit"
dot_dir = HOME / "Polka"
docs_dir = git_dir / "Docs"
enc_dir = desk_dir / "Encrypted"
git_user = "acctux"
ssh_dir = ".ssh"
ssh_key = HOME / ssh_dir / key_files[0]
gpg_key = f"{ssh_dir}/{key_files[1]}"
git_repos = [(git_dir, "Docs"), (git_dir, "Noah"), (HOME, "Polka")]
dir_icons = [
    [desk_dir / "Games", "folder-games.svg"],
    [git_dir, "folder-github.svg"],
    [git_dir / "Noah", "folder-root.svg"],
    [docs_dir, "folder-bookmark.svg"],
    [dot_dir, "folder-html.svg"],
    [enc_dir, "folder-locked.svg"],
]
hide_apps = [
    "assistant.desktop",
    "avahi-discover.desktop",
    "bssh.desktop",
    "bvnc.desktop",
    "com.github.FontManager.FontViewer.desktop",
    "jconsole-java-openjdk.desktop",
    "khal.desktop",
    "linguist.desktop",
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
###########-SYMLINK-############
# Polka Config
dots_dir = HOME / "Polka"
dirs_to_link = ["config/systemd/user", "config/nvim", "local/bin"]
base_dir = HOME / "Lit/Docs/base"
ind_dirs = [
    ((base_dir / "fonts"), (HOME / ".local" / "share" / "fonts")),
    ((base_dir / "task"), (HOME / ".config" / "task")),
    ((base_dir / "zsh"), (HOME / ".config" / "zsh")),
]
