from pathlib import Path
from textwrap import dedent
from archinstall.lib.models.bootloader import BootloaderConfiguration
from archinstall.lib.models.application import (
    PowerManagementConfiguration,
    PowerManagement,
    Firewall,
    FirewallConfiguration,
    FontPackage,
    FontsConfiguration,
    ZramConfiguration,
)
from archinstall.lib.models import (
    ApplicationConfiguration,
    BluetoothConfiguration,
    AudioConfiguration,
    PrintServiceConfiguration,
    Audio,
    LocaleConfiguration,
    NetworkConfiguration,
    NicType,
    Bootloader,
)
from archinstall.lib.args import ArchConfig
from pydantic import BaseModel
from dataclasses import dataclass, field


class UsrSrv(BaseModel):
    source: str
    target: str
    services: list[str]


arch_config = ArchConfig(
    app_config=ApplicationConfiguration(
        bluetooth_config=BluetoothConfiguration(enabled=True),
        audio_config=AudioConfiguration(audio=Audio.PIPEWIRE),
        power_management_config=PowerManagementConfiguration(PowerManagement.TUNED),
        print_service_config=PrintServiceConfiguration(enabled=False),
        firewall_config=FirewallConfiguration(Firewall.FWD),
        fonts_config=FontsConfiguration([FontPackage.LIBERATION, FontPackage.EMOJI]),
    ),
    locale_config=LocaleConfiguration(
        kb_layout="us", sys_lang="en_US", sys_enc="UTF-8"
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
    def populate_usr_srv(self, user_name: str) -> list[UsrSrv]:
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
        return list(self.usr_srv)

    groups: tuple[str, ...] = ("adm", "games", "realtime", "storage", "video")
    dots_repo: str = "polka"
    git_user: str = "acctux"
    usb_key_dir: str = "keys"
    wireguard_dir: str = "wireguard"
    my_pass: str = "users.json"
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
    ###########################################################
    # USER CONFIG
    ###########################################################
    android: bool = True
    firewalld: bool = True
    ###########################################################
    # HOME & PATHS
    ###########################################################
    HOME: Path = field(default_factory=Path.home)
    DESKTOP: Path = field(init=False)
    ENCRYPTED: Path = field(init=False)
    GIT_DIR: Path = field(init=False)
    dots_path: Path = field(init=False)
    DOCS: Path = field(init=False)
    ssh_path: Path = field(init=False)
    gpg_path: Path = field(init=False)
    masterpass_path: Path = field(init=False)
    ###########################################################
    # REPOSITORIES
    ###########################################################
    repos: list[str] = field(default_factory=lambda: ["noah", "polka"])
    private_repos: list[str] = field(default_factory=lambda: ["Docs"])
    ###########################################################
    # DOTFILES
    ###########################################################
    dirs_to_link: list[str] = field(default_factory=lambda: ["local/bin"])
    sec_dir: Path = field(init=False)
    ind_dirs: dict[str, Path] = field(init=False)
    ###########################################################
    # ICONS
    ###########################################################
    dirs_icons: dict[Path, str] = field(init=False)
    ###########################################################
    # YAZI PLUGINS
    ###########################################################
    yazi_plugins: list[str] = field(
        default_factory=lambda: [
            "yazi-rs/plugins:jump-to-char",
            "uhs-robert/sshfs",
            "boydaihungst/gvfs",
            "uhs-robert/recycle-bin",
            "h-hg/yamb",
        ]
    )

    def __post_init__(self):
        self.DESKTOP = self.HOME / "Desktop"
        self.ENCRYPTED = self.DESKTOP / "Encrypted"
        self.GIT_DIR = self.HOME / "Lit"
        self.DOTS = self.GIT_DIR / "polka"
        self.DOCS = self.GIT_DIR / "Docs"
        self.ssh_path = self.HOME / ".ssh" / "id_ed25519"
        self.gpg_path = self.HOME / ".gnupg" / "my_sec_gpg.asc"
        self.masterpass_path = self.HOME / ".ssh" / "pass.txt"
        self.sec_dir = self.DOCS / "base"
        self.ind_dirs = {
            "fonts": self.HOME / ".local" / "share",
            "task": self.HOME / ".config",
            "zsh": self.HOME / ".config",
            "git": self.HOME / ".config",
            "gh": self.HOME / ".config",
        }
        self.dirs_icons = {
            self.DESKTOP / "Games": "folder-games",
            self.ENCRYPTED: "folder-locked",
            self.GIT_DIR: "folder-github",
            self.GIT_DIR / "noah": "folder-root",
            self.DOCS: "folder-bookmark",
            self.DOTS: "folder-html",
        }


pkgs: dict[str, list[str]] = {
    "base": [
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
        "zoxide",
    ],
    "language": [
        "hunspell-en_us",
        "hyphen-en",
        "tesseract-data-eng",
    ],
    "chaotic_repo": [
        "cachyos-ananicy-rules-git",
        "floorp",
        "octopi",
        "paru",
        "systemd-oomd-defaults",
        "ocrmypdf",
    ],
    "extra": [
        "rust",
        "stylua",
        "yamlfmt",
        "tree-sitter-rust",
        "deluge-gtk",
        "nvtop",
        "jolt",
        "ugrep",
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
    ],
    "extra_chaos": [
        "logiops",
        "neovim-symlinks",
        "ayugram-desktop-git",
        "qt6-imageformats",  # AyuGram missing dependency
        "betterbird-bin",
        "nchat-git",
        "proton-cachyos-slr",
        "rpcs3-git",
        "eden-git",
    ],
}

aur_pkgs: tuple[str, ...] = ("wvkbd-deskintl",)
