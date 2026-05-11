from archinstall.lib.installer import Installer
from archinstall.lib.models import User
from typing import override
from archinstall.default_profiles.profile import (
    CustomSetting,
    DisplayServerType,
    GreeterType,
    Profile,
    ProfileType,
)


class NoahProfile(Profile):
    def __init__(self) -> None:
        super().__init__(
            "Hyprland",
            ProfileType.Custom,
            support_gfx_driver=True,
            display_server=DisplayServerType.Wayland,
        )

        self.custom_settings = {CustomSetting.SeatAccess: None}

    @property
    @override
    def packages(self) -> list[str]:
        return [
            "ananicy-cpp",
            "apparmor",
            "bluetui",
            "bluez-utils",  # for loggy
            "brightnessctl",
            "btop",
            "cliphist",
            "rocm-smi-lib",  # btop dependency for amd gpu
            "dmidecode",
            "dosfstools",
            "exfatprogs",
            "kanshi",
            "kitty",
            "less",
            "mcfly",
            "ntfs-3g",
            "smartmontools",
            "udisks2-btrfs",
            "usb_modeswitch",
            "powertop",
            "gnome-logs",
            "systemctl-tui",
            "base-devel",
            "logrotate",
            "plymouth",
            "rebuild-detector",
            "reflector",
            "xdg-user-dirs",
            "zsh-autocomplete",
            "zsh-completions",
            "zsh-syntax-highlighting",
            "starship",
            "trash-cli",
            "pkgfile",
            # Network
            "bind",
            "impala",
            "iw",
            "openresolv",
            "profile-sync-daemon",
            "protonmail-bridge-core",
            "wireguard-tools",
            "networkmanager",
            # media
            "cava",
            "imv",
            "mpd",
            "mpd-mpris",
            "mpv-mpris",
            "pavucontrol",
            "playerctl",
            "rmpc",
            # Hypr
            "capitaine-cursors",
            "fuzzel",
            "gnome-keyring",
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
            "awww",
            "uwsm",
            "waybar",
            "xdg-desktop-portal-gnome",
            "xdg-desktop-portal-hyprland",
            # Python
            "python-dbus-fast",  # loggy
            "python-gnupg",  # noah
            "python-imaplib2",  # emailcheck
            "python-pandas",  # weather
            "python-pydantic",  # noah
            "python-pyperclip",  # noah
            "python-systemd",  # loggy
            "python-wand",  # wallpaper script
            "otf-firamono-nerd",
            "inotify-tools",  # nvim
            "npm",
            "neovim-lspconfig",
            "uv",
            "qt5ct",
            "qt6ct",
            "wl-clipboard",
            "wl-clip-persist",
            "yazi",
            "zbar",  # qr codes
            "qrencode",  # qr codes
            "git-delta",
            "taskwarrior-tui",
            "man-pages",
            "rofimoji",
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
            "bat-extras",
            "eza",
            "fd",
            "fzf",
            "github-cli",
            "lazygit",
            "ripgrep-all",
            "sd",
            "file-roller",
            "unrar",  # File roller
            "gocryptfs",
            "zathura-pdf-mupdf",
            "zoxide",
        ]

    @property
    @override
    def default_greeter_type(self) -> GreeterType:
        return GreeterType.Sddm

    @property
    @override
    def services(self) -> list[str]:
        if pref := self.custom_settings.get(CustomSetting.SeatAccess, None):
            return [pref]
        return []

    @override
    def post_install(self, install_session: Installer) -> None:
        install_session.arch_chroot(
            "mariadb-install-db --user=mysql --basedir=/usr --datadir=/var/lib/mysql"
        )

    @override
    def provision(self, install_session: Installer, users: list[User]) -> None:
        print("")
