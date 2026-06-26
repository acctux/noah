import packages.pacman as pp
import packages.chaotic as pc

archinstall_json = {
    "app_config": {
        "audio_config": {
            "audio": "pipewire",
        },
        "bluetooth_config": {
            "enabled": True,
        },
        "firewall_config": {
            "firewall": "firewalld",
        },
        "fonts_config": {
            "fonts": [
                "noto-fonts-emoji",
                "ttf-liberation",
            ]
        },
        "power_management_config": {
            "power_management": "tuned",
        },
        "print_service_config": {
            "enabled": False,
        },
    },
    "archinstall-language": "English",
    "bootloader_config": {
        "bootloader": "Limine",
        "removable": False,
        "uki": False,
    },
    "hostname": "yulia",
    "kernels": [
        "linux",
    ],
    "locale_config": {
        "kb_layout": "us",
        "sys_enc": "UTF-8",
        "sys_lang": "en_US.UTF-8",
    },
    "optional_repositories": [
        "multilib",
    ],
    "network_config": {"type": "iso"},
    "ntp": True,
    "packages": (
        pp.base
        + pp.coding
        + pp.hardware
        + pp.hyprland
        + pp.monitoring
        + pp.network
        + pp.office
        + pp.personal
        + pc.base_chaotic_pkgs
    ),
    "pacman_config": {
        "color": True,
        "parallel_downloads": 10,
    },
    "profile_config": {
        "gfx_driver": "AMD / ATI (open-source)",
        "greeter": "ly",
        "profile": {"main": ["Minimal"]},
    },
    "services": [
        "iwd.service",
        "named.service",
        "systemd-networkd",
        "paccache.timer",
        "sysinfo",
    ],
    "swap": {
        "algorithm": "zstd",
        "enabled": True,
    },
    "timezone": "US/Eastern",
    "version": "4.3",
}
noah_json = {
    "parallel_downloads": 10,
    "logitech_mouse": True,
    "terminal": "kitty",
    "firefox_browser": "firedragon",
    "dots_git_user_repo": "acctux/polka",
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
    "mask_svcs": [
        "systemd-networkd-wait-online",
    ],
    "no_extracts": [
        "etc/xdg/autostart/firewall-applet.desktop",
        "usr/share/icons/capitaine-cursors/*",
    ],
    "copy_config": [
        {
            "type": "gpg",
            "source": "noahinstall",
            "targets": [{"dest": "~/.gnupg", "names": ["my_sec_gpg.asc"]}],
        },
        {
            "type": "auth_conf",
            "source": "noahinstall",
            "targets": [{"dest": "~/", "names": ["users.json"]}],
        },
        {
            "type": "ssh",
            "source": "noahinstall",
            "targets": [{"dest": "~/.ssh", "names": ["id_ed25519"]}],
        },
        {
            "type": "masterpass",
            "source": "noahinstall",
            "targets": [{"dest": "~/", "names": ["pass.txt"]}],
        },
        {
            "type": "wireguard",
            "source": "noahinstall",
            "targets": [{"dest": "/etc", "names": ["wireguard"]}],
        },
    ],
    "user_services": [
        {
            "source": "/usr/lib/systemd/user",
            "targets": {
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
        },
        {
            "source": ".config/systemd/user",
            "targets": {
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
                    "taskwarrior-notify.timer",
                    "taskwarrior-schedule.timer",
                    "wall.timer",
                ],
            },
        },
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
        "notmuch-emacs-mua",
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
    "sudo_defaults": [
        "insults",
        "passwd_tries=10",
        "lecture=never",
        "passwd_timeout=0",
        "timestamp_timeout=20",
        "pwfeedback",
        "timestamp_type=global",
        "editor=/usr/sbin/nvim, !env_editor",
    ],
    "git_repo_config": {
        "user_name": "acctux",
        "repos": {
            "noah": "Lit/noah",
            "polka": "Lit/polka",
            "docs": "Lit/Docs",
        },
    },
    "dotdirs_to_link": [
        "Lit/polka",
        "Lit/Docs/secdots",
    ],
    "encrypted_dir": "Desktop/Private",
    "dirs_icons": {
        "Desktop/Games": "folder-games",
        "Desktop/Videos": "folder-videos",
        "Desktop/Pictures": "folder-pictures",
        "Desktop/Private": "folder-locked",
        "Desktop/Books": "folder-book",
        "Desktop/Contacts": "addressbook",
        "Desktop/Calendar": "google-calendar",
        "Desktop/Mail": "folder-mail",
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
        "ndtoan96/ouch",
        "yazi-rs/plugins:full-border",
    ],
}
