from pathlib import Path


HOME = Path.home()
###########################################################
# SYSTEM CONF
###########################################################
user_name = "nick"

# Host name, https://wiki.archlinux.org/title/Network_configuration#Set_the_hostname
hostname = "yulia"

# Reflector Options, https://wiki.archlinux.org/title/Reflector
# https://man.archlinux.org/listing/reflector
refl_options = [
    "--country US",
    "--protocol https",
    "--latest 15",
    "--sort rate",
    "--number 3",
]

# Dirs to be copied from the current git/script dir
sys_dir_to_cp = ["etc", "usr"]

# https://wiki.archlinux.org/title/Mkinitcpio#HOOKS
mkinit_hooks = [
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
]

# https://wiki.archlinux.org/title/Users_and_groups#Group_management
# storage group is defunct but we restore the function through udisk polkit rules
groups = [
    "adm",  # "Administration group, commonly used to give read access to protected logs. It has full read access to journal files."
    "games",  # https://aur.archlinux.org/packages/proton-ge-custom-bin?O=10, Proton requests to add
    "realtime",  # https://wiki.archlinux.org/title/Realtime_process_management
    "storage",  # https://lists.archlinux.org/archives/list/arch-dev-public@lists.archlinux.org/message/IEZCAXRIBMXGOMMW7C4Z3ADED32W24ZI/
    "video",  # "Access to video capture devices, 2D/3D hardware acceleration, framebuffer (X can be used without belonging to this group)."
]

# Four Main Networking parts for WiFi:
# DHCP - "Automatic network configuration is accomplished using Dynamic Host Configuration Protocol (DHCP). The network's DHCP server provides IP address(es), the default gateway IP address(es) and optionally also DNS name servers upon request from the DHCP client."
# Wireless Authentication - "There are mainly two options for Wi-Fi authentication on Linux: wpa_supplicant and iwd." https://wiki.archlinux.org/title/Network_configuration/Wireless#Authentication
# DNS - https://wiki.archlinux.org/title/Domain_name_resolution, https://wiki.archlinux.org/title/Domain_name_resolution#DNS_servers
# Openresolv- opens communication between the pieces, two variants depending on systemd-resolved usage
# If you don't use a VPN or you use systemd-resolved over BIND then probably unenecessary
# https://wiki.archlinux.org/title/Openresolv#Users
# https://wiki.archlinux.org/title/Openresolv#Subscribers
# https://wiki.archlinux.org/title/Systemd-resolved

# Mine:
# DHCP - systemd-networkd
# Wireless Authentication: IWD
# DNS: BIND (named)
# Openresolv-openresolv
# https://wiki.archlinux.org/title/Network_configuration#Network_managers
sys_services = [
    # Unsure if games group should be used but don't use gamemode pkg/group
    "ananicy-cpp",  # https://github.com/CachyOS/ananicy-rules/blob/master/README.md#gamemode--ananicy-cpp--bad-idea
    "bluetooth",  # https://wiki.archlinux.org/title/Bluetooth
    "tlp",  # https://wiki.archlinux.org/title/TLP
    "iwd",  # https://wiki.archlinux.org/title/Iwd
    "ly@tty1",  # https://wiki.archlinux.org/title/Ly
    "named",  # https://wiki.archlinux.org/title/BIND
    "firewalld",  # https://wiki.archlinux.org/title/Firewalld
    "swayosd-libinput-backend",  # https://github.com/ErikReider/SwayOSD
    "systemd-networkd",
    "systemd-oomd",  # https://wiki.archlinux.org/title/Improving_performance#Improving_system_responsiveness_under_low-memory_conditions
    "systemd-timesyncd",  # https://wiki.archlinux.org/title/Systemd-timesyncd
    "btrfs-scrub@-.timer",  # https://wiki.archlinux.org/title/Btrfs#Scrub
    "btrfs-scrub@home.timer",
    "fstrim.timer",  # https://wiki.archlinux.org/title/Solid_state_drive#Periodic_TRIM
    "logrotate.timer",  # https://wiki.archlinux.org/title/Logrotate
    "man-db.timer",  # https://wiki.archlinux.org/title/Man_page
    "paccache.timer",  # https://wiki.archlinux.org/title/Pacman#Cleaning_the_package_cache
    "reflector.timer",
    #####-Custom-####
    "loggy",
    "wireguard-list",
]

disable_svcs = [
    "getty@tty1",  # LY requires this be disabled
    "systemd-networkd-wait-online",
]


###########################################################
# USB PASED FILES CONF
###########################################################
usb_key_dir = "keys"
wireguard_dir = "wireguard"
ssh_key = "id_ed25519"
gpg_key = "my_sec_gpg.asc"
pass_manager_pass_path = HOME / ".ssh" / "pass.txt"
user_pass_file = "pass.py"
usb_cp_files = [ssh_key, gpg_key, pass_manager_pass_path.name, user_pass_file]
usb_fs_type = "exfat"
min_usb_size = "20G"

###########################################################
# USER CONF
###########################################################
git_dir = HOME / "Lit"
dot_dir = HOME / "Polka"
docs_dir = git_dir / "Docs"

enc_dir = HOME / "Desktop" / "Encrypted"
git_user = "acctux"
git_repos = [(git_dir, "Docs"), (git_dir, "noah"), (HOME, "Polka")]
dir_icons = [
    [HOME / "Desktop" / "Games", "folder-games.svg"],
    [git_dir, "folder-github.svg"],
    [git_dir / "Noah", "folder-root.svg"],
    [docs_dir, "folder-bookmark.svg"],
    [dot_dir, "folder-html.svg"],
    [enc_dir, "folder-locked.svg"],
]
hide_apps = [
    "avahi-discover.desktop",
    "bssh.desktop",
    "bvnc.desktop",
    "com.github.FontManager.FontViewer.desktop",
    "jshell-java-openjdk.desktop",
    "jconsole-java-openjdk.desktop",
    "khal.desktop",
    "nvtop.desktop",
    "octopi-cachecleaner.desktop",
    "octopi-notifier.desktop",
    "octopi-repoeditor.desktop",
    "org.gnome.Nautilus.desktop",
    "org.gnome.baobab.desktop",
    "org.kde.kdeconnect.nonplasma.desktop",
    "qv4l2.desktop",
    "qvidcap.desktop",
    "taskwarrior-tui.desktop",
    "uuctl.desktop",
    "xgps.desktop",
    "xgpsspeed.desktop",
]
