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
from archinstall.lib.installer import Installer, SysCommand
from archinstall.lib.menu.util import delayed_warning
from archinstall.lib.models import (
    Bootloader,
    Audio,
    AudioConfiguration,
    ApplicationConfiguration,
    BluetoothConfiguration,
)
from archinstall.lib.models.device import DiskLayoutType, EncryptionType
from archinstall.lib.models.users import User
from archinstall.lib.output import debug, error, info
from archinstall.tui.ui.components import tui
from archinstall.lib.models.users import Password
from pydantic import BaseModel
from pathlib import Path
import sys
import time
import subprocess
import json
import re
import shlex
import shutil
from dataclasses import dataclass, field
from textwrap import dedent
from utils import log, run_dmc, yes_no
from archinstall.lib.profile.profiles_handler import profile_handler


class UsrSrv(BaseModel):
    source: str
    target: str
    services: list[str]


###########################################################
# ARCHINSTALL CONF
###########################################################
@dataclass()
class NoahConfig:
    user_name: str = "nick"
    hostname: str = "yulia"
    timezone: str = "US/Eastern"
    dots_git_repo: str = "acctux/polka"
    usb_key_dir: str = "keys"
    wireguard_dir: str = "wireguard"
    my_pass: str = "pass.py"
    parallel_downloads: int = 10
    multilib: bool = True
    kernel: tuple[str, ...] = ("linux",)
    groups: tuple[str, ...] = ("adm", "games", "realtime", "storage", "video")
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
    sys_services: tuple[str, ...] = (
        "ananicy-cpp",
        "named",
        "swayosd-libinput-backend",
        "systemd-oomd",
        "btrfs-scrub@-.timer",
        "btrfs-scrub@home.timer",
        "fstrim.timer",
        "logrotate.timer",
        "man-db.timer",
        "paccache.timer",
        "reflector.timer",
    )
    custom_services: tuple[str, ...] = (
        "loggy",
        "sysinfo",
    )
    disable_svcs: tuple[str, ...] = (
        "systemd-resolved",
        "systemd-networkd-wait-online",
    )
    usr_srv: tuple[UsrSrv, ...] = (
        UsrSrv(
            source="/usr/lib/systemd/user",
            target="default",
            services=["pipewire-pulse.service", "psd.service"],
        ),
        UsrSrv(
            source="/usr/lib/systemd/user",
            target="sockets",
            services=[
                "pipewire-pulse.socket",
                "gnome-keyring-daemon.socket",
                "gcr-ssh-agent.socket",
                "mpd.socket",
            ],
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
            "etc/tmpfiles.d/mpd.conf": dedent(
                f"""\
                d /home/{NoahConfig.user_name}/.cache/mpd 0755 {NoahConfig.user_name} mpd -
                d /home/{NoahConfig.user_name}/.cache/mpd/playlists 0755 {NoahConfig.user_name} mpd -
                """
            ),
        }
    )


#########################
# UTILS
#########################
def run_chroot(
    commands: list[str], mnt_point: Path, username: str | None = None, peek=True
) -> None:
    script_path = "var/tmp/user-commands.sh"
    chroot_path = mnt_point / script_path
    chroot_path.parent.mkdir(parents=True, exist_ok=True)
    with open(chroot_path, "w") as script:
        script.write("#!/bin/bash\n")
        if peek:
            script.write("set -e\n")
        for cmd in commands:
            if username:
                log.info(f"Will run as {username}: {cmd}")
                cmd = f"su - {username} -c {shlex.quote(cmd)}"
            log.info(f"Chroot run: {cmd}")
            script.write(cmd + "\n")
    chroot_path.chmod(0o755)
    SysCommand(f"arch-chroot -S {mnt_point} /{script_path}")
    chroot_path.unlink()


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
            f"\033[93m{'Name':<8}\033[0m "
            f"\033[94m{'Size':<8}\033[0m "
            f"\033[96m{'FS Type':>8}\033[0m"
        )
        print("-" * 45)
        for i, (name, size, fstype) in enumerate(candidates, 1):
            print(
                f"\033[91m{i:<5}\033[0m "
                f"\033[93m{name:<8}\033[0m "
                f"\033[94m{size:<8}\033[0m "
                f"\033[96m{fstype:>8}\033[0m"
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
def chaotic_repo(mnt_point: Path) -> None:
    def append_repo(path: Path):
        with path.open("a") as f:
            f.write("\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n")

    key_serv = "keyserver.ubuntu.com"
    chaotic_web = "https://cdn-mirror.chaotic.cx/chaotic-aur/"
    cmds = [
        ["pacman-key", "--init"],
        ["pacman-key", "--recv-key", "3056513887B78AEB", "--keyserver", key_serv],
        ["pacman-key", "--lsign-key", "3056513887B78AEB"],
        ["pacman", "-U", "--noconfirm", f"{chaotic_web}chaotic-keyring.pkg.tar.zst"],
        ["pacman", "-U", "--noconfirm", f"{chaotic_web}chaotic-mirrorlist.pkg.tar.zst"],
    ]
    for cmd in cmds:
        run_dmc(cmd, check=True)
    append_repo(Path("/etc/pacman.conf"))
    run_dmc(["pacman", "-Sy"], check=True)
    run_chroot([" ".join(cmd) for cmd in cmds], mnt_point)
    append_repo(mnt_point / "etc/pacman.conf")
    run_chroot(["pacman -Sy"], mnt_point)


def generate_pacman_conf(
    mnt_point: Path | None,
    no_extracts: list,
    parallel_downloads: int = 10,
    multilib: bool = True,
) -> None:
    pacman_p = "etc/pacman.conf"
    pac_mnt_p = Path("/") / pacman_p
    if mnt_point:
        pac_mnt_p = mnt_point / pacman_p
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
    pac_mnt_p.write_text(pacman_content)


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
def enable_user_serv(mnt_point: Path, units: list[UsrSrv], username: str) -> None:
    user_commands: list[str] = []
    base_dir = Path(f"/home/{username}/.config/systemd/user")
    for unit in units:
        for service in unit.services:
            target_dir = base_dir / f"{unit.target}.target.wants"
            user_commands.append(f"mkdir -p {target_dir}")
            user_commands.append(
                f"ln -sf {unit.source}/{service} {target_dir / service}"
            )
    run_chroot([f"chown -R {username}:{username} /home/{username}/"], mnt_point)
    run_chroot(user_commands, mnt_point, username)


def user_service(
    mnt_point: Path,
    username: str,
    terminal: str,
    user_script="user_setup.py",
    script_dir: str = Path(__file__).resolve().parent.name,
) -> None:
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
    enable_user_serv(mnt_point, [unit], username)


###################################
# User Space
###################################
def install_icon_theme(
    mnt_point: Path,
    git: str = "vinceliuice/WhiteSur-icon-theme",
    old: str = "#ffffff",
    new: str = "#F4F5F6",
    icon_dir: str = "/usr/share/icons",
) -> None:
    tmp = "/tmp/icons"
    cmd = [f"git clone https://github.com/{git}.git {tmp}", f"bash {tmp}/install.sh"]
    run_chroot(cmd, mnt_point)
    icon_path = mnt_point / icon_dir
    for svg in [p for p in icon_path.rglob("*.svg") if "scalable" not in p.parts]:
        text = svg.read_text()
        if old in text:
            svg.write_text(text.replace(old, new))
    if (icon_path / "WhiteSur-light").exists():
        shutil.rmtree(icon_path / "WhiteSur-light")


def clone_dots_to_skel(mnt_point: Path, git_repo: str) -> None:
    tmp = mnt_point / "tmp" / git_repo
    cmd = ["git", "clone", f"https://github.com/{git_repo}.git", f"{tmp}"]
    run_dmc(cmd, True)
    shutil.rmtree(tmp / ".git")
    for p in tmp.iterdir():
        p.rename(p.parent / ("." + p.name))
    copy_dir(tmp, mnt_point / "etc" / "skel")


def copy_keys(
    mnt_point: Path, usb_key_dir: str, username: str, to_cp: dict[str, tuple[str, ...]]
) -> None:
    chown_cmds = []
    for folder, files in to_cp.items():
        sys_path = Path("home") / username / folder
        mnt_dir = mnt_point / sys_path
        mnt_dir.mkdir(parents=True, exist_ok=True)
        mnt_dir.chmod(0o700)
        chown_cmds.append(f"chown {username}:{username} /{sys_path}")
        for name in files:
            src = Path("/root") / usb_key_dir / name
            dest = mnt_dir / name
            copy_file(src, dest)
            dest.chmod(0o600)
            chown_cmds.append(f"chown {username}:{username} /{sys_path / name}")
    if chown_cmds:
        run_chroot(chown_cmds, mnt_point)


def set_firefox_extensions(mnt_point: Path, browser: str, ext_names: list) -> None:
    file_path = mnt_point / "usr" / "lib" / browser / "distribution" / "policies.json"
    if file_path.exists():
        new_exts = [
            f"https://addons.mozilla.org/firefox/downloads/latest/{ext}/latest.xpi"
            for ext in ext_names
        ]
        data = json.loads(file_path.read_text())
        install = data["policies"]["Extensions"]["Install"]
        for ext in new_exts:
            if ext not in install:
                install.append(ext)
        file_path.write_text(json.dumps(data, indent=2))
        log.info("Firefox extensions updated successfully.")


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
    cf: NoahConfig,
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
        installation._hooks = list(cf.mkinit_hooks)
        if disk_config.config_type != DiskLayoutType.Pre_mount:
            installation.mount_ordered_layout()
        if disk_config.config_type != DiskLayoutType.Pre_mount:
            if (
                disk_config.disk_encryption
                and disk_config.disk_encryption.encryption_type
                != EncryptionType.NO_ENCRYPTION
            ):
                installation.generate_key_files()
        # cmd = [
        #     "reflector",
        #     *(part for opt in cf.reflector_options for part in opt.split()),
        # ]
        # run_dmc(cmd)
        # generate_pacman_conf(None, no_extracts=list(cf.no_extracts))
        installation.minimal_installation(
            hostname=config.hostname, locale_config=locale
        )
        # generate_pacman_conf(mountpoint, list(cf.no_extracts))
        # copy_file(
        #     Path("/etc/pacman.d/mirrorlist"), mountpoint / "etc/pacman.d/mirrorlist"
        # )
        # chaotic_repo(mountpoint)
        # modify_mkinit(mountpoint, list(cf.mkinit_hooks), plymouth=True)
        # if config.swap and config.swap.enabled:
        #     installation.setup_swap(algo=config.swap.algorithm)
        if (
            config.bootloader_config
            and config.bootloader_config.bootloader != Bootloader.NO_BOOTLOADER
        ):
            installation.add_bootloader(
                config.bootloader_config.bootloader,
                uki_enabled=True,
                bootloader_removable=False,
            )
            if config.bootloader_config.bootloader == Bootloader.Systemd:
                sysd_plymouth_setup(mountpoint)
        installation.copy_iso_network_config(enable_services=True)
        installation.set_timezone(config.timezone)
        for driver in gfx_drivers:
            profile_handler.install_gfx_driver(installation, driver)
        profile_handler.install_greeter(installation, GreeterType.Ly)
        installation.add_additional_packages("realtime-privileges")
        clone_dots_to_skel(mountpoint, cf.dots_git_repo)
        if config.auth_config:
            if config.auth_config.users:
                installation.create_users(config.auth_config.users)
        if app_config := config.app_config:
            application_handler.install_applications(installation, app_config)
        if config.packages and config.packages[0] != "":
            installation.add_additional_packages(config.packages)
        for filepath, content in cf.etc_files_to_write.items():
            full_path = mountpoint / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with full_path.open("w") as file:
                file.write(content)
                log.info(f"Content: {content}\nWritten to: {full_path}")
        copy_dir(Path("/root") / cf.wireguard_dir, mountpoint / "etc" / "wireguard")
        (mountpoint / "etc/xdg/reflector/reflector.conf").write_text(
            "\n".join(cf.reflector_options)
        )
        set_firefox_extensions(
            mountpoint, cf.firefox_browser, list(cf.firefox_extensions)
        )
        sys_dots(mountpoint, script_d)
        install_icon_theme(mountpoint)
        if config.auth_config:
            if config.auth_config.users:
                first_user = config.auth_config.users[0].username
                configure_sudo(mountpoint, first_user, pless=True)
                cmd = [f"paru -S --noconfirm --needed {' '.join(cf.aur_pkgs)}"]
                run_chroot(cmd, mountpoint, first_user)
                configure_sudo(mountpoint, first_user)
                first_user_home = f"home/{config.auth_config.users[0].username}"
                copy_dir(script_d, (mountpoint / first_user_home / script_d.name))
                copy_keys(mountpoint, cf.usb_key_dir, first_user, cf.to_cp)
                for user in config.auth_config.users:
                    run_chroot(["xdg-user-dirs-update"], mountpoint, user.username)
                    enable_user_serv(mountpoint, list(cf.usr_srv), user.username)
                    user_service(mountpoint, user.username, cf.terminal)
                    user_home = f"home/{user.username}"
                    for app in cf.apps_to_hide:
                        file_p = f"home/{user.username}/.local/share/applications/{app}.desktop"
                        (mountpoint / file_p).write_text(
                            "[Desktop Entry]\nNoDisplay=true\n"
                        )
                        installation.chown(user.username, f"/{user_home}")
                    installation.chown(user.username, f"/{user_home}/{script_d.name}")
        installation.enable_service(arch_config_handler.config.services)
        installation.disable_service(list(cf.disable_svcs))
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
    cf = NoahConfig()
    arch_config_handler = ArchConfigHandler()
    mnt_cp_keys(cf.usb_key_dir, list(cf.usb_cp_files), cf.wireguard_dir)
    if pw := src_pass_file(cf.usb_key_dir, cf.my_pass):
        user = User(cf.user_name, Password(pw), True, list(cf.groups))
        arch_config_handler.config.auth_config = AuthenticationConfiguration(
            None, [user]
        )
    arch_config_handler.config.hostname = cf.hostname
    arch_config_handler.config.swap = ZramConfiguration(enabled=True)
    arch_config_handler.config.timezone = cf.timezone
    arch_config_handler.config.bootloader_config = BootloaderConfiguration(
        Bootloader.Systemd
    )
    arch_config_handler.config.ntp = True
    arch_config_handler.config.kernels = list(cf.kernel)
    arch_config_handler.config.services = list(cf.sys_services + cf.custom_services)
    arch_config_handler.config.app_config = ApplicationConfiguration(
        BluetoothConfiguration(True),
        AudioConfiguration(Audio.PIPEWIRE),
        PowerManagementConfiguration(PowerManagement.TUNED),
        None,
        FirewallConfiguration(Firewall.FWD),
        FontsConfiguration([FontPackage.EMOJI, FontPackage.LIBERATION]),
    )
    gfx_drivers = get_gfx_drivers(_sys_info.graphics_devices)
    pkgs = list(cf.pkgs["base"] + cf.pkgs["language"] + cf.pkgs["chaotic_repo"])
    if GfxDriver.VMOpenSource not in gfx_drivers:
        pkgs.extend(list(cf.pkgs["extra"] + cf.pkgs["extra_chaos"]))
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
    perform_installation(arch_config_handler, ApplicationHandler(), cf, gfx_drivers)


if __name__ == "__main__":
    main()
