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
groups = ["adm", "games", "realtime", "storage"]
git_name = "acctux"
dots_git = "polka"
###########################################################
# FOLDERS TO COPY FROM SCRIPT DIR TO /mnt
###########################################################
script_pwd_to_cp = ["etc", "usr"]
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
noextract_lines = [
    "NoExtract = etc/xdg/autostart/firewall-applet.desktop",
    "NoExtract = usr/share/icons/capitaine-cursors/*",
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
    "bluez-utils",  # for loggy
    "brightnessctl",
    "dosfstools",
    "exfatprogs",
    "ntfs-3g",
    "realtime-privileges",
    "smartmontools",
    "tlp",
    "udisks2-btrfs",
    "usb_modeswitch",
]
base_pkgs = [
    "base-devel",
    "logrotate",
    "ly",
    "pkgfile",
    "plymouth",
    "rebuild-detector",
    "xdg-user-dirs",
]
cli_pkgs = [
    "bat-extras",
    "bluetui",
    "btop",
    "rocm-smi-lib",  # btop dependency for amd gpu
    "eza",
    "fd",
    "fzf",
    "git-delta",
    "github-cli",
    "kitty",
    "lazygit",
    "less",
    "man-pages",
    "mcfly",
    "nvtop",
    "powertop",
    "ripgrep-all",
    "sd",
    "starship",
    "taskwarrior-tui",
    "trash-cli",
    "ugrep",
    "yazi",
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
    "cliphist",
    "featherpad",
    "file-roller",
    "gocryptfs",
    "khal",
    "partitionmanager",
    "qalculate-qt",
    "qt5ct",
    "qt6ct",
    "qjournalctl",
    "unrar",  # File roller
    "wl-clipboard",
    "wl-clip-persist",
    "zbar",  # qr codes
]
android_pkgs = [
    "kdeconnect",
    "gvfs-mtp",
    "sshfs",
    "scrcpy",
]
network_pkgs = [
    "bind",
    "deluge-gtk",
    "firewalld",
    "impala",
    "openresolv",
    "profile-sync-daemon",
    "protonmail-bridge",
    "wireguard-tools",
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
    "yt-dlp",
]
hyprland_pkgs = [
    "capitaine-cursors",
    "fuzzel",
    "gnome-keyring",
    "gsimplecal",
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
    "swww",
    "uwsm",
    "waybar",
    "xdg-desktop-portal-gnome",
    "xdg-desktop-portal-hyprland",
]
office_pkgs = [
    "gnucash",
    "libreoffice-fresh",
    "coin-or-mp",  # LibreOffice Calc Solver
]
coding_pkgs = [
    "inotify-tools",  # nvim
    "npm",
    "neovim-lspconfig",
    "rust",
    "uv",
    #### Language Servers
    "bash-language-server",
    "lua-language-server",
    "rust-analyzer",
    "tailwindcss-language-server",
    "tombi",
    "ty",
    "vscode-json-languageserver",
    "yaml-language-server",
    #### Formatters
    "prettier",
    "ruff",
    "shfmt",
    "stylua",
    ## Tree sitter
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
###########################################################
# CHAOTIC PKGS
###########################################################
chaotic_pkgs = [
    "ayugram-desktop-git",
    "qt6-imageformats",  # AyuGram missing dependency
    "betterbird-bin",
    "dxvk-mingw-git",
    "firedragon",
    "logiops",
    "nchat-git",
    "neovim-symlinks",
    "ocrmypdf",
    "octopi",
    "paru",
    "proton-ge-custom-bin",
    "rpcs3-git",
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
    "tlp",
    "btrfs-scrub@-.timer",
    "btrfs-scrub@home.timer",
    "fstrim.timer",
    "logrotate.timer",
    "man-db.timer",
    "paccache.timer",
    "reflector.timer",
]
custom_services = ["loggy", "wireguard-list"]
disable_svcs = ["getty@tty1", "systemd-networkd-wait-online"]
###########################################################
# USER SERVICES
###########################################################
usr_srv_default = UserSrv(
    source="/usr/lib/systemd/user",
    target="default",
    services=["pipewire-pulse.service", "psd.service"],
)
usr_srv_sockets = UserSrv(
    source="/usr/lib/systemd/user",
    target="sockets",
    services=[
        "pipewire-pulse.socket",
        "gnome-keyring-daemon.socket",
        "gcr-ssh-agent.socket",
        "mpd.socket",
    ],
)
usr_srv_graphical = UserSrv(
    source="/usr/lib/systemd/user",
    target="graphical-session",
    services=["hypridle.service", "swaync.service", "waybar.service"],
)
###########################################################
# HIDE APPS
###########################################################
hide_apps = [
    "avahi-discover",
    "bssh",
    "btop",
    "bvnc",
    "jshell-java-openjdk",
    "jconsole-java-openjdk",
    "khal",
    "libreoffice-base",
    "libreoffice-draw",
    "libreoffice-math",
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
    "uuctl",
    "xgps",
    "xgpsspeed",
]
