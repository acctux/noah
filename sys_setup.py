#!/usr/bin/env python3
from archinstall.lib.models.bootloader import BootloaderConfiguration
from archinstall.lib.models.application import (
    ZramConfiguration,
    PowerManagementConfiguration,
    PowerManagement,
    Firewall,
    FirewallConfiguration,
    FontsConfiguration,
    FontPackage,
)
from archinstall.lib.applications.application_handler import ApplicationHandler
from archinstall.lib.hardware import _sys_info, GfxDriver
from archinstall.default_profiles.profile import GreeterType
from archinstall.lib.args import (
    ArchConfig,
    ArchConfigHandler,
    AuthenticationConfiguration,
)
from archinstall.lib.configuration import ConfigurationOutput
from archinstall.lib.disk.filesystem import FilesystemHandler
from archinstall.lib.disk.utils import disk_layouts
from archinstall.lib.general.general_menu import (
    PostInstallationAction,
    select_post_installation,
)
from archinstall.lib.global_menu import GlobalMenu
from archinstall.lib.installer import Installer
from archinstall.lib.menu.util import delayed_warning
from archinstall.lib.models import (
    Bootloader,
    Audio,
    AudioConfiguration,
    ApplicationConfiguration,
    BluetoothConfiguration,
    PrintServiceConfiguration,
    LocaleConfiguration,
    ProfileConfiguration,
    NetworkConfiguration,
    NicType,
)
from archinstall.lib.models.device import DiskLayoutType, EncryptionType
from archinstall.lib.models.users import User
from archinstall.lib.output import debug, error, info
from archinstall.tui.ui.components import tui
from archinstall.lib.models.users import Password
from archinstall.lib.network.network_handler import install_network_config
from pydantic import BaseModel
from pathlib import Path
import sys
import time
import subprocess
import json
import re
import shutil
from dataclasses import dataclass, field
from textwrap import dedent
from utils import log, run_dmc, yes_no
from archinstall.lib.profile.profiles_handler import profile_handler


class UsrSrv(BaseModel):
    source: str
    target: str
    services: list[str]


arch_config = ArchConfig(
    app_config=ApplicationConfiguration(
        bluetooth_config=BluetoothConfiguration(enabled=True),
        audio_config=AudioConfiguration(audio=Audio.PIPEWIRE),
        power_management_config=PowerManagementConfiguration(PowerManagement.TUNED),
        print_service_config=PrintServiceConfiguration(enabled=True),
        firewall_config=FirewallConfiguration(Firewall.FWD),
        fonts_config=FontsConfiguration([FontPackage.LIBERATION, FontPackage.EMOJI]),
    ),
    locale_config=LocaleConfiguration(
        kb_layout="us", sys_lang="en_US", sys_enc="UTF-8"
    ),
    profile_config=ProfileConfiguration(
        profile=None, gfx_driver=GfxDriver.NvidiaOpenKernel, greeter=GreeterType.Ly
    ),
    network_config=NetworkConfiguration(type=NicType.ISO),
    bootloader_config=BootloaderConfiguration(Bootloader.Systemd, False, False),
    hostname="yulia",
    kernels=["linux"],
    ntp=True,
    swap=ZramConfiguration(enabled=True),
    timezone="US/Eastern",
    services=[
        "ananicy-cpp",
        "iwd",
        "named",
        "swayosd-libinput-backend",
        "systemd-networkd",
        "systemd-oomd",
        "btrfs-scrub@-.timer",
        "btrfs-scrub@home.timer",
        "fstrim.timer",
        "logrotate.timer",
        "man-db.timer",
        "paccache.timer",
        "reflector.timer",
    ],
)


###########################################################
# ARCHINSTALL CONF
###########################################################
@dataclass
class NoahConfig:
    def populate_usr_srv(self, user_name: str):
        self.usr_srv = (
            UsrSrv(
                source="/usr/lib/systemd/user",
                target="default",
                services=["psd.service"],
            ),
            UsrSrv(
                source="/usr/lib/systemd/user",
                target="sockets",
                services=["gcr-ssh-agent.socket", "mpd.socket"],
            ),
            UsrSrv(
                source="/usr/lib/systemd/user",
                target="graphical-session",
                services=[
                    "cliphist.service",
                    "hypridle.service",
                    "hyprsunset.service",
                    "swaync.service",
                    "waybar.service",
                ],
            ),
            UsrSrv(
                source=f"/home/{user_name}/.config/systemd/user",
                target="graphical-session",
                services=[
                    "ayugram.service",
                    "clip-persist.service",
                    "kdeconnectd.service",
                    "kanshi.service",
                    "playerctld.service",
                    "polkit-gnome.service",
                    "snixembed.service",
                    "swayosd.service",
                    "awww-daemon.service",
                ],
            ),
            UsrSrv(
                source=f"/home/{user_name}/.config/systemd/user",
                target="timers",
                services=[
                    "emailcheck.timer",
                    "task-reminder.timer",
                    "task-schedule.timer",
                    "wall.timer",
                ],
            ),
        )

    username: str = "nick"
    groups: tuple[str, ...] = ("adm", "games", "realtime", "storage", "video")
    dots_repo: str = "polka"
    git_user: str = "acctux"
    usb_key_dir: str = "keys"
    wireguard_dir: str = "wireguard"
    my_pass: str = "pass.py"
    parallel_downloads: int = 10
    multilib: bool = True
    terminal: str = "kitty"
    usb_cp_files: tuple[str, ...] = (
        "id_ed25519",
        "my_sec_gpg.asc",
        "pass.txt",
        my_pass,
    )
    no_extracts: tuple[str, ...] = (
        "etc/xdg/autostart/firewall-applet.desktop",
        "usr/share/icons/capitaine-cursors/*",
    )
    to_cp: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            ".ssh": ("id_ed25519", "pass.txt"),
            ".gnupg": ("my_sec_gpg.asc",),
        }
    )
    firefox_browser: str = "floorp"
    firefox_extensions: tuple[str, ...] = (
        "return-youtube-dislikes",
        "leechblock-ng",
        "proton-pass",
        "firefox-color",
        "darkreader",
        "flagfox",
        "ublock-origin",
    )
    mkinit_hooks: tuple[str, ...] = (
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
    )
    reflector_options: tuple[str, ...] = (
        "--country US",
        "--protocol https",
        "--latest 15",
        "--sort rate",
        "--number 3",
        "--save /etc/pacman.d/mirrorlist",
    )
    pkgs: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "base": (
                # HARDWARE
                "ananicy-cpp",
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
            ),
            "language": (
                "hunspell-en_us",
                "hyphen-en",
                "tesseract-data-eng",
            ),
            "chaotic_repo": (
                "cachyos-ananicy-rules-git",
                "floorp",
                "octopi",
                "paru",
                "systemd-oomd-defaults",
                "ocrmypdf",
            ),
            "extra": (
                "rust",
                "stylua",
                "yamlfmt",
                "tree-sitter-rust",
                "deluge-gtk",
                "nvtop",
                "jolt",
                "ugrep",
                "zoxide",
                "anki",
                "authenticator",
                "baobab",
                "bustle",
                "partitionmanager",
                "qalculate-qt",
                "evince",
                "gimp",
                "guvcview",
                "yt-dlp",  # for mpv youtube playback
                "libreoffice-fresh",
                "coin-or-mp",  # LibreOffice Calc Solver
                "gnucash",
                "kdeconnect",
                "gvfs-mtp",
                "sshfs",
                "scrcpy",
                "gvfs-afc",
                "gvfs-gphoto2",
                "usbmuxd",
                "dbeaver",
                "jdk-openjdk",
                "mariadb",
                "python-pymysql",
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
            ),
            "extra_chaos": (
                "logiops",
                "neovim-symlinks",
                "ayugram-desktop-git",
                "qt6-imageformats",  # AyuGram missing dependency
                "betterbird-bin",
                "nchat-git",
                "proton-cachyos-slr",
                "rpcs3-git",
                "eden-git",
            ),
        }
    )
    aur_pkgs: tuple[str, ...] = ("wvkbd-deskintl",)
    custom_services: tuple[str, ...] = (
        "loggy",
        "sysinfo",
    )
    disable_svcs: tuple[str, ...] = (
        "systemd-resolved",
        "systemd-networkd-wait-online",
    )
    apps_to_hide: tuple[str, ...] = (
        "avahi-discover",
        "bssh",
        "btop",
        "bvnc",
        "jshell-java-openjdk",
        "jconsole-java-openjdk",
        "libreoffice-base",
        "libreoffice-draw",
        "libreoffice-impress",
        "libreoffice-math",
        "khal",
        "kvantummanager",
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
        "tuned-gui",
        "uuctl",
        "xgps",
        "xgpsspeed",
    )
    etc_files_to_write: dict[str, str] = field(
        default_factory=lambda: {
            "etc/tmpfiles.d/mpd.conf": dedent(
                """\
                x /home/*/.cache/mpd 0755 %u %g -
                x /home/*/.cache/mpd/playlists 0755 %u %g -
                """
            ),
            "etc/iwd/main.conf": dedent(
                """\
                [Network]
                NameResolvingService=resolvconf
                """
            ),
            "etc/systemd/system/iwd.service.d/override.conf": dedent(
                """\
                [Service]
                RuntimeDirectory=resolvconf
                ReadWritePaths=/etc/resolv.conf
                """
            ),
            "etc/systemd/system/wg-quick@.service.d/override.conf": dedent(
                """\
                [Unit]
                After=
                Wants=
                """
            ),
            "etc/systemd/network/20-usb-tether.network": dedent(
                """\
                [Match]
                Name=enp*

                [Network]
                DHCP=yes
                IPv6AcceptRA=yes
                """
            ),
            "etc/resolvconf.conf": dedent(
                """\
                resolv_conf=/etc/resolv.conf
                name_servers="::1 127.0.0.1"
                """
            ),
            "etc/nsswitch.conf": dedent(
                """\
                passwd: files systemd
                group: files [SUCCESS=merge] systemd
                shadow: files systemd
                gshadow: files systemd
                publickey: files
                hosts: mymachines mdns_minimal [NOTFOUND=return] resolve [!UNAVAIL=return] files myhostname dns
                networks: files
                protocols: files
                services: files
                ethers: files
                rpc: files
                netgroup: files
                """
            ),
            "etc/firewalld/zones/block.xml": dedent(
                """\
                <?xml version="1.0" encoding="utf-8"?>
                <zone target="%%REJECT%%">
                  <short>Block</short>
                  <description>Unsolicited incoming network packets are rejected. Incoming packets that are related to outgoing network connections are accepted. Outgoing network connections are allowed.</description>
                  <service name="kdeconnect"/>
                  <service name="ssh"/>
                  <service name="wireguard"/>
                  <port port="6881-6889" protocol="tcp"/>
                  <port port="6881-6889" protocol="udp"/>
                  <forward/>
                </zone>
                """
            ),
            "etc/named.conf": dedent(
                """\
                // vim:set ts=4 sw=4 et:
                tls cloudflare {
                    remote-hostname "one.one.one.one";
                };

                options {
                    pid-file "/run/named/named.pid";
                    directory "/var/named";
                    max-cache-size 200m;
                    listen-on { 127.0.0.1; };
                    listen-on-v6 { ::1; };
                    allow-recursion {
                        127.0.0.1;
                        ::1;
                    };
                    forward only;
                    forwarders port 853 tls cloudflare {
                        1.1.1.1; 2606:4700:4700::1111;
                        1.0.0.1; 2606:4700:4700::1001;
                    };
                // if system time is wrong and can't connect
                //    dnssec-validation no;
                };

                zone "localhost" IN {
                    type master;
                    file "localhost.zone";
                };

                zone "0.0.127.in-addr.arpa" IN {
                    type master;
                    file "127.0.0.zone";
                };
                """
            ),
            "etc/xdg/user-dirs.defaults": dedent(
                """\
                DOCUMENTS=Desktop/Documents
                DESKTOP=Desktop
                MUSIC=Desktop/Music
                PICTURES=Desktop/Pictures
                VIDEOS=Desktop/Videos
                DOWNLOAD=Desktop/Downloads
                TEMPLATES=Desktop/Templates
                PUBLICSHARE=Desktop/Public
                """
            ),
            "etc/conf.d/pacman-contrib": 'PACCACHE_ARGS="-k 2"\n',
            "boot/loader/loader.conf": dedent(
                """\
                default @saved
                timeout 1
                editor no
                """
            ),
            "etc/pacman.d/hooks/95-systemd-boot.hook": dedent(
                """\
                [Trigger]
                Type = Package
                Operation = Upgrade
                Target = systemd

                [Action]
                Description = Gracefully upgrading systemd-boot...
                When = PostTransaction
                Exec = /usr/bin/systemctl restart systemd-boot-update.service
                """
            ),
            "etc/systemd/journald.conf.d/00-journal-size.conf": dedent(
                """\
                [Journal]
                SystemMaxUse=50M
                """
            ),
            "etc/systemd/zram-generator.conf": dedent(
                """\
                [zram0]
                zram-size = min(ram / 3, 8192)
                compression-algorithm = zstd
                """
            ),
            "etc/sysctl.d/99-zram.conf": dedent(
                """\
                vm.swappiness = 180
                vm.watermark_boost_factor = 0
                vm.watermark_scale_factor = 125
                vm.page-cluster = 0
                """
            ),
            "etc/fuse.conf": dedent(
                """\
                user_allow_other
                """
            ),
            "etc/sysctl.d/99-watchdog.conf": dedent(
                """\
                kernel.nmi_watchdog = 0
                """
            ),
            "etc/sysctl.d/99-steam.conf": dedent(
                """\
                vm.max_map_count = 2147483642
                """
            ),
            "etc/sysctl.d/99-net.conf": dedent(
                """\
                net.core.rmem_max = 8388608
                net.core.wmem_max = 8388608
                """
            ),
            "etc/udisks2/mount_options.conf": dedent(
                """\
                [defaults]
                defaults=noatime
                """
            ),
            "etc/udev/rules.d/99-thunderbolt.rules": dedent(
                """\
                ACTION=="add", SUBSYSTEM=="thunderbolt", ATTR{authorized}=="0", ATTR{authorized}="1"
                """
            ),
            "etc/polkit-1/rules.d/49-rules.rules": dedent(
                """\
                polkit.addRule(function(action, subject) {
                    if (
                        subject.isInGroup("storage") &&
                        (
                            action.id == "org.freedesktop.udisks2.filesystem-mount" ||
                            action.id == "org.freedesktop.udisks2.filesystem-mount-system" ||
                            action.id == "org.freedesktop.udisks2.encrypted-unlock" ||
                            action.id == "org.freedesktop.udisks2.encrypted-unlock-system"
                        )
                    ) {
                        return polkit.Result.YES;
                    }
                    if (
                        action.id === "org.kde.kpmcore.externalcommand.init" &&
                        subject.isInGroup("wheel")
                    ) {
                        return polkit.Result.YES;
                    }
                });
                """
            ),
            "etc/logid.cfg": dedent(
                """\
                // Top=0xc4  Gesture=0xc3 Back=0x53 Forward=0x56
                devices: ({
                    name: "MX Master 3S";
                    smartshift: {
                        on: true;
                        threshold: 15;
                    };
                    hiresscroll: {
                        hires: true;
                        invert: false;
                        target: false;
                    };
                    dpi: 5200;
                    buttons: (
                        {
                            cid: 0x56;
                            action: {
                                type: "Gestures";
                                gestures: (
                                    {
                                        direction: "None";
                                        mode: "OnRelease";
                                        action: {
                                            type: "Keypress";
                                            keys: [ "KEY_LEFTCTRL", "KEY_V" ];
                                        }
                                    },
                                    {
                                        direction: "Up";
                                        mode: "OnRelease";
                                        action: {
                                            type: "Keypress";
                                            keys: [ "KEY_LEFTMETA", "KEY_SPACE" ];
                                        }
                                    },
                                    {
                                        direction: "Down";
                                        mode: "OnRelease";
                                        action: {
                                            type: "Keypress";
                                            keys: [ "KEY_LEFTMETA", "KEY_B" ];
                                        }
                                    },
                                    {
                                        direction: "Right";
                                        mode: "OnRelease";
                                        action: {
                                            type: "Keypress";
                                            keys: [ "KEY_LEFTMETA", "KEY_T" ];
                                        }
                                    },
                                    {
                                        direction: "Left";
                                        mode: "OnRelease";
                                        action: {
                                            type: "Keypress";
                                            keys: [ "KEY_LEFTMETA", "KEY_E" ];
                                        }
                                    }
                                );
                            };
                        },
                        {
                            cid: 0x53;
                            action: {
                                type: "Gestures";
                                gestures: (
                                    {
                                        direction: "None";
                                        mode: "OnRelease";
                                        action: {
                                            type: "Keypress";
                                            keys: [ "KEY_LEFTCTRL", "KEY_C" ];
                                        }
                                    },
                                    {
                                        direction: "Right";
                                        mode: "OnRelease";
                                        action: {
                                            type: "Keypress";
                                            keys: [ "KEY_LEFTMETA", "KEY_G" ];
                                        }
                                    },
                                    {
                                        direction: "Left";
                                        mode: "OnRelease";
                                        action: {
                                            type: "Keypress";
                                            keys: [ "KEY_LEFTMETA", "KEY_D" ];
                                        }
                                    },
                                    {
                                        direction: "Up";
                                        mode: "OnRelease";
                                        action: {
                                            type: "Keypress";
                                            keys: [ "KEY_LEFTMETA", "KEY_F" ];
                                        }
                                    },
                                    {
                                        direction: "Down";
                                        mode: "OnRelease";
                                        action: {
                                            type: "Keypress";
                                            keys: [ "KEY_ESC" ];
                                        }
                                    }
                                );
                            };
                        },
                        {
                            cid: 0xc3;
                            action: {
                                type: "Gestures";
                                gestures: (
                                    {
                                        direction: "None";
                                        mode: "OnRelease";
                                        action: {
                                            type: "Keypress";
                                            keys: [ "KEY_LEFTMETA", "KEY_R" ];
                                        }
                                    },
                                    {
                                        direction: "Right";
                                        mode: "OnRelease";
                                        action: {
                                            type: "Keypress";
                                            keys: [ "KEY_LEFTMETA", "KEY_K" ];
                                        }
                                    },
                                    {
                                        direction: "Left";
                                        mode: "OnRelease";
                                        action: {
                                            type: "Keypress";
                                            keys: [ "KEY_LEFTMETA", "KEY_J" ];
                                        }
                                    },
                                    {
                                        direction: "Up";
                                        mode: "OnRelease";
                                        action: {
                                            type: "Keypress";
                                            keys: [ "KEY_LEFTMETA", "KEY_H" ];
                                        }
                                    },
                                    {
                                        direction: "Down";
                                        mode: "OnRelease";
                                        action: {
                                            type: "Keypress";
                                            keys: [ "KEY_LEFTMETA", "KEY_L" ];
                                        }
                                    }
                                );
                            };
                        },
                        {
                            cid: 0xc4;
                            action: {
                                type: "Keypress";
                                keys: [ "KEY_LEFTSHIFT" ];
                            };
                        }
                    );
                });
                """
            ),
            "etc/ly/config.ini": dedent(
                """\
                allow_empty_password = true
                animation = matrix
                animation_timeout_sec = 0
                asterisk = *
                auth_fails = 10
                bg = 0x00101013
                bigclock = none
                blank_box = true
                border_fg = 0x00D3DAE3
                box_title = null
                brightness_down_cmd = /usr/bin/brightnessctl -q s 10%-
                brightness_down_key = F5
                brightness_up_cmd = /usr/bin/brightnessctl -q s +10%
                brightness_up_key = F6
                clear_password = false
                clock = null
                cmatrix_fg = 0x000000FF
                cmatrix_min_codepoint = 0x21
                cmatrix_max_codepoint = 0x7B
                colormix_col1 = 0x0000FF00
                colormix_col2 = 0x000000CC
                colormix_col3 = 0x20000000
                console_dev = /dev/console
                default_input = login
                doom_top_color = 0x00FF0000
                doom_middle_color = 0x00FFFF00
                doom_bottom_color = 0x00FFFFFF
                error_bg = 0x00000000
                error_fg = 0x01FF0000
                fg = 0x00D3DAE3
                hide_borders = false
                hide_key_hints = false
                initial_info_text = null
                input_len = 34
                lang = en
                load = true
                login_cmd = null
                logout_cmd = null
                margin_box_h = 2
                margin_box_v = 1
                min_refresh_delta = 5
                numlock = true
                path = /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
                restart_cmd = /sbin/shutdown -r now
                restart_key = F2
                save = true
                service_name = ly
                session_log = .cache/ly
                setup_cmd = /etc/ly/setup.sh
                shutdown_cmd = /sbin/shutdown -a now
                shutdown_key = F1
                sleep_cmd = null
                sleep_key = F3
                text_in_center = false
                tty = 2
                vi_default_mode = normal
                vi_mode = false
                waylandsessions = /usr/share/wayland-sessions
                x_cmd = /usr/bin/X
                xauth_cmd = /usr/bin/xauth
                xinitrc = ~/.xinitrc
                xsessions = /usr/share/xsessions
                """
            ),
        }
    )


#########################
# UTILS
#########################
def src_pass_file(usb_key_dir: str, pass_file: str) -> str:
    key_path = Path("/root") / usb_key_dir / pass_file
    pw = ""
    if key_path.exists():
        try:
            pw = key_path.read_text().strip()
            log.info(f"{key_path} loaded ")
            return pw
        except Exception as e:
            log.error(f"{e}")
    log.warning(f"{key_path} not found.")
    return pw


def copy_file(src: Path, dest: Path) -> None:
    if not src.is_file():
        log.error(f"{src} does not exist")
        return
    dest = dest / src.name if dest.is_dir() else dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    log.info(f"Copied file: {src} -> {dest}")


def copy_dir(src: Path, dest: Path) -> None:
    if not src.is_dir():
        log.error(f"{src} does not exist")
        return
    shutil.copytree(src, dest, dirs_exist_ok=True, ignore_dangling_symlinks=True)
    log.info(f"Copied directory: {src} -> {dest}")


###################################
# USB Files
###################################
def get_device(min_gb: int = 20, usb_fs_type: str = "ext4") -> str:
    def recurse(devices):
        for dev in devices:
            if (
                dev["type"] == "part"
                and dev.get("fstype") == usb_fs_type
                and dev.get("mountpoint") is None
                and float(dev["size"][:-1]) > min_gb
            ):
                candidates.append(
                    (
                        dev["name"],
                        dev["size"],
                        dev.get("fstype"),
                    )
                )
            if "children" in dev:
                recurse(dev["children"])

    data = json.loads(
        subprocess.check_output(
            ["lsblk", "-J", "-o", "NAME,SIZE,FSTYPE,MOUNTPOINT,TYPE"], text=True
        )
    )
    candidates = []
    recurse(data["blockdevices"])
    while True:
        print(
            f"\033[91m{'No.':<5}\033[0m "
            f"\033[93m{'Name':<10}\033[0m "
            f"\033[94m{'Size':<10}\033[0m "
            f"\033[96m{'FS Type':>10}\033[0m"
        )
        print("-" * 45)
        for i, (name, size, fstype) in enumerate(candidates, 1):
            print(
                f"\033[91m{i:<5}\033[0m "
                f"\033[93m{name:<10}\033[0m "
                f"\033[94m{size:<10}\033[0m "
                f"\033[96m{fstype:>10}\033[0m"
            )
        choice = input(f"\033[92mEnter 1-{len(candidates)}: \033[0m").strip()
        if not choice.isdigit() or not (1 <= int(choice) <= len(candidates)):
            log.error("Out of range.")
            continue
        selected_path = f"/dev/{candidates[int(choice) - 1][0]}"
        break
    return selected_path


def mnt_cp_keys(
    key_dir: str | None = None,
    key_files: list[str] | None = None,
    wireguard_dir: str | None = None,
    usb_mnt: Path = Path("/mnt/usb"),
    home: Path = Path.home(),
) -> None:
    if usb_mnt.is_mount() and yes_no("USB mounted, unmount?"):
        run_dmc(["umount", str(usb_mnt)], check=True)
    missing = []
    if key_dir and key_files:
        missing += [k for k in key_files if not (home / key_dir / k).exists()]
    if wireguard_dir and not (home / wireguard_dir).is_dir():
        missing.append(wireguard_dir)
    if not missing:
        log.info("All required files present.")
        return
    if not yes_no(f"Mount USB to copy {', '.join(missing)}"):
        return
    selected = get_device()
    usb_mnt.mkdir(parents=True, exist_ok=True)
    run_dmc(["mount", "-o", "ro", str(selected), str(usb_mnt)], check=True)
    time.sleep(2)
    if key_dir and key_files:
        (home / key_dir).mkdir(parents=True, exist_ok=True)
        for k in key_files:
            copy_file(usb_mnt / key_dir / k, home / key_dir / k)
    if wireguard_dir:
        copy_dir(usb_mnt / wireguard_dir, home / wireguard_dir)
    time.sleep(1)
    if yes_no("Files copied, unmount?"):
        run_dmc(["umount", str(usb_mnt)], check=True)
        time.sleep(1)


###################################
# PACMAN
###################################
def generate_pacman_conf(
    mnt_point: Path | None,
    no_extracts: list,
    parallel_downloads: int = 10,
    multilib: bool = True,
) -> None:
    no_extract_lines = "\n        ".join(
        [f"NoExtract = {item}" for item in no_extracts]
    )
    pacman_content = dedent(f"""
        [options]
        HoldPkg = pacman glibc
        Architecture = auto
        Color
        ILoveCandy
        ParallelDownloads = {parallel_downloads}
        DownloadUser = alpm
        SigLevel    = Required DatabaseOptional
        LocalFileSigLevel = Optional
        {no_extract_lines}

        [core]
        Include = /etc/pacman.d/mirrorlist

        [extra]
        Include = /etc/pacman.d/mirrorlist

        {"[multilib]\n        Include = /etc/pacman.d/mirrorlist" if multilib else ""}
    """)
    pacman_p = "etc/pacman.conf"
    pac_p = Path("/") / pacman_p
    if mnt_point:
        pac_p = mnt_point / pacman_p
    pac_p.write_text(pacman_content)


def write_etc_file(mnt_point: Path, files_to_write: dict[str, str]) -> None:
    for filepath, content in files_to_write.items():
        full_path = mnt_point / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with full_path.open("w") as file:
            file.write(content)
            log.info(f"Content: {content}\nWritten to: {full_path}")


###################################
# ETC/BOOT
###################################
def configure_sudo(mnt_point: Path, user_name: str, pless=False) -> None:
    sudoers_content = dedent(
        f"""\
        {user_name} ALL=(ALL:ALL) {"NOPASSWD:ALL" if pless else "ALL"}
        Defaults    insults
        Defaults    passwd_tries=10
        Defaults    lecture=never
        Defaults    passwd_timeout=0
        Defaults    timestamp_timeout=20
        Defaults    timestamp_type=global
        Defaults    editor=/usr/sbin/nvim, !env_editor
        """
    )
    (mnt_point / f"etc/sudoers.d/00_{user_name}").write_text(sudoers_content)
    log.info(f"{'Removed' if pless else 'Created'} pass requirement for {user_name}")


def sys_dots(mnt_point: Path, script_dir: Path) -> None:
    for dir_name in ["etc", "usr"]:
        source_dir = script_dir / dir_name
        target_dir = mnt_point / dir_name
        log.info("Processing %s -> %s", source_dir, target_dir)
        if not source_dir.exists():
            log.error("Source directory not found: %s", source_dir)
            continue
        shutil.copytree(
            source_dir, target_dir, dirs_exist_ok=True, copy_function=shutil.copy2
        )
        log.info("Copied %s to %s", source_dir, target_dir)


def sysd_plymouth_setup(mnt_point: Path, boot_opts=["quiet", "splash"]) -> None:
    entries_dir = mnt_point / "boot" / "loader" / "entries"
    for entry in entries_dir.iterdir():
        lines = entry.read_text().splitlines()
        new_lines = []
        for line in lines:
            if line.startswith("options "):
                existing_opts = line[len("options ") :].split()
                for opt in boot_opts:
                    if opt not in existing_opts:
                        existing_opts.append(opt)
                line = "options " + " ".join(existing_opts)
            new_lines.append(line)
        entry.write_text("\n".join(new_lines) + "\n")


def modify_fstab(mnt_point: Path) -> None:
    fstab_path = mnt_point / "etc" / "fstab"
    content = fstab_path.read_text()
    content = re.sub(r"^(?!#).*?\bfmask=\d+", "fmask=0077", content, flags=re.MULTILINE)
    content = re.sub(r"^(?!#).*?\bdmask=\d+", "dmask=0077", content, flags=re.MULTILINE)
    fstab_path.write_text(content)


def modify_mkinit(mnt_point: Path, hooks: list[str], plymouth: bool) -> None:
    if plymouth and "plymouth" not in hooks:
        hooks.insert(hooks.index("kms") + 1, "plymouth")
    with open(f"/{mnt_point}/etc/mkinitcpio.conf", "r+") as mkinit:
        content = mkinit.read()
        content = re.sub(r"\nHOOKS=.*", f"\nHOOKS=({' '.join(hooks)})", content)
        mkinit.seek(0)
        mkinit.truncate()
        mkinit.write(content)


def get_gfx_drivers(graphics_devices: dict[str, str]) -> list[GfxDriver]:
    driver_map = {
        "nvidia": GfxDriver.NvidiaOpenKernel,
        "geforce": GfxDriver.NvidiaOpenKernel,
        "amd": GfxDriver.AmdOpenSource,
        "ati": GfxDriver.AmdOpenSource,
        "intel": GfxDriver.IntelOpenSource,
    }
    return [
        driver_map.get(device.lower().split()[0], GfxDriver.VMOpenSource)
        for device in graphics_devices
    ]


###################################
# USR_SVC
###################################
def enable_user_serv(units: list[UsrSrv], username: str) -> list[str]:
    chroot_cmds: list[str] = []
    base_dir = f"/home/{username}/.config/systemd/user"
    for unit in units:
        target_dir = f"{base_dir}/{unit.target}.target.wants"
        chroot_cmds.append(f"mkdir -p {target_dir}")
        for service in unit.services:
            chroot_cmds.append(f"ln -sf {unit.source}/{service} {target_dir}/{service}")
    return chroot_cmds


def user_service(
    mnt_point: Path,
    username: str,
    terminal: str,
    user_script="user_setup.py",
    script_dir: str = Path(__file__).resolve().parent.name,
) -> list[str]:
    if terminal.strip().lower() == "alacritty":
        terminal = "alacritty -e"
    dir_path = f"home/{username}/.config/systemd/user"
    run_script = f"/home/{username}/{script_dir}/{user_script}"
    name = f"{user_script.rsplit('.', 1)[0]}.service"
    content = dedent(
        f"""\
        [Unit]
        Description=Open {terminal} {run_script} on login
        After=graphical-session.target

        [Service]
        Type=oneshot
        ExecStart=/usr/bin/{terminal} python {run_script}
        Restart=no

        [Install]
        WantedBy=graphical-session.target
        """
    )
    (mnt_point / dir_path / name).write_text(content)
    unit = UsrSrv(source=f"/{dir_path}", target="graphical-session", services=[name])
    chroot_cmds = enable_user_serv([unit], username)
    return chroot_cmds


###################################
# User Space
###################################
def copy_keys(
    mnt_point: Path, usb_key_dir: str, username: str, to_cp: dict[str, tuple[str, ...]]
) -> list[str]:
    chown_paths = []
    for folder, files in to_cp.items():
        sys_path = f"home/{username}/{folder}"
        mnt_dir = mnt_point / sys_path
        mnt_dir.mkdir(parents=True, exist_ok=True)
        mnt_dir.chmod(0o700)
        chown_paths.append(f"/{sys_path}")
        for name in files:
            src = Path("/root") / usb_key_dir / name
            dest = mnt_dir / name
            copy_file(src, dest)
            dest.chmod(0o600)
            chown_paths.append(f"/{sys_path}/{name}")
    return chown_paths


def set_extensions(mnt_point: Path, browser: str, ext_names: list[str]) -> None:
    file_path = mnt_point / "usr" / "lib" / browser / "distribution" / "policies.json"
    uninstall_names = ["google", "bing", "amazondotcom", "ebay", "twitter"]
    new_policies = {
        "DisableAppUpdate": True,
        "DisableDeveloperTools": False,
        "DisableFeedbackCommands": True,
        "DisableFirefoxStudies": True,
        "DisablePocket": True,
        "DisableProfileImport": False,
        "DisableSetDesktopBackground": False,
        "DisableTelemetry": True,
        "OverrideFirstRunPage": "about:welcome",
        "OverridePostUpdatePage": "",
        "DNSOverHTTPS": {"Enabled": False, "ProviderURL": "", "Locked": False},
        "HardwareAcceleration": True,
        "WebsiteFilter": {
            "Block": ["https://localhost/*"],
            "Exceptions": ["https://localhost/*"],
        },
        "Extensions": {
            "Install": [
                f"https://addons.mozilla.org/firefox/downloads/latest/{ext}/latest.xpi"
                for ext in ext_names
            ],
            "Uninstall": [f"{name}@search.mozilla.org" for name in uninstall_names],
        },
        "3rdparty": {
            "Extensions": {
                "uBlock0@raymondhill.net": {
                    "adminSettings": {
                        "assetsBootstrapLocation": "https://codeberg.org/librewolf/source/raw/branch/main/assets/uBOAssets.json"
                    }
                }
            }
        },
        "SearchEngines": {
            "PreventInstalls": False,
            "Default": "DuckDuckGo",
            "Remove": ["Bing", "Amazon.com", "eBay", "Twitter"],
        },
    }
    data = {}
    if file_path.exists():
        try:
            data = json.loads(file_path.read_text())
        except json.JSONDecodeError:
            log.warning(f"Corrupt JSON in {file_path}, resetting.")
    data.setdefault("policies", {}).update(new_policies)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data, indent=2))
    log.info(f"Policies for {browser} have been set (overwritten).")


###################################
# Archinstall
###################################
def show_menu(arch_config_handler: ArchConfigHandler) -> None:
    global_menu = GlobalMenu(arch_config_handler.config)
    global_menu.disable_all()
    global_menu.set_enabled("disk_config", True)
    global_menu.set_enabled("archinstall_language", True)
    global_menu.set_enabled("locale_config", True)
    global_menu.set_enabled("timezone", True)
    global_menu.set_enabled("bootloader_config", True)
    global_menu.set_enabled("ntp", True)
    global_menu.set_enabled("kernels", True)
    global_menu.set_enabled("hostname", True)
    global_menu.set_enabled("auth_config", True)
    global_menu.set_enabled("app_config", True)
    global_menu.set_enabled("packages", True)
    global_menu.set_enabled("__config__", True)
    result: ArchConfig | None = tui.run(global_menu)
    if result is None:
        sys.exit(0)


def perform_installation(
    arch_config_handler: ArchConfigHandler,
    application_handler: ApplicationHandler,
    gfx_drivers: list[GfxDriver],
) -> None:
    script_d = Path(__file__).resolve().parent
    start_time = time.monotonic()
    info("Starting installation...")
    config = arch_config_handler.config
    if not config.disk_config:
        error("No disk configuration provided")
        return
    disk_config = config.disk_config
    mountpoint = Path("/mnt/arch")
    locale = config.locale_config
    with Installer(mountpoint, disk_config, kernels=config.kernels) as installation:
        if disk_config.config_type != DiskLayoutType.Pre_mount:
            installation.mount_ordered_layout()
        if disk_config.config_type != DiskLayoutType.Pre_mount:
            if (
                disk_config.disk_encryption
                and disk_config.disk_encryption.encryption_type
                != EncryptionType.NO_ENCRYPTION
            ):
                installation.generate_key_files()
        nc = NoahConfig()
        cmd = [
            "reflector",
            *(part for opt in nc.reflector_options for part in opt.split()),
        ]
        run_dmc(cmd)
        generate_pacman_conf(None, no_extracts=list(nc.no_extracts))
        installation.minimal_installation(
            hostname=config.hostname, locale_config=locale
        )
        copy_file(
            Path("/etc/pacman.d/mirrorlist"), mountpoint / "etc/pacman.d/mirrorlist"
        )
        generate_pacman_conf(mountpoint, list(nc.no_extracts))

        if config.swap and config.swap.enabled:
            installation.setup_swap(algo=config.swap.algorithm)
        if (
            config.bootloader_config
            and config.bootloader_config.bootloader != Bootloader.NO_BOOTLOADER
        ):
            installation.add_bootloader(
                config.bootloader_config.bootloader,
                config.bootloader_config.uki,
                config.bootloader_config.removable,
            )
            if config.bootloader_config.bootloader == Bootloader.Systemd:
                if config.bootloader_config.uki:
                    print("Nope")
                else:
                    sysd_plymouth_setup(mountpoint)

        modify_mkinit(mountpoint, list(nc.mkinit_hooks), plymouth=True)

        for driver in gfx_drivers:
            profile_handler.install_gfx_driver(installation, driver)

        profile_handler.install_greeter(installation, GreeterType.Ly)

        if config.network_config:
            install_network_config(config.network_config, installation, None)

        installation.add_additional_packages("realtime-privileges")

        tmp = mountpoint / "tmp" / nc.dots_repo
        tmp.mkdir(exist_ok=True)
        git = f"https://github.com/{nc.git_user}/{nc.dots_repo}.git"
        run_dmc(["git", "clone", git, str(tmp)])
        shutil.rmtree(tmp / ".git")
        for p in tmp.iterdir():
            p.rename(p.parent / ("." + p.name))
        copy_dir(tmp, mountpoint / "etc" / "skel")

        if config.auth_config:
            if config.auth_config.users:
                installation.create_users(config.auth_config.users)

        if app_config := config.app_config:
            application_handler.install_applications(installation, app_config)

        srv = "keyserver.ubuntu.com"
        web = "https://cdn-mirror.chaotic.cx/chaotic-aur/"
        run_dmc(["pacman-key", "--init"])
        installation.arch_chroot(" ".join(["pacman-key", "--init"]))
        cmd = ["pacman-key", "--recv-key", "3056513887B78AEB", "--keyserver", srv]
        run_dmc(cmd)
        installation.arch_chroot(" ".join(cmd))
        cmd = ["pacman-key", "--lsign-key", "3056513887B78AEB"]
        run_dmc(cmd)
        installation.arch_chroot(" ".join(cmd))
        cmd = ["pacman", "-U", "--noconfirm", f"{web}chaotic-keyring.pkg.tar.zst"]
        run_dmc(cmd)
        installation.arch_chroot(" ".join(cmd))
        cmd = ["pacman", "-U", "--noconfirm", f"{web}chaotic-mirrorlist.pkg.tar.zst"]
        run_dmc(cmd)
        installation.arch_chroot(" ".join(cmd))
        for path in [Path("/etc/pacman.conf"), mountpoint / "etc/pacman.conf"]:
            with path.open("a") as f:
                f.write("\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n")
        run_dmc(["pacman", "-Sy"], check=True)
        installation.arch_chroot("pacman -Sy")

        if config.packages and config.packages[0] != "":
            installation.add_additional_packages(config.packages)

        if timezone := config.timezone:
            installation.set_timezone(timezone)

        if config.ntp:
            installation.activate_time_synchronization()

        write_etc_file(mountpoint, nc.etc_files_to_write)
        copy_dir(Path("/root") / nc.wireguard_dir, mountpoint / "etc" / "wireguard")
        reflector_timer_conf = mountpoint / "etc/xdg/reflector/reflector.conf"
        reflector_timer_conf.write_text("\n".join(nc.reflector_options))
        set_extensions(mountpoint, nc.firefox_browser, list(nc.firefox_extensions))
        sys_dots(mountpoint, script_d)

        git = "https://github.com/vinceliuice/WhiteSur-icon-theme.git"
        installation.arch_chroot(f"git clone {git}")
        installation.arch_chroot("bash ./WhiteSur-icon-theme/install.sh")
        icon_path = mountpoint / "usr/share/icons"
        white_sur_light = icon_path / "WhiteSur-light"
        if white_sur_light.exists():
            shutil.rmtree(white_sur_light)
            log.info(f"Removed {white_sur_light}")
        themes_to_modify = []
        for folder in icon_path.iterdir():
            if folder.is_dir() and (
                "-dark" in folder.name or "WhiteSur" in folder.name
            ):
                themes_to_modify.append(folder)
        for theme_dir in themes_to_modify:
            for svg_file in theme_dir.rglob("*.svg"):
                if svg_file.is_file():
                    text = svg_file.read_text()
                    if "#ffffff" in text:
                        svg_file.write_text(text.replace("#ffffff", "#F4F5F6"))
                        log.info(f"Modified {svg_file}")

        if config.auth_config:
            if config.auth_config.users:
                first_user = config.auth_config.users[0].username
                configure_sudo(mountpoint, first_user, pless=True)
                cmd = f"paru -S --noconfirm --needed {' '.join(nc.aur_pkgs)}"
                installation.arch_chroot(cmd, first_user)
                configure_sudo(mountpoint, first_user)
                first_user_home = f"home/{config.auth_config.users[0].username}"
                copy_dir(script_d, (mountpoint / first_user_home / script_d.name))
                chown_paths = copy_keys(
                    mountpoint, nc.usb_key_dir, first_user, nc.to_cp
                )
                for ch_p in chown_paths:
                    installation.chown(first_user, ch_p)
                for user in config.auth_config.users:
                    installation.arch_chroot("xdg-user-dirs-update", user.username)
                    nc.populate_usr_srv(user.username)
                    chroot_cmds = enable_user_serv(list(nc.usr_srv), user.username)
                    chroot_cmds += user_service(mountpoint, user.username, nc.terminal)
                    for cmd in chroot_cmds:
                        installation.arch_chroot(cmd, user.username)
                    user_home = f"home/{user.username}"
                    for app in nc.apps_to_hide:
                        file_p = f"{user_home}/.local/share/applications/{app}.desktop"
                        (mountpoint / file_p).write_text(
                            "[Desktop Entry]\nNoDisplay=true\n"
                        )
                    installation.arch_chroot(
                        f"chown -R {user.username}:{user.username} /{user_home}"
                    )

        installation.enable_service(config.services)
        installation.disable_service(list(nc.disable_svcs))

        if disk_config.has_default_btrfs_vols():
            btrfs_options = disk_config.btrfs_options
            snapshot_config = btrfs_options.snapshot_config if btrfs_options else None
            snapshot_type = snapshot_config.snapshot_type if snapshot_config else None
            if snapshot_type:
                bootloader = (
                    config.bootloader_config.bootloader
                    if config.bootloader_config
                    else None
                )
                installation.setup_btrfs_snapshot(snapshot_type, bootloader)

        installation.genfstab()
        modify_fstab(mountpoint)

        debug(f"Disk states after installing:\n{disk_layouts()}")
        if not arch_config_handler.args.silent:
            elapsed_time = time.monotonic() - start_time
            action: PostInstallationAction = tui.run(
                lambda: select_post_installation(elapsed_time)
            )
            match action:
                case PostInstallationAction.EXIT:
                    pass
                case PostInstallationAction.REBOOT:
                    _ = subprocess.run(["sudo", "reboot"], check=True)
                case PostInstallationAction.CHROOT:
                    try:
                        installation.drop_to_shell()
                    except Exception:
                        pass


def main() -> None:
    nc = NoahConfig()
    mnt_cp_keys(nc.usb_key_dir, list(nc.usb_cp_files), nc.wireguard_dir)
    arch_config_handler = ArchConfigHandler()
    if pw := src_pass_file(nc.usb_key_dir, nc.my_pass):
        arch_config_handler.config.auth_config = AuthenticationConfiguration(
            None, [User(nc.username, Password(pw), True, list(nc.groups))], None
        )
    arch_config_handler.config.hostname = arch_config.hostname
    arch_config_handler.config.ntp = arch_config.ntp
    arch_config_handler.config.swap = arch_config.swap
    arch_config_handler.config.timezone = arch_config.timezone
    arch_config_handler.config.bootloader_config = arch_config.bootloader_config
    arch_config_handler.config.ntp = True
    arch_config_handler.config.kernels = arch_config.kernels
    arch_config_handler.config.services = arch_config.services + list(
        nc.custom_services
    )
    arch_config_handler.config.app_config = arch_config.app_config
    gfx_drivers = get_gfx_drivers(_sys_info.graphics_devices)
    pkgs = list(nc.pkgs["base"] + nc.pkgs["language"] + nc.pkgs["chaotic_repo"])
    if GfxDriver.VMOpenSource not in gfx_drivers:
        pkgs.extend(list(nc.pkgs["extra"] + nc.pkgs["extra_chaos"]))
    arch_config_handler.config.packages = pkgs
    show_menu(arch_config_handler)
    config = ConfigurationOutput(arch_config_handler.config)
    config.write_debug()
    config.save()
    if not arch_config_handler.args.silent:
        aborted = False
        res: bool = tui.run(config.confirm_config)
        if not res:
            debug("Installation aborted")
            aborted = True
        if aborted:
            return main()
    if arch_config_handler.config.disk_config:
        fs_handler = FilesystemHandler(arch_config_handler.config.disk_config)
        if not delayed_warning("Starting device modifications in "):
            return main()
        fs_handler.perform_filesystem_operations()
    perform_installation(arch_config_handler, ApplicationHandler(), gfx_drivers)


if __name__ == "__main__":
    main()
