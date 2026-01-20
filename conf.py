from pathlib import Path
from archinstall.lib.args import LocaleConfiguration
from utils import UserSrv

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
#############-GROUPS-#############
groups = ["audio", "games", "gamemode", "log", "realtime", "storage", "video"]
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
    "android-file-transfer",
    "bluetui",
    "bluez-utils",  # for loggy
    "brightnessctl",
    "btop",
    "dosfstools",
    "exfatprogs",
    "ntfs-3g",
    "nvtop",
    "partitionmanager",
    "powertop",
    "realtime-privileges",
    "rocm-smi-lib",  # btop dependency for amd gpu
    "smartmontools",
    "tlp",
    "udisks2-btrfs",
    "usb_modeswitch",
    #########-Network-#########
    "bind",
    "deluge-gtk",
    "firewalld",
    "impala",
    "kdeconnect",
    "openresolv",
    "profile-sync-daemon",
    "protonmail-bridge",
    "sshfs",
    "wireguard-tools",
    "wireless-regdb",
    ########-Lang/Fonts-########
    "font-manager",
    "hunspell-en_us",
    "hyphen-en",
    "noto-fonts-emoji",
    "otf-firamono-nerd",
    "rofimoji",
    "tesseract-data-eng",
    "ttf-jetbrains-mono",
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
    "alacritty",
    "aria2",
    "bash-completion",
    "bat-extras",
    "eza",
    "fd",
    "github-cli",
    "lazygit",
    "less",
    "man-pages",
    "mcfly",
    "ouch",
    "rebuild-detector",
    "ripgrep-all",
    "sd",
    "starship",
    "taskwarrior-tui",
    "tmuxp",
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
    "nwg-clipman",
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
    ###########-Basic-###########
    "baobab",
    "bustle",
    "featherpad",
    "gocryptfs",
    "logrotate",
    "ly",
    "nemo-audio-tab",
    "plymouth",
    "qalculate-qt",
    "qt6ct",
    "qjournalctl",
    "wl-clipboard",
    "wl-clip-persist",
    "xdg-user-dirs",
    ###########-Office-###########
    "coin-or-mp",  # For LibreOffice Calc Solver
    "gnucash",
    "khal",
    "libreoffice-fresh",
    "thunderbird-i18n-en-us",
    "thunderbird-dark-reader",
    "thunderbird-ublock-origin",
    ###########-Coding-###########
    "luarocks",
    "lua-sec",
    "npm",
    "neovim-lspconfig",
    "rust",
    "uv",
    # Language Servers
    "bash-language-server",
    "clang",
    "lua-language-server",
    "pyright",
    "rust-analyzer",
    "systemd-language-server",
    "tailwindcss-language-server",
    "vscode-json-languageserver",
    "yaml-language-server",
    # Linters
    "ruff",
    # Tree sitter
    "tree-sitter-bash",
    "tree-sitter-cli",
    "tree-sitter-javascript",
    "tree-sitter-python",
    "tree-sitter-rust",
    ###########-Python-###########
    "python-dbus-fast",  # loggy
    "python-imaplib2",  # emailcheck
    "python-mpd2",
    "python-mysqlclient",
    "python-pandas",
    "python-pygit2",
    "python-pyperclip",
    "python-systemd",  # loggy
    "python-wand",  # wallpaper script
    #########-SQL Server-##########
    "dbeaver",
    "jdk-openjdk",
    "mariadb",
    ###########-Gaming-###########
    "gamemode",
    "gnome-chess",
    "gnuchess",
    "lib32-gamemode",
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
#############-SERVICES-##############
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
    ###########-Custom-############
    "loggy",
    "wireguard-list",
]
###########-Disable############
disable_svcs = [
    "getty@tty1",
    "systemd-networkd-wait-online",
]
###########-USER SERVICES-############
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
###########-FOLDERS/GITS-############
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
git_repos = [
    (git_dir, "Docs"),
    (git_dir, "Noah"),
    (HOME, "Polka"),
]
dir_icons = [
    [desk_dir / "Games", "folder-games.svg"],
    [git_dir, "folder-github.svg"],
    [git_dir / "Noah", "folder-root.svg"],
    [docs_dir, "folder-bookmark.svg"],
    [dot_dir, "folder-html.svg"],
    [enc_dir, "folder-locked.svg"],
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
