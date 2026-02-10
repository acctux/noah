from utils import UserGitRepo

###########################################################
# ARCHINSTALL CONF
###########################################################
user_name = "nick"
ssh_key = "id_ed25519"
gpg_key = "my_sec_gpg.asc"
usb_key_dir = "keys"
pass_manager_pass = "pass.txt"
###########################################################
# GIT
###########################################################
git_user = "acctux"
git_dir = "Lit"
git_repos = [UserGitRepo(target_dir=git_dir, repos=["Docs", "noah", "polka"])]
dots_dir = "Polka"
docs = f"{git_dir}/Docs"
enc_dir = "Desktop/Encrypted"
###########################################################
# ICONS
###########################################################
dirs_icons = [
    ("Desktop/Games", "folder-games.svg"),
    ("Lit", "folder-github.svg"),
    ("Lit/Noah", "folder-root.svg"),
    ("Lit/Docs", "folder-bookmark.svg"),
    ("Polka", "folder-html.svg"),
    ("Desktop/Encrypted", "folder-locked.svg"),
]
###########################################################
# SYMLINK/DOT FILE
############################################################
dirs_to_link = ["config/systemd/user", "config/nvim", "local/bin"]
ind_dirs = [
    ((f"{docs}/fonts"), (".local/share/fonts")),
    ((f"{docs}/task"), (".config/task")),
    ((f"{docs}/zsh"), (".config/zsh")),
]
###########################################################
# HIDE APPS
###########################################################
hide_apps = [
    "avahi-discover.desktop",
    "bssh.desktop",
    "btop.desktop",
    "bvnc.desktop",
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
    "org.gnome.baobab.desktop",
    "org.kde.kdeconnect.nonplasma.desktop",
    "qt5ct.desktop",
    "qt6ct.desktop",
    "qv4l2.desktop",
    "qvidcap.desktop",
    "scrcpy-console.desktop",
    "taskwarrior-tui.desktop",
    "uuctl.desktop",
    "xgps.desktop",
    "xgpsspeed.desktop",
]
###########################################################
# YAZI
###########################################################
yazi_plugins = [
    "yazi-rs/plugins:jump-to-char",
    "uhs-robert/sshfs",
    "boydaihungst/gvfs",
    "uhs-robert/recycle-bin",
    "dedukun/bookmarks",
]
