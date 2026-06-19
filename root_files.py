from textwrap import dedent

###########################################################
# ARCHINSTALL CONF
###########################################################
network_files: dict[str, str] = {
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
    "etc/resolvconf.conf": dedent(
        """\
        resolv_conf=/etc/resolv.conf
        name_servers="::1 127.0.0.1"
        """
    ),
    "etc/chrony.conf": dedent(
        """\
        server 0.arch.pool.ntp.org iburst
        server 1.arch.pool.ntp.org iburst
        server 2.arch.pool.ntp.org iburst
        server 3.arch.pool.ntp.org iburst
        driftfile /var/lib/chrony/drift
        rtcsync
        makestep 1.0 3
        leapseclist /usr/share/zoneinfo/leap-seconds.list
        logdir /var/log/chrony
        log measurements statistics tracking
        allow 127.0.0.1
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
}
etc_files_to_write: dict[str, str] = {
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
        """
    ),
    "etc/fuse.conf": dedent(
        """\
        user_allow_other
        """
    ),
    "etc/sysctl.d/99-sysctl.conf": dedent(
        """\
        vm.max_map_count = 2147483642
        # Disable NMI watchdog
        kernel.nmi_watchdog = 0
        # To hide any kernel messages from the console
        kernel.printk = 3 3 3 3
        # Restricting access to kernel pointers in the proc filesystem
        kernel.kptr_restrict = 2
        # May help prevent losing packets
        net.core.netdev_max_backlog = 4096
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
        GAMES=Desktop/Games
        WALLPAPERS=Desktop/Pictures/Wallpapers
        VIDEOS=Desktop/Videos
        DOWNLOAD=Desktop/Downloads
        TEMPLATES=Desktop/Templates
        PRIVATE=Desktop/Private
        PUBLICSHARE=Desktop/Public
        PROJECTS=Lit
        """
    ),
    "etc/conf.d/pacman-contrib": 'PACCACHE_ARGS="-k 2"\n',
    "etc/systemd/journald.conf.d/00-journal-size.conf": dedent(
        """\
        [Journal]
        SystemMaxUse=50M
        """
    ),
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
            dpi: 6000;
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
}
