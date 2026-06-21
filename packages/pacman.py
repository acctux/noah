hardware: list[str] = [
    "ananicy-cpp",
    "bees",
    "bluetui",
    "bluez-utils",  # for loggy
    "bolt",
    "brightnessctl",
    "dmidecode",
    "dosfstools",
    "exfatprogs",
    "keyd",
    "ntfs-3g",
    "smartmontools",
    "udisks2-btrfs",
    "usb_modeswitch",
]
network: list[str] = [
    "aria2",
    "bandwhich",
    "bind",
    "impala",
    "iw",
    "openresolv",
    "profile-sync-daemon",
    "wireguard-tools",
    "networkmanager",
]
media: list[str] = [
    "ardour",
    "blender",
    "cava",
    "gimp",
    "guvcview",
    "handbrake-cli",
    "imv",
    "mpd",
    "mpd-mpris",
    "mpv-mpris",
    "obs-studio",
    "playerctl",
    "realtime-privileges",
    "rmpc",
    "songrec",
    "wiremix",
    "yt-dlp",  # for mpv youtube playback
]
monitoring: list[str] = [
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
    # General
    "git-zsh-completion",
    "github-cli",
    "git-delta",
    "inotify-tools",  # nvim
    "lazygit",
    "npm",
    "neovim-lspconfig",
    "uv",
    "rust",
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
    "stylua",
    "yamlfmt",
    # Lint
    "biome",
    "luacheck",
    "shellcheck",
    "yamllint",
    # Tree sitter
    "tree-sitter-bash",
    "tree-sitter-cli",
    "tree-sitter-python",
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
    "shikane",
    "kvantum",
    "kvantum-qt5",
    "polkit-gnome",
    "qt5-wayland",
    "qt6-wayland",
    "qt5ct",
    "qt6ct",
    "satty",
    "snixembed",
    "swappy",
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
    "archinstall",  # noah
    "python-matplotlib",
    "python-tomlkit",  # tuned
    "python-dbus-fast",  # loggy
    "python-gnupg",  # noah
    "python-pandas",  # weather
    "python-pydantic",  # noah
    "python-pyperclip",  # noah
    "python-systemd",  # loggy
    "python-wand",  # wallpaper script
    "qrencode",  # qr codes
    "zbar",  # qr codes
]
base: list[str] = [
    "base-devel",
    "bat-extras",
    "capitaine-cursors",
    "deluge-gtk",
    "dust",
    "eza",
    "ouch",
    "fzf",
    "gocryptfs",
    "keepassxc",
    "khal",
    "kitty",
    "less",
    "man-pages",
    "mcfly",
    "otf-firamono-nerd",
    "partitionmanager",
    "pipe-rename",
    "rebuild-detector",
    "reflector",
    "ripgrep-all",
    "seahorse",
    "starship",
    "taskwarrior-tui",
    "translate-shell",
    "trash-cli",
    "zsh-autocomplete",
    "zsh-completions",
    "zsh-syntax-highlighting",
    "yazi",
    "fd",
    "jq",
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
    "csvkit",
    "csvlens",
    "elinks",
    "isync",
    "khard",
    "ledger",
    "libreoffice-fresh",
    "msmtp",
    "neomutt",
    "notmuch",
    "pdfgrep",
    "protonmail-bridge-core",
    "qalculate-qt",
    "sagemath",
    "timew",
    "urlscan",
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
basic_server: list[str] = [
    "dbeaver",
    "jdk-openjdk",
    "mariadb",
    "python-pymysql",
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
earth: list[str] = [
    "python-gpxpy",
    "python-piexif",
    "qgis",
    "stellarium",
]
random: list[str] = [
    "ugrep",
    "coin-or-mp",  # LibreOffice Calc Solver
    "easyeffects",
    "fwupd",
    "inkscape",
    "mtpfs",
    "pastel",
    "performous",
    "radicale",
    "showmethekey",
]
emulators: list[str] = [
    "desmume",
    "dolphin-emu",
    "plastic",
    "mupen64plus",
    "ppsspp",
    "snes9x",
]
server: list[str] = [
    "termscp",
    "apache",
    "php-apcu",
    "php-gd",
    "php-imagick",
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
    # "nextcloud",
    # "jellyfin-server",
    # "seerr",
    # "radarr",
    # "sonarr",
]
