from utils import UserSrv
from pathlib import Path

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
        target="default",
        services=["pipewire-pulse.service"],
        source_dir=Path("/usr/lib/systemd/user"),
    ),
    UserSrv(
        target="sockets",
        services=["pipewire-pulse.socket"],
        source_dir=Path("/usr/lib/systemd/user"),
    ),
]
###########################################################
# PACMAN CONF
###########################################################
noextract_lines = [
    "NoExtract = etc/xdg/autostart/firewall-applet.desktop",
    "NoExtract = usr/share/icons/capitaine-cursors/*",
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
pass_manager = "pass.txt"
my_pass = "pass.py"
wireguard_dir = "wireguard"
usb_cp_files = [ssh_key, gpg_key, pass_manager, my_pass]
pkgs = [
    ############-Amd-############
    "mesa",
    "xf86-video-amdgpu",
    "xf86-video-ati",
    "vulkan-radeon",
    ##########-Nvidia-##########
    "lib32-nvidia-utils",
    "libva-nvidia-driver",
    "libva-utils",
    "libxnvctrl",
    "nvidia-open",
    "nvidia-prime",
    "opencl-nvidia",
    #########-Pipewire-#########
    "pipewire",
    "pipewire-alsa",
    "pipewire-jack",
    "pipewire-pulse",
    "gst-plugin-pipewire",
    "libpulse",
    "wireplumber",
    #########-Hardware-#########
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
    ###########-Basic Sys-###########
    "base-devel",
    "logrotate",
    "ly",
    "pkgfile",
    "plymouth",
    "rebuild-detector",
    "xdg-user-dirs",
    #########-Android-#########
    "kdeconnect",
    "gvfs-mtp",  # Nautilus/Android
    "sshfs",
    "scrcpy",
    #########-Network-#########
    "bind",
    "deluge-gtk",
    "firewalld",
    "impala",
    "openresolv",
    "profile-sync-daemon",
    "protonmail-bridge",
    "wireguard-tools",
    ########-Lang/Fonts-########
    "hunspell-en_us",
    "hyphen-en",
    "noto-fonts-emoji",
    "otf-firamono-nerd",
    "rofimoji",
    "tesseract-data-eng",
    "ttf-liberation",
    ########-Multimedia-########
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
    ###########-CLI-############
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
    #########-Hyprland-#########
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
    ###########-Office-###########
    "gnucash",
    "libreoffice-fresh",
    "coin-or-mp",  # LibreOffice Calc Solver
    ###########-Basic User-###########
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
    ###########-Coding-###########
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
    ##########-SQL Server-##########
    "dbeaver",
    "jdk-openjdk",
    "mariadb",
    "python-pymysql",
    ###########-Python-###########
    "python-dbus-fast",  # loggy
    "python-gnupg",  # noah
    "python-imaplib2",  # emailcheck
    "python-pandas",  # weather
    "python-pydantic",  # noah
    "python-pyperclip",  # noah
    "python-systemd",  # loggy
    "python-wand",  # wallpaper script
    ###########-Gaming-###########
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
    ########-CHAOTIC PKGS-########
    "anki",
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
aur_pkgs = ["wvkbd-deskintl"]
