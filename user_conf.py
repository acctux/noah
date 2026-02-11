from utils import UserGitRepo

###########################################################
# CONF
###########################################################
user_name = "nick"
ssh_key = "id_ed25519"
gpg_key = "my_sec_gpg.asc"
pass_manager_pass = "pass.txt"
git_user = "acctux"
git_dir = "Lit"
docs = "Docs"
desk = "Desktop"
games = "Games"
enc_dir = "Encrypted"
###########################################################
# GIT/DOT FILE
############################################################
dots_dir = "polka"
git_repos = [UserGitRepo(target_dir=git_dir, repos=[docs, "noah", dots_dir])]
dirs_to_link = ["config/systemd/user", "local/bin"]
ind_dirs = [
    ((f"{git_dir}/{docs}/fonts"), (".local/share/fonts")),
    ((f"{git_dir}/{docs}/task"), (".config/task")),
    ((f"{git_dir}/{docs}/zsh"), (".config/zsh")),
]
###########################################################
# ICONS
###########################################################
dirs_icons = [
    (f"{desk}/{games}", "folder-games"),
    (f"{desk}/{enc_dir}", "folder-locked"),
    (git_dir, "folder-github"),
    (f"{git_dir}/noah", "folder-root"),
    (f"{git_dir}/{docs}", "folder-bookmark"),
    (f"{git_dir}/{dots_dir}", "folder-html"),
]
###########################################################
# YAZI
###########################################################
yazi_plugins = [
    "yazi-rs/plugins:jump-to-char",
    "uhs-robert/sshfs",
    "boydaihungst/gvfs",
    "uhs-robert/recycle-bin",
    "h-hg/yamb",
]
