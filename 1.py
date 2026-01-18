import subprocess
import getpass
import os
from pathlib import Path
import shlex
import shutil
import textwrap
from archinstall.lib.applications.application_handler import application_handler
from archinstall.lib.args import (
    ApplicationConfiguration,
    LocaleConfiguration,
    Password,
    User,
    arch_config_handler,
)
from archinstall.lib.configuration import ConfigurationOutput
from archinstall.lib.disk.filesystem import FilesystemHandler
from archinstall.lib.general import json
from archinstall.lib.global_menu import DiskLayoutConfigurationMenu
from archinstall.lib.installer import Bootloader, Installer, SysCommand
from archinstall.lib.interactions.general_conf import (
    PostInstallationAction,
    ask_post_installation,
)
from archinstall.lib.models.application import (
    Audio,
    AudioConfiguration,
    BluetoothConfiguration,
)
from archinstall.lib.models.device import DiskLayoutType, EncryptionType
from archinstall.lib.output import debug, error, info
from archinstall.tui import Tui

#################-CONF-#################
user_name = "nick"
my_host = "yulia"
my_contry = "Spain"
reflector_cmd = f"reflector --country {my_contry} --protocol http,https --latest 12 --sort rate --number 3 --save /etc/pacman.d/mirrorlist"
my_locale = LocaleConfiguration(kb_layout="us", sys_lang="en_US", sys_enc="UTF-8")
git_name = "acctux"
user_script = "d.py"
my_app = ApplicationConfiguration(
    BluetoothConfiguration(True), AudioConfiguration(Audio.PIPEWIRE)
)
sys_dir_cp = ["etc", "usr", "root"]
#################-PKGS-#################
pkgs = [
    #################-AMD-#################
    "mesa",
    "xf86-video-amdgpu",
    "xf86-video-ati",
    "vulkan-radeon",
    ################-NVIDIA-################
    "lib32-nvidia-utils",
    "libva-nvidia-driver",
    "libva-utils",
    "libxnvctrl",
    "nvidia-open",
    "nvidia-prime",
    "opencl-nvidia",
    ###############-Hardware-###############
    "ananicy-cpp",
    "android-file-transfer",
    "bluetui",
    "bluez-utils",  # for loggy
    "brightnessctl",
    "btop",
    "dosfstools",
    "exfatprogs",
    "ntfs-3g",
    "nvtop",
    "powertop",
    "realtime-privileges",
    "rocm-smi-lib",  # btop dependency for amd gpu
    "smartmontools",
    "tlp",
    "udisks2-btrfs",
    "usb_modeswitch",
    ###############-Network-################
    "bind",
    "deluge-gtk",
    "firewalld",
    "impala",
    "kdeconnect",
    "openresolv",
    "profile-sync-daemon",
    "protonmail-bridge",
    "sshfs",
    "wireguard-tools",
    "wireless-regdb",
    ##############-SQL Server-##############
    "dbeaver",
    "jdk-openjdk",
    "mariadb",
    ############-Language/Fonts-############
    "font-manager",
    "hunspell-en_us",
    "hyphen-en",
    "noto-fonts-emoji",
    "otf-firamono-nerd",
    "rofimoji",
    "tesseract-data-eng",
    "ttf-jetbrains-mono",
    #############-Multimedia-###############
    "cava",
    "evince",
    "gimp",
    "guvcview",
    "imv",
    "mpd",
    "mpd-mpris",
    "mpv-mpris",
    "pavucontrol",
    "playerctl",
    "rmpc",
    "yt-dlp",
    ###############-Coding-#################
    "luarocks",
    "lua-sec",
    "npm",
    "neovim-lspconfig",
    "rust",
    "uv",
    # Language Servers
    "bash-language-server",
    "clang",
    "lua-language-server",
    "pyright",
    "rust-analyzer",
    "systemd-language-server",
    "tailwindcss-language-server",
    "vscode-json-languageserver",
    "yaml-language-server",
    # Linters
    "ruff",
    # Tree sitter
    "tree-sitter-bash",
    "tree-sitter-cli",
    "tree-sitter-javascript",
    "tree-sitter-python",
    "tree-sitter-rust",
    ###############-Gaming-#################
    "gamemode",
    "gnome-chess",
    "gnuchess",
    "lib32-gamemode",
    "lib32-mangohud",
    "lutris",
    "mangohud",
    "mgba-qt",
    "steam",
    "umu-launcher",
    "vkd3d",
    "wine-mono",
    "wine-staging",
    "winetricks",
    #################-CLI-##################
    "alacritty",
    "aria2",
    "bash-completion",
    "bat-extras",
    "eza",
    "fd",
    "github-cli",
    "lazygit",
    "less",
    "man-pages",
    "mcfly",
    "pacman-contrib",
    "rebuild-detector",
    "ripgrep-all",
    "sd",
    "starship",
    "taskwarrior-tui",
    "tmuxp",
    "trash-cli",
    "yazi",
    "zoxide",
    "zsh-autocomplete",
    "zsh-completions",
    "zsh-syntax-highlighting",
    ##############-Hyprland-###############
    "capitaine-cursors",
    "fuzzel",
    "gnome-keyring",
    "gsimplecal",
    "hypridle",
    "hyprland",
    "hyprlock",
    "hyprshot",
    "hyprsunset",
    "kvantum",
    "nwg-clipman",
    "polkit-gnome",
    "qt5-wayland",
    "qt6-wayland",
    "satty",
    "seahorse",
    "snixembed",
    "swaync",
    "swayosd",
    "swww",
    "uwsm",
    "waybar",
    "xdg-desktop-portal-gnome",
    "xdg-desktop-portal-hyprland",
    #################-Office-###############
    "coin-or-mp",  # For LibreOffice Calc Solver
    "gnucash",
    "khal",
    "libreoffice-fresh",
    "thunderbird-i18n-en-us",
    "thunderbird-dark-reader",
    "thunderbird-ublock-origin",
    #################-Basic-###############
    "baobab",
    "bustle",
    "cdrtools",
    "d-spy",
    "featherpad",
    "gocryptfs",
    "logrotate",
    "ly",
    "nemo-fileroller",
    "plymouth",
    "qalculate-qt",
    "qt6ct",
    "qjournalctl",
    "unrar",
    "wl-clipboard",
    "wl-clip-persist",
    "xdg-user-dirs",
    #################-Python-##############
    "python-dbus-fast",  # loggy
    "python-imaplib2",  # emailcheck
    "python-mpd2",
    "python-mysqlclient",
    "python-pandas",
    "python-pygit2",
    "python-pyperclip",
    "python-systemd",  # loggy
    "python-tasklib",
    "python-wand",  # wallpaper script
]
#############-SERVICES-##############
services = [
    "ananicy-cpp",
    "tlp",
    "iwd",
    "ly@tty1",
    "named",
    "firewalld",
    "swayosd-libinput-backend",
    "systemd-networkd",
    "systemd-oomd",
    "systemd-timesyncd",
    "btrfs-scrub@-.timer",
    "btrfs-scrub@home.timer",
    "fstrim.timer",
    "logrotate.timer",
    "man-db.timer",
    "paccache.timer",
    "reflector.timer",
]
###########-DISABLE SERVICES-############
disable_svc = [
    "getty@tty1",
    "systemd-networkd-wait-online",
]
###########-GROUPS-############
groups = [
    "audio",
    "games",
    "gamemode",
    "log",
    "realtime",
    "storage",
    "video",
]
###########-CHAOTIC PKGS-############
chaos_pkgs = [
    "anki",
    "ayugram-desktop-git",
    "dxvk-mingw-git",
    "firedragon",
    "logiops",
    "neovim-symlinks",
    "ocrmypdf",
    "octopi",
    "paru",
    "proton-ge-custom-bin",
    "rpcs3-git",
]
###########-CUSTOM SVCS-############
custom_svc = [
    "loggy",
    "wireguard-list",
]
#################-MOUNT AND COPY KEYS-#################
wireguard_dir = "wireguard"
key_files = ["id_ed25519", "my_sec_gpg.asc", "pass.txt"]
key_dir = "keys"
usb_fs_type = "exfat"
min_size = "20G"
#################-SET VARS-#################
my_pass = getpass.getpass(prompt=f"Enter password for {user_name}: ")
script_dir = Path(__file__).resolve().parent


def run_cmd(cmd, check=False):
    try:
        info(f"Running: {cmd}")
        result = subprocess.run(cmd, text=True, shell=True, check=check)
        return result
    except subprocess.CalledProcessError as e:
        error(f"Failed: {cmd}\nExit code: {e.returncode}")
        return e


def check_usb_files(key_dir, key_files):
    missing_files = False
    for key_file in key_files:
        file_path = Path(f"/root/{key_dir}/{key_file}")
        if not file_path.exists():
            missing_files = True
            error(f"Needed: {file_path}")
    return missing_files


def string_to_float_size(size_str):
    if not size_str:
        return 0.0
    K = 1024
    M = 1024**2
    G = 1024**3
    T = 1024**4
    size_str = size_str.strip().upper()
    units = {"K": K, "M": M, "G": G, "T": T}
    return float(size_str[:-1]) * units.get(size_str[-1], 1.0)


def mnt_keys_partition(usb_mnt: Path, min_size: str, usb_fs_type: str):
    output = subprocess.check_output(
        ["lsblk", "-J", "-o", "NAME,SIZE,FSTYPE,MOUNTPOINT,TYPE"], text=True
    )
    data = json.loads(output)
    candidates = []

    def recurse(devices):
        for dev in devices:
            if (
                dev["type"] == "part"
                and dev.get("fstype") == usb_fs_type
                and dev.get("mountpoint") is None
                and string_to_float_size(dev["size"]) > string_to_float_size(min_size)
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

    recurse(data["blockdevices"])
    while True:
        print(f"{'No.':<5} {'Name':<8} {'Size':<8} {'FS Type':>8}")
        print("-" * 45)
        for i, (name, size, fstype) in enumerate(candidates, 1):
            print(f"{i:<5} {name:<8} {size:<8} {fstype:>8}")
        choice = input(f"Enter 1-{len(candidates)}: ").strip()
        if not choice.isdigit():
            error("Not a number.")
            continue
        choice_num = int(choice)
        if not (1 <= choice_num <= len(candidates)):
            error("Out of range.")
            continue
        selected_path = f"/dev/{candidates[choice_num - 1][0]}"
        break
    usb_mnt.mkdir(parents=True, exist_ok=True)
    try:
        run_cmd([f"mount {selected_path} {usb_mnt}"], check=True)
        return selected_path
    except subprocess.CalledProcessError as e:
        error(f"Failed to mount {selected_path}: {e}")


def usb_cp_keys(usb_mount, key_dir, key_files):
    print("Preparing to copy key files from USB...")
    dest_dir = Path.home() / key_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    for key_file in key_files:
        src = Path(usb_mount) / key_dir / key_file
        dest = dest_dir / key_file
        if not dest.exists():
            try:
                shutil.copy2(src, dest)
                info(f"Copied {key_file} to {dest}")
            except FileNotFoundError:
                error(f"Source file {src} not found on USB.")
        else:
            error(f"{key_file} already exists in {dest_dir}, skipping copy.")


def usb_cp_folder(usb_mount, folder_name):
    info("Preparing to copy folder from USB...")
    src_dir = Path(usb_mount) / folder_name
    dest_dir = Path.home() / folder_name
    if not dest_dir.exists():
        try:
            shutil.copytree(src_dir, dest_dir)
            info(f"Copied folder {folder_name} to {dest_dir}")
        except FileNotFoundError:
            error(f"Source folder {src_dir} not found on USB.")
        except Exception as e:
            error(f"Failed to copy folder {folder_name} from USB: {e}")


def unmount_partition(usb_mount: Path):
    result = run_cmd(["mountpoint", "-q", f"{usb_mount}"], check=False)
    if result.returncode == 0:
        run_cmd(["umount", f"{usb_mount}"], check=True)
        info(f"Unmounted USB from {usb_mount}.")
    if usb_mount.exists():
        try:
            Path(usb_mount).unlink()
        except OSError:
            pass


def mnt_cp_keys(
    key_dir: str | None = None,
    key_files: list[str] | None = None,
    wireguard_dir: str | None = None,
    usb_mnt=Path("/mnt/usb"),
    min_size=min_size,
    usb_fs_type=usb_fs_type,
):
    if key_dir and key_files or wireguard_dir:
        if check_usb_files(key_dir, key_files):
            mnt_keys_partition(usb_mnt, min_size, usb_fs_type)
            if key_dir and key_files:
                usb_cp_keys(usb_mnt, key_dir, key_files)
            if wireguard_dir:
                usb_cp_folder(usb_mnt, wireguard_dir)
            unmount_partition(usb_mnt)
    else:
        info("All required files present.")


#################-MAIN FUNCTIONS-#################
def run_cc(
    commands: list[str],
    mnt_point: Path,
    user_name: str | None = None,
    peek: bool = True,
) -> None:
    script_path = "var/tmp/user-commands.sh"
    chroot_path = mnt_point / script_path
    chroot_path.parent.mkdir(parents=True, exist_ok=True)
    with open(chroot_path, "w") as script:
        script.write("#!/bin/bash\n")
        if peek:
            script.write("set -e\n")
        for cmd in commands:
            script.write(cmd + "\n")
    os.chmod(chroot_path, 0o755)
    cmd = f"bash /{script_path}"
    if user_name:
        cmd = f"su - {user_name} -c {shlex.quote(cmd)}"
    SysCommand(f"arch-chroot -S {mnt_point} {cmd}")
    os.unlink(chroot_path)


def setup_alacritty_auto(
    mnt_point: Path,
    script_dir: Path,
    user_name: str,
    user_script: str,
) -> None:
    home = Path(f"home/{user_name}")
    run_script = home / user_script
    service_dir = home / ".config/systemd/user"
    service_name = f"{run_script.stem}.service"
    shutil.copy(script_dir / user_script, mnt_point / run_script)
    service_path = service_dir / service_name
    mnt_service_path = mnt_point / service_path
    mnt_service_path.parent.mkdir(parents=True, exist_ok=True)
    mnt_service_path.write_text(f"""[Unit]
Description=Open Alacritty running {user_script} on login
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/usr/bin/alacritty -e python /{run_script}
Restart=no

[Install]
WantedBy=graphical-session.target
""")
    mnt_service_path.chmod(0o644)
    info(f"wrote service to {mnt_service_path}")
    wants_dir = service_dir / "graphical-session.target.wants"
    run_cc(
        [
            f"mkdir -p /{wants_dir}",
            f"ln -sf /{service_path} /{wants_dir / service_name}",
        ],
        mnt_point,
        user_name,
    )


def sys_dots(mnt_point: Path, script_dir: Path, sys_dir_cp: list[str]):
    for dir_name in sys_dir_cp:
        source_dir = script_dir / dir_name
        target_dir = mnt_point / dir_name
        if not source_dir.exists():
            error(f"{source_dir} not found.")
            continue
        shutil.copytree(
            source_dir,
            target_dir,
            dirs_exist_ok=True,
            copy_function=shutil.copy2,
        )
        info(f"Copying {source_dir} -> {target_dir}")


def chaotic_repo(
    mnt_point: Path,
    chaos_pkgs: list[str],
):
    info("Setting up Chaotic-AUR repository.")
    chaotic_key_id = "3056513887B78AEB"
    key_serv = "keyserver.ubuntu.com"
    chaotic_web = " https://cdn-mirror.chaotic.cx/chaotic-aur"
    run_cc(
        [
            "pacman-key --init",
            f"pacman-key --recv-key {chaotic_key_id} --keyserver {key_serv}",
            f"pacman-key --lsign-key {chaotic_key_id}",
            f"pacman -U --noconfirm --needed {chaotic_web}/chaotic-keyring.pkg.tar.zst",
            f"pacman -U --noconfirm --needed {chaotic_web}/chaotic-mirrorlist.pkg.tar.zst",
        ],
        mnt_point,
    )
    pacman_conf = Path(f"{mnt_point}/etc/pacman.conf")
    section = "[chaotic-aur]"
    content = pacman_conf.read_text()
    if section not in content:
        with pacman_conf.open("a") as f:
            f.write("\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n")
    run_cc(
        ["pacman -Sy", f"pacman -S --noconfirm --needed {' '.join(chaos_pkgs)}"],
        mnt_point,
    )
    info("Chaotic-AUR repository added.")


def configure_sudo(user_name: str, mnt_point: Path, no_password: bool):
    sudoers_file = mnt_point / f"etc/sudoers.d/00_{user_name}"
    if no_password:
        sudoers_line = f"{user_name} ALL=(ALL:ALL) NOPASSWD:ALL"
        prt_val = "without password requirement"
    else:
        sudoers_line = f"{user_name} ALL=(ALL:ALL) ALL"
        prt_val = "with password requirement"
    sudoers_content = textwrap.dedent(f"""\
        {sudoers_line}
        Defaults    insults
        Defaults    passwd_tries=10
        Defaults    lecture=never
        Defaults    passwd_timeout=0
        Defaults    timestamp_timeout=20
        Defaults    timestamp_type=global
        Defaults    editor=/usr/sbin/nvim, !env_editor
    """)
    sudoers_file.parent.mkdir(parents=True, exist_ok=True)
    sudoers_file.write_text(sudoers_content.strip())
    os.chmod(sudoers_file, 0o440)
    info(f"Created {sudoers_file} {prt_val} for {user_name}")


def modify_fstab(mnt_point: Path) -> None:
    fstab = mnt_point / "etc" / "fstab"
    out = []
    for line in fstab.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            out.append(line)
            continue
        parts = line.split()
        if len(parts) < 6:
            out.append(line)
            continue
        opts = parts[3].split(",")
        for i, opt in enumerate(opts):
            if opt.startswith("fmask="):
                opts[i] = "fmask=0077"
            elif opt.startswith("dmask="):
                opts[i] = "dmask=0077"
        parts[3] = ",".join(opts)
        out.append("\t".join(parts))
    fstab.write_text("\n".join(out) + "\n")


def systemd_modify(
    mnt_point: Path,
    boot_opts: list[str] = ["quiet", "splash"],
) -> None:
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
    loader_file = mnt_point / "boot" / "loader" / "loader.conf"
    loader_file.write_text("default @saved\ntimeout 1\neditor no\n")
    os.chmod(loader_file, 0o644)
    info(f"Modified {loader_file}")


def config_pac_conf(mnt_point: Path | None = None, parallel_downloads: int = 10):
    pacman_content = textwrap.dedent(f"""\
        [options]
        HoldPkg     = pacman glibc
        Architecture = auto
        Color
        ILoveCandy
        ParallelDownloads = {parallel_downloads}
        DownloadUser = alpm
        SigLevel    = Required DatabaseOptional
        LocalFileSigLevel = Optional
        NoExtract = /etc/xdg/autostart/firewall-applet.desktop
        NoExtract = /usr/share/icons/capitaine-cursors/*

        [core]
        Include = /etc/pacman.d/mirrorlist

        [extra]
        Include = /etc/pacman.d/mirrorlist

        [multilib]
        Include = /etc/pacman.d/mirrorlist
    """)
    pacman_conf_path = Path("/etc/pacman.conf")
    if mnt_point:
        pacman_conf_path = mnt_point / "etc/pacman.conf"
    pacman_conf_path.write_text(pacman_content.strip())
    if mnt_point:
        run_cc(["pacman -Sy"], mnt_point)
    else:
        run_cmd(["pacman -Sy"], True)


def mv_usb_files(mnt_point: Path, keys_dir: str, wireguard_dir: str, user_home: str):
    src_dir = Path("/root") / keys_dir
    dest_dir = mnt_point / user_home / ".ssh"
    if not src_dir.is_dir():
        error(f"{src_dir} does not exist")
    shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)
    src_dir = Path("/root") / wireguard_dir
    dest_dir = mnt_point / "etc" / "wireguard"
    if not src_dir.is_dir():
        error(f"{src_dir} does not exist")
    shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)
    run_cc(
        [
            "chown -R root:root /etc/wireguard",
            "chmod 700 /etc/wireguard",
            "chmod 600 /etc/wireguard/*",
        ],
        mnt_point,
    )


##############################################################
def perform_installation(mountpoint=Path("/mnt")) -> None:
    config = arch_config_handler.config
    if not config.disk_config:
        error("No disk configuration provided")
        return
    disk_config = config.disk_config

    with Installer(mountpoint, disk_config, [], ["linux"]) as installation:
        if disk_config.config_type != DiskLayoutType.Pre_mount:
            installation.mount_ordered_layout()
        installation.sanity_check()
        if disk_config.config_type != DiskLayoutType.Pre_mount:
            if (
                disk_config.disk_encryption
                and disk_config.disk_encryption.encryption_type
                != EncryptionType.NoEncryption
            ):
                installation.generate_key_files()
        installation.setup_swap()
        installation.minimal_installation([], True, my_host, my_locale)
        installation.add_additional_packages("reflector")
        run_cc([reflector_cmd], mountpoint)
        installation.add_bootloader(Bootloader.Systemd)
        installation.copy_iso_network_config(enable_services=False)
        user = User(user_name, Password(my_pass), True)
        installation.create_users(user)
        if app_config := my_app:
            application_handler.install_applications(installation, app_config, [user])
        installation.add_additional_packages(pkgs)
        installation.set_timezone("US/Eastern")
        installation.enable_service(services)
        installation.genfstab()
        ############################################################
        user_home = f"home/{user_name}"
        svc_cmd = [
            f"usermod -a -G {','.join(groups)} {user_name}",
            f"systemctl enable {' '.join(custom_svc)}",
            f"systemctl disable {' '.join(disable_svc)}",
        ]
        user_cmds = [
            "xdg-user-dirs-update",
            f"mkdir -p /home/{user_name}/.cache/mpd/playlists /home/{user_name}/.cache/mpd/state",
        ]
        configure_sudo(user_name, mountpoint, no_password=False)
        config_pac_conf(mountpoint)
        chaotic_repo(mountpoint, chaos_pkgs)
        sys_dots(mountpoint, script_dir, sys_dir_cp)
        systemd_modify(mountpoint)
        run_cc(svc_cmd, mountpoint)
        run_cc(user_cmds, mountpoint, user_name)
        mv_usb_files(mountpoint, key_dir, wireguard_dir, user_home)
        setup_alacritty_auto(mountpoint, script_dir, user_name, user_script)
        cmd = [f"chown -R {user_name}:{user_name} /{user_home}"]
        run_cc(cmd, mountpoint)
        modify_fstab(mountpoint)
        ############################################################
        if not arch_config_handler.args.silent:
            with Tui():
                action = ask_post_installation()
            match action:
                case PostInstallationAction.EXIT:
                    pass
                case PostInstallationAction.REBOOT:
                    os.system("reboot")
                case PostInstallationAction.CHROOT:
                    try:
                        installation.drop_to_shell()
                    except Exception:
                        pass


def _minimal() -> None:
    mnt_cp_keys(key_dir, key_files, wireguard_dir)
    with Tui():
        disk_config = DiskLayoutConfigurationMenu(disk_layout_config=None).run()
        arch_config_handler.config.disk_config = disk_config
    config = ConfigurationOutput(arch_config_handler.config)
    config.write_debug()
    config.save()
    if not arch_config_handler.args.silent:
        aborted = False
        with Tui():
            if not config.confirm_config():
                debug("Installation aborted")
                aborted = True
        if aborted:
            exit(0)
    if arch_config_handler.config.disk_config:
        fs_handler = FilesystemHandler(arch_config_handler.config.disk_config)
        fs_handler.perform_filesystem_operations()
    run_cmd(reflector_cmd)
    config_pac_conf()
    perform_installation(Path("/mnt"))


_minimal()
