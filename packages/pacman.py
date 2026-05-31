hardware: list[str] = [
    "ananicy-cpp",
    "bluetui",
    "bluez-utils",  # for loggy
    "brightnessctl",
    "btrfs-assistant",
    "dmidecode",
    "dosfstools",
    "exfatprogs",
    "hwdetect",
    "ntfs-3g",
    "smartmontools",
    "udisks2-btrfs",
    "usb_modeswitch",
]
network: list[str] = [
    "bind",
    "impala",
    "iw",
    "openresolv",
    "profile-sync-daemon",
    "wireguard-tools",
    "networkmanager",
]
media: list[str] = [
    "cava",
    "imv",
    "mpd",
    "mpd-mpris",
    "mpv-mpris",
    "obs-studio",
    "pavucontrol",
    "playerctl",
    "realtime-privileges",
    "rmpc",
    "guvcview",
    "yt-dlp",  # for mpv youtube playback
    "gimp",
]
monitoring: list[str] = [
    "bandwhich",
    "btop",
    "rocm-smi-lib",  # btop dependency for amd gpu
    "gnome-logs",
    "jolt",
    "nvtop",
    "logrotate",
    "powertop",
    "systemctl-tui",
]
coding: list[str] = [
    "ugrep",
    "inotify-tools",  # nvim
    "npm",
    "neovim-lspconfig",
    "uv",
    "github-cli",
    "git-delta",
    "lazygit",
    # coding
    # Language Servers
    "bash-language-server",
    "lua-language-server",
    "rust-analyzer",
    "tombi",
    "ty",
    "vscode-css-languageserver",
    "vscode-json-languageserver",
    "yaml-language-server",
    # Formatters
    "ruff",
    "shfmt",
    # Lint
    "shellcheck",
    "biome",
    "luacheck",
    "yamllint",
    # Tree sitter
    "tree-sitter-bash",
    "tree-sitter-cli",
    "tree-sitter-python",
    "rust",
    "stylua",
    "yamlfmt",
    "tree-sitter-rust",
]
hyprland: list[str] = [
    "cliphist",
    "fuzzel",
    "gnome-keyring",
    "hypridle",
    "hyprland",
    "hyprlock",
    "hyprpicker",
    "hyprshot",
    "hyprsunset",
    "kanshi",
    "kvantum",
    "kvantum-qt5",
    "polkit-gnome",
    "qt5-wayland",
    "qt6-wayland",
    "qt5ct",
    "qt6ct",
    "satty",
    "snixembed",
    "swaync",
    "swayosd",
    "awww",
    "uwsm",
    "waybar",
    "xdg-desktop-portal-gnome",
    "xdg-desktop-portal-hyprland",
    "xdg-user-dirs",
    "wl-clip-persist",
]
personal: list[str] = [
    "acpi",  # auto hibernate
    "archinstall",  # noah
    "python-dbus-fast",  # loggy
    "python-gnupg",  # noah
    "python-imaplib2",  # emailcheck
    "python-pandas",  # weather
    "python-pydantic",  # noah
    "python-pyperclip",  # noah
    "python-systemd",  # loggy
    "python-wand",  # wallpaper script
    "qrencode",  # qr codes
    "zbar",  # qr codes
]
base: list[str] = [
    "authenticator",
    "base-devel",
    "bat-extras",
    "capitaine-cursors",
    "deluge-gtk",
    "dust",
    "eza",
    "fd",
    "ouch",
    "fzf",
    "gocryptfs",
    "khal",
    "kitty",
    "less",
    "man-pages",
    "mcfly",
    "otf-firamono-nerd",
    "partitionmanager",
    "rebuild-detector",
    "reflector",
    "ripgrep-all",
    "sd",
    "seahorse",
    "starship",
    "taskwarrior-tui",
    "trash-cli",
    "zsh-autocomplete",
    "zsh-completions",
    "zsh-syntax-highlighting",
    "yazi",
    "zoxide",
]
language: list[str] = [
    "hunspell-en_us",
    "hyphen-en",
    "tesseract-data-eng",
    "tesseract-data-rus",
    "tesseract-data-ukr",
]
gaming: list[str] = [
    "gnome-chess",
    "gnuchess",
    "lib32-mangohud",
    "lutris",
    "mangohud",
    "mgba-qt",
    "steam",
    "umu-launcher",
    "wine-mono",
    "wine-staging",
    "winetricks",
]
office: list[str] = [
    "anki",
    "gnucash",
    "evince",
    "libreoffice-fresh",
    "neomutt",
    "protonmail-bridge-core",
    "coin-or-mp",  # LibreOffice Calc Solver
    "qalculate-qt",
    "zathura-pdf-mupdf",
]
android: list[str] = [
    "kdeconnect",
    "gvfs-mtp",
    "sshfs",
    "scrcpy",
    "android-udev",
]
ios: list[str] = [
    "usbmuxd",
    "ifuse",
    "gvfs-afc",
    "gvfs-gphoto2",
]
printer: list[str] = [
    "cups",
    "cups-browsed",
    "cups-filters",
    "cups-pdf",
    "foomatic-db",
    "foomatic-db-engine",
    "foomatic-db-gutenprint-ppds",
    "foomatic-db-nonfree",
    "foomatic-db-nonfree-ppds",
    "foomatic-db-ppds",
    "ghostscript",
    "gsfonts",
    "gutenprint",
    "simple-scan",
    "splix",
    "system-config-printer",
]
server: list[str] = [
    "termscp",
    "gvfs-nfs",
    "samba",
    "duplicity",
    "grafana",
    "netdata",
    "caddy",
    "traefik",
    "fail2ban",
    "docker",
    "tailscale",
    "dbeaver",
    "jdk-openjdk",
    "mariadb",
    "python-pymysql",
    # "nextcloud",
    # "jellyfin-server",
    # "seerr",
    # "radarr",
    # "sonarr",
]
