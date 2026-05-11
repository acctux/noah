from textwrap import dedent

arch_config_json = {
    "app_config": {
        "audio_config": {"audio": "pipewire"},
        "bluetooth_config": {"enabled": True},
        "firewall_config": {"firewall": "firewalld"},
        "fonts_config": {"fonts": ["noto-fonts-emoji", "ttf-liberation"]},
        "power_management_config": {"power_management": "tuned"},
        "print_service_config": {"enabled": False},
    },
    "archinstall-language": "English",
    "bootloader_config": {"bootloader": "Limine", "removable": False, "uki": False},
    "disk_config": {
        "btrfs_options": {"snapshot_config": {"type": "Timeshift"}},
        "config_type": "manual_partitioning",
        "device_modifications": [],
        "disk_encryption": {
            "encryption_type": "luks",
            "lvm_volumes": [],
            "partitions": ["5734738e-adf6-4a35-91b1-51ea2d13408d"],
        },
    },
    "hostname": "yulia",
    "kernels": ["linux"],
    "locale_config": {"kb_layout": "us", "sys_enc": "UTF-8", "sys_lang": "en_US.UTF-8"},
    "network_config": {"type": "iso"},
    "ntp": True,
    "packages": [],
    "pacman_config": {"color": True, "parallel_downloads": 10},
    "profile_config": {
        "gfx_driver": "AMD / ATI (open-source)",
        "greeter": "ly",
        "profile": {
            "custom_settings": {"Hyprland": {"seat_access": "polkit"}},
            "details": ["Hyprland"],
            "main": "Desktop",
        },
    },
    "services": [
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
        "loggy",
        "sysinfo",
    ],
    "swap": {"algorithm": "zstd", "enabled": True},
    "timezone": "US/Eastern",
    "version": "4.3",
}
orig_arch_config_json = {
    "app_config": {
        "audio_config": {"audio": "pipewire"},
        "bluetooth_config": {"enabled": True},
        "firewall_config": {"firewall": "firewalld"},
        "fonts_config": {"fonts": ["noto-fonts-emoji", "ttf-liberation"]},
        "power_management_config": {"power_management": "tuned"},
        "print_service_config": {"enabled": False},
    },
    "archinstall-language": "English",
    "bootloader_config": {"bootloader": "Limine", "removable": False, "uki": False},
    "disk_config": {
        "btrfs_options": {"snapshot_config": {"type": "Timeshift"}},
        "config_type": "manual_partitioning",
        "device_modifications": [
            {
                "device": "/dev/nvme0n1",
                "partitions": [
                    {
                        "btrfs": [],
                        "flags": ["boot", "esp"],
                        "fs_type": "fat32",
                        "mount_options": [],
                        "mountpoint": "/boot",
                        "obj_id": "cee25bd2-ec12-4cf0-a3e7-e25a5eb2c2d2",
                        "size": {
                            "sector_size": {"unit": "B", "value": 512},
                            "unit": "MiB",
                            "value": 512,
                        },
                        "start": {
                            "sector_size": {"unit": "B", "value": 512},
                            "unit": "MiB",
                            "value": 1,
                        },
                        "status": "create",
                        "type": "primary",
                    },
                    {
                        "btrfs": [
                            {"mountpoint": "/", "name": "@"},
                            {"mountpoint": "/home", "name": "@home"},
                            {"mountpoint": "/var/log", "name": "@log"},
                            {"mountpoint": "/var/cache/pacman/pkg", "name": "@pkg"},
                        ],
                        "flags": [],
                        "fs_type": "btrfs",
                        "mount_options": ["compress=zstd"],
                        "obj_id": "5734738e-adf6-4a35-91b1-51ea2d13408d",
                        "size": {
                            "sector_size": {"unit": "B", "value": 512},
                            "unit": "B",
                            "value": 511033999360,
                        },
                        "start": {
                            "sector_size": {"unit": "B", "value": 512},
                            "unit": "B",
                            "value": 537919488,
                        },
                        "status": "create",
                        "type": "primary",
                    },
                ],
                "wipe": True,
            }
        ],
        "disk_encryption": {
            "encryption_type": "luks",
            "lvm_volumes": [],
            "partitions": ["5734738e-adf6-4a35-91b1-51ea2d13408d"],
        },
    },
    "hostname": "yulia",
    "kernels": ["linux"],
    "locale_config": {"kb_layout": "us", "sys_enc": "UTF-8", "sys_lang": "en_US.UTF-8"},
    "network_config": {"type": "iso"},
    "ntp": True,
    "packages": [],
    "pacman_config": {"color": True, "parallel_downloads": 10},
    "profile_config": {
        "gfx_driver": "AMD / ATI (open-source)",
        "greeter": "ly",
        "profile": {
            "custom_settings": {"Hyprland": {"seat_access": "polkit"}},
            "details": ["Hyprland"],
            "main": "Desktop",
        },
    },
    "services": [
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
        "loggy",
        "sysinfo",
    ],
    "swap": {"algorithm": "zstd", "enabled": True},
    "timezone": "US/Eastern",
    "version": "4.3",
}
json_config = {
    "parallel_downloads": 10,
    "terminal": "kitty",
    "firefox_browser": "floorp",
    "dots_repo": "polka",
    "git_user": "acctux",
    "encrypted_dir": "Desktop/Encrypted",
    "ssh_key_file": "id_ed25519",
    "gpg_key_file": "my_sec_gpg.asc",
    "master_pass_file": "pass.txt",
    "my_pass": "users.json",
    "dirs_to_link": [
        "local/bin",
    ],
    "git_repos": [
        {
            "username": "acctux",
            "repos": [
                ["noah", "Lit/noah"],
                ["polka", "Lit/polka"],
                ["docs", "Lit/Docs"],
            ],
        }
    ],
    "mkinit_hooks": [
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
    ],
    "reflector_options": [
        "--country US",
        "--protocol https",
        "--latest 15",
        "--sort rate",
        "--number 3",
        "--save /etc/pacman.d/mirrorlist",
    ],
    "disable_svcs": [
        "systemd-resolved",
        "systemd-networkd-wait-online",
    ],
    "apps_to_hide": [
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
    ],
    "no_extracts": [
        "etc/xdg/autostart/firewall-applet.desktop",
        "usr/share/icons/capitaine-cursors/*",
    ],
    "to_cp": {
        "files_to_cp": [
            {
                "source_dir": "noahinstall",
                "target_dir": ".ssh",
                "names": [
                    "users.json",
                    "id_ed25519",
                    "pass.txt",
                ],
            },
            {
                "source_dir": "noahinstall",
                "target_dir": ".gnupg",
                "names": [
                    "my_sec_gpg.asc",
                ],
            },
        ],
        "dir_contents_to_cp": [
            {
                "source_dir": "noahinstall",
                "target_dir": "/etc/wireguard",
                "names": [
                    "wireguard",
                ],
            },
        ],
    },
    "user_services": {
        "/usr/lib/systemd/user": {
            "default": [
                "psd.service",
            ],
            "sockets": [
                "gcr-ssh-agent.socket",
                "mpd.socket",
            ],
            "graphical-session": [
                "cliphist.service",
                "hypridle.service",
                "hyprsunset.service",
                "swaync.service",
                "waybar.service",
            ],
        },
        "/.config/systemd/user": {
            "graphical-session": [
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
            "timers": [
                "emailcheck.timer",
                "task-reminder.timer",
                "task-schedule.timer",
                "wall.timer",
            ],
        },
    },
    "ind_dirs": {
        "fonts": ".local/share",
        "task": ".config",
        "zsh": ".config",
        "git": ".config",
        "gh": ".config",
    },
    "dirs_icons": {
        "Desktop/Games": "folder-games",
        "Desktop/Encrypted": "folder-locked",
        "Lit": "folder-github",
        "Lit/noah": "folder-root",
        "Lit/Docs": "folder-bookmark",
        "Lit/polka": "folder-html",
    },
    "yazi_plugins": [
        "yazi-rs/plugins:jump-to-char",
        "uhs-robert/sshfs",
        "boydaihungst/gvfs",
        "uhs-robert/recycle-bin",
        "h-hg/yamb",
    ],
}


###########################################################
# ARCHINSTALL CONF
###########################################################
etc_files_to_write: dict[str, str] = {
    "etc/iwd/main.conf": dedent(
        """\
        [Network]
        NameResolvingService=resolvconf
        """
    ),
    "etc/apparmor/parser.conf": dedent(
        """\
        write-cache
        cache-loc /etc/apparmor/earlypolicy/
        Optimize=compress-fast
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
    "etc/xdg/user-dirs.defaults": dedent(
        """\
        DOCUMENTS=Desktop/Documents
        DESKTOP=Desktop
        MUSIC=Desktop/Music
        PICTURES=Desktop/Pictures
        BOOKS=Desktop/Books
        SCREENSHOTS=Desktop/Pictures/Screenshots
        GAMES=Games
        WALLPAPERS=Desktop/Pictures/Wallpapers
        VIDEOS=Desktop/Videos
        DOWNLOAD=Desktop/Downloads
        TEMPLATES=Desktop/Templates
        PRIVATE=Desktop/Private
        PUBLICSHARE=Desktop/Public
        PROJECTS="Lit"
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
    "etc/fuse.conf": dedent(
        """\
        user_allow_other
        """
    ),
    "etc/systemd/zram-generator.conf": dedent(
        """\
        [zram0]
        zram-size = min(ram / 2, 8192)
        compression-algorithm = zstd
        """
    ),
    "etc/sysctl.d/99-zram.conf": dedent(
        """\
        vm.swappiness = 180
        vm.watermark_boost_factor = 0
        vm.watermark_scale_factor = 125
        vm.page-cluster = 0

        vm.max_map_count = 2147483642
 
        # This action will speed up your boot and shutdown, because one less module is loaded.
        # Additionally disabling watchdog timers increases performance and lowers power consumption
        # Disable NMI watchdog
        kernel.nmi_watchdog = 0

        # To hide any kernel messages from the console
        kernel.printk = 3 3 3 3

        # Restricting access to kernel pointers in the proc filesystem
        kernel.kptr_restrict = 2

        # Increase netdev receive queue
        # May help prevent losing packets
        net.core.netdev_max_backlog = 4096
        """
    ),
    "etc/ssh/sshd_config.d/20-deny_root.conf": dedent("PermitRootLogin no"),
    "etc/modprobe.d/blacklist.conf": dedent(
        """\
        # Blacklist the Intel TCO Watchdog/Timer module
        blacklist iTCO_wdt
        # Blacklist the AMD SP5100 TCO Watchdog/Timer module (Required for Ryzen cpus)
        blacklist sp5100_tco"
        """
    ),
    "etc/modprobe.d/nvidia.conf": dedent(
        """\
        # Blacklist the Intel TCO Watchdog/Timer module
        options nvidia NVreg_UsePageAttributeTable=1 
        """
    ),
    "etc/udisks2/mount_options.conf": dedent(
        """\
        [defaults]
        # 'ntfs' signature, the new 'ntfs3' kernel driver
        ntfs:ntfs3_defaults=uid=$UID,gid=$GID
        ntfs:ntfs3_allow=uid=$UID,gid=$GID,umask,dmask,fmask,iocharset,discard,nodiscard,sparse,nosparse,hidden,nohidden,sys_immutable,showmeta,noshowmeta,prealloc,noprealloc,hide_dot_files,nohide_dot_files,windows_names,nocase,case
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
            "https://addons.mozilla.org/firefox/downloads/latest/return-youtube-dislikes/latest.xpi",
            "https://addons.mozilla.org/firefox/downloads/latest/leechblock-ng/latest.xpi",
            "https://addons.mozilla.org/firefox/downloads/latest/proton-pass/latest.xpi",
            "https://addons.mozilla.org/firefox/downloads/latest/firefox-color/latest.xpi",
            "https://addons.mozilla.org/firefox/downloads/latest/darkreader/latest.xpi",
            "https://addons.mozilla.org/firefox/downloads/latest/flagfox/latest.xpi",
            "https://addons.mozilla.org/firefox/downloads/latest/ublock-origin/latest.xpi",
        ],
        "Uninstall": [
            "google",
            "bing",
            "amazondotcom",
            "ebay",
            "twitter",
        ],
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
        "Remove": [
            "Bing",
            "Amazon.com",
            "eBay",
            "Twitter",
        ],
    },
}

pkgs: dict[str, list[str]] = {
    "base": [
        # HARDWARE
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
    ],
    "language": [
        "hunspell-en_us",
        "hyphen-en",
        "tesseract-data-eng",
    ],
    "chaotic_repo": [
        "apparmor.d-git",
        "cachyos-ananicy-rules-git",
        "downgrade",
        "floorp",
        "octopi",
        "paru",
        "systemd-oomd-defaults",
        "ocrmypdf",
    ],
    "printer": [
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
        "splix",
        "system-config-printer",
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
aur_pkgs: list[str] = [
    "wvkbd-deskintl",
]
