import time
from archinstall.lib.configuration import ConfigurationOutput
from archinstall.lib.disk.filesystem import FilesystemHandler
from archinstall.lib.global_menu import DiskLayoutConfigurationMenu
from archinstall.lib.installer import Bootloader, Installer, SysCommand
from archinstall.lib.models.device import DiskLayoutType, EncryptionType
from archinstall.tui import Tui
from archinstall.lib.interactions.general_conf import (
    PostInstallationAction,
    ask_post_installation,
)
from archinstall.lib.args import (
    LocaleConfiguration,
    Password,
    User,
    arch_config_handler,
)
import subprocess
from pathlib import Path
import json
import re
import shlex
import shutil
import textwrap
from utils import (
    UserSrv,
    src_pass_file,
    ask_pass,
    run_cmd,
    get_logger,
    copy_file,
    copy_dir,
    ind_key_permission,
)
import sys_conf as sc

###########################################################
# CONSTANTS
###########################################################
script_d = Path(__file__).resolve().parent
user_home = f"home/{sc.user_name}"
HOME = Path.home()
mountpoint = Path("/mnt/arch")
log = get_logger("Noah")


def yes_no(prompt: str) -> bool:
    while True:
        response = input(f"{prompt} (y/n): ").strip().lower()
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'.")


def check_missing(
    key_dir: str | None = None,
    key_files: list[str] | None = None,
    wireguard_dir: str | None = None,
) -> list[str]:
    log = get_logger("Needed")
    missing_files = []
    if key_files:
        for key in key_files:
            key_path = HOME / f"{key_dir}/{key}"
            if not key_path.exists():
                missing_files.append(key)
    if wireguard_dir and not (HOME / wireguard_dir).is_dir():
        missing_files.append(wireguard_dir)
    if missing_files:
        log.warning(", ".join(missing_files))
    return missing_files


def get_device(usb_mnt: Path, min_gb=20, usb_fs_type="ext4") -> str:
    data = json.loads(
        subprocess.check_output(
            ["lsblk", "-J", "-o", "NAME,SIZE,FSTYPE,MOUNTPOINT,TYPE"], text=True
        )
    )
    candidates = []
    selected_path = ""

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

    recurse(data["blockdevices"])
    while True:
        get_logger("").info(f"{'No.':<5} {'Name':<8} {'Size':<8} {'FS Type':>8}")
        get_logger("").info("-" * 45)
        for i, (name, size, fstype) in enumerate(candidates, 1):
            get_logger("").info(f"{i:<5} {name:<8} {size:<8} {fstype:>8}")
        choice = input(f"Enter 1-{len(candidates)}: ").strip()
        if not choice.isdigit() or not (1 <= int(choice) <= len(candidates)):
            log.error("Out of range.")
            continue
        selected_path = f"/dev/{candidates[int(choice) - 1][0]}"
        break
    return selected_path


def usb_cp_keys(usb_mount: Path, key_dir, key_files):
    (HOME / key_dir).mkdir(parents=True, exist_ok=True)
    for key in key_files:
        copy_file(usb_mount / key_dir / key, HOME / key_dir / key)


def umount_usb(usb_mount: Path):
    cmd = ["umount", str(usb_mount)]
    run_cmd(cmd, check=True, shell=True)
    log.info(f"Unmounted USB from {usb_mount}.")
    if usb_mount.exists():
        try:
            shutil.rmtree(usb_mount)
            usb_mount.unlink(missing_ok=True)
        except OSError:
            pass


def mnt_cp_keys(
    key_dir: str | None = None,
    key_files: list[str] | None = None,
    wireguard_dir: str | None = None,
    min_size: str = "20GB",
    usb_fs_type: str = "ext4",
    usb_mnt=Path("/mnt/usb"),
):
    if usb_mnt.is_mount():
        if yes_no("Found /mnt/usb, try unmount?"):
            umount_usb(usb_mnt)
    if key_dir and key_files or wireguard_dir:
        if check_missing(key_dir, key_files, wireguard_dir):
            if yes_no("Mount USB to copy missing files?"):
                selected_path = get_device(usb_mnt)
                usb_mnt.mkdir(parents=True, exist_ok=True)
                cmd = [f"mount -t ext4 -o ro {selected_path} {usb_mnt}"]
                run_cmd(cmd, check=True, shell=True)
                time.sleep(1)
                if key_dir and key_files:
                    usb_cp_keys(usb_mnt, key_dir, key_files)
                if wireguard_dir:
                    if not (HOME / wireguard_dir).exists():
                        copy_dir(usb_mnt / wireguard_dir, HOME / wireguard_dir)
                if yes_no("Unmount USB?"):
                    umount_usb(usb_mnt)
    else:
        log.info("All required files present.")


#########################
# GNUPG
#########################
def run_chroot(
    commands: list[str], mnt_point: Path, user_name: str | None = None, peek=True
):
    script_path = "var/tmp/user-commands.sh"
    chroot_path = mnt_point / script_path
    chroot_path.parent.mkdir(parents=True, exist_ok=True)
    with open(chroot_path, "w") as script:
        script.write("#!/bin/bash\n")
        if peek:
            script.write("set -e\n")
        for cmd in commands:
            script.write(cmd + "\n")
    chroot_path.chmod(0o755)
    cmd = f"bash /{script_path}"
    if user_name:
        cmd = f"su - {user_name} -c {shlex.quote(cmd)}"
    SysCommand(f"arch-chroot -S {mnt_point} {cmd}")
    chroot_path.unlink()


#########################
# USR_SVC
#########################
def enable_user_serv(units: UserSrv | list[UserSrv], mnt_point: Path, user_name: str):
    if isinstance(units, UserSrv):
        units = [units]
    user_commands: list[str] = []
    base_dir = Path(f"/home/{user_name}/.config/systemd/user")
    for unit in units:
        for service in unit.services:
            target_dir = base_dir / f"{unit.target}.target.wants"
            user_commands.append(f"mkdir -p {target_dir}")
            src = Path(unit.source) / service
            dst = target_dir / service
            user_commands.append(f"ln -sf {src} {dst}")
    run_chroot([f"chown -R {user_name}:{user_name} /home/{user_name}/"], mnt_point)
    run_chroot(user_commands, mnt_point, user_name)


def user_service(
    mnt_point: Path,
    user_name: str,
    user_script="user_setup.py",
    script_dir: str = Path(__file__).resolve().parent.name,
):
    dir = f"home/{user_name}/.config/systemd/user"
    (mnt_point / dir).mkdir(parents=True, exist_ok=True)
    run_script = f"/home/{user_name}/{script_dir}/{user_script}"
    name = f"{user_script.rsplit('.', 1)[0]}.service"
    service_content = textwrap.dedent(f"""\
    [Unit]
    Description=Open Alacritty running {run_script} on login
    After=graphical-session.target

    [Service]
    Type=oneshot
    ExecStart=/usr/bin/kitty python {run_script}
    Restart=no

    [Install]
    WantedBy=graphical-session.target
    """)
    (mnt_point / dir / name).write_text(service_content)
    unit = UserSrv(source=f"/{dir}", target="graphical-session", services=[name])
    enable_user_serv(unit, mnt_point, user_name)


#########################
# PACMAN
#########################
def chaotic_repo(mnt_point: Path | None = None):
    log.info("Setting up Chaotic-AUR repository.")
    key_serv = "keyserver.ubuntu.com"
    chaotic_web = "https://cdn-mirror.chaotic.cx/chaotic-aur/"
    cmds_setup = [
        ["pacman-key", "--init"],
        ["pacman-key", "--recv-key", "3056513887B78AEB", "--keyserver", key_serv],
        ["pacman-key", "--lsign-key", "3056513887B78AEB"],
        ["pacman", "-U", "--noconfirm", f"{chaotic_web}chaotic-keyring.pkg.tar.zst"],
        ["pacman", "-U", "--noconfirm", f"{chaotic_web}chaotic-mirrorlist.pkg.tar.zst"],
    ]
    if mnt_point:
        for cmd in cmds_setup:
            run_chroot([" ".join(cmd)], mnt_point)
        pacman_conf = mnt_point / "etc/pacman.conf"
        run_chroot(["pacman -Sy"], mnt_point)
    else:
        for cmd in cmds_setup:
            run_cmd(cmd, check=True)
        pacman_conf = Path("/etc/pacman.conf")
        run_cmd(["pacman", "-Sy"], check=True)
    section = "[chaotic-aur]"
    content = pacman_conf.read_text()
    if section not in content:
        with pacman_conf.open("a") as f:
            f.write("\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n")


def config_pac_conf(
    mnt_point: Path | None,
    parallel_downloads: int = 10,
    noextract_lines: list[str] = [],
):
    pacman_content = textwrap.dedent(f"""\
        [options]
        HoldPkg = pacman glibc
        Architecture = auto
        Color
        ILoveCandy
        ParallelDownloads = {parallel_downloads}
        DownloadUser = alpm
        SigLevel    = Required DatabaseOptional
        LocalFileSigLevel = Optional
        {"\n".join(noextract_lines)}

        [core]
        Include = /etc/pacman.d/mirrorlist

        [extra]
        Include = /etc/pacman.d/mirrorlist

        [multilib]
        Include = /etc/pacman.d/mirrorlist
    """)
    if mnt_point:
        (mnt_point / "etc/pacman.conf").write_text(pacman_content.strip())
        run_chroot(["pacman -Sy"], mnt_point)
    else:
        Path("/etc/pacman.conf").write_text(pacman_content.strip())
        run_cmd(["pacman", "-Sy"], True)


#########################
# ETC/BOOT
#########################
def sys_dots(mnt_point: Path, script_dir: Path, sys_dir_cp: list[str]):
    for dir_name in sys_dir_cp:
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


def configure_sudo(user_name: str, mnt_point: Path, passwordless_sudo=True):
    sudoers_file = mnt_point / f"etc/sudoers.d/00_{user_name}"
    if passwordless_sudo:
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
    sudoers_file.write_text(sudoers_content.strip())
    sudoers_file.chmod(0o440)
    log.info(f"Created {sudoers_file} {prt_val} for {user_name}")


def modify_systemd(mnt_point: Path, boot_opts: list[str] = ["quiet", "splash"]) -> None:
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
    loader_file.chmod(0o644)
    log.info(f"Modified {loader_file}")


# def modify_fstab(mnt_point: Path) -> None:
#     fstab_path = mnt_point / "etc" / "fstab"
#     content = fstab_path.read_text()
#     # ^(?!#) = ignore comments, .*? = match any characters up to the \option\
#     # \bfmask=\d+  → word boundary, then  digits
#     content = re.sub(r"^(?!#).*?\bfmask=\d+", "fmask=0077", content, flags=re.MULTILINE)
#     content = re.sub(r"^(?!#).*?\bdmask=\d+", "dmask=0077", content, flags=re.MULTILINE)
#     fstab_path.write_text(content)


def modify_mkinit(mnt_point: Path, hooks: list[str]):
    mkinitcpio_conf_path = f"{mnt_point}/etc/mkinitcpio.conf"
    with open(mkinitcpio_conf_path, "r+") as mkinit:
        content = mkinit.read()
        content = re.sub(r"\nHOOKS=.*", f"\nHOOKS=({' '.join(hooks)})", content)
        mkinit.seek(0)
        mkinit.truncate()
        mkinit.write(content)


def install_icon_theme(
    mnt_point: Path, old="#ffffff", new="#F4F5F6", icon_dir="/usr/share/icons"
):
    tmp = "/tmp/icons"
    run_chroot(
        [
            f"git clone https://github.com/vinceliuice/WhiteSur-icon-theme.git {tmp} {icon_dir}",
            f"bash {tmp}/install.sh",
        ],
        mnt_point,
        peek=True,
    )
    icon_path = mnt_point / icon_dir
    for svg in [p for p in icon_path.rglob("*.svg") if "scalable" not in p.parts]:
        text = svg.read_text()
        if old in text:
            svg.write_text(text.replace(old, new))
    if (icon_path / "WhiteSur-light").exists():
        shutil.rmtree(icon_path / "WhiteSur-light")


def hide_apps(mnt_point: Path, username: str, applications: list[str]) -> None:
    system_dir = mnt_point / "/usr/share/applications"
    user_dir = mnt_point / "home" / username / ".local" / "share" / "applications"
    user_dir.mkdir(parents=True, exist_ok=True)
    for app in applications:
        if not app.endswith(".desktop"):
            app = f"{app}.desktop"
        system_file = system_dir / app
        if system_file.exists():
            hide_entry = "[Desktop Entry]\nHidden=true\nNoDisplay=true\n"
            (user_dir / app).write_text(hide_entry)
        else:
            log.info("Skipping %s, not found", system_file)


def clone_dots_to_skel(mnt_point: Path, git_name: str, dots_git: str):
    skel_tmp = Path.home() / dots_git
    cmd = [
        "git",
        "clone",
        f"https://github.com/{git_name}/{dots_git}.git",
        f"{skel_tmp}",
    ]
    run_cmd(cmd, True)
    shutil.rmtree(skel_tmp / ".git")
    for p in skel_tmp.iterdir():
        p.rename(p.parent / ("." + p.name))
    copy_dir(skel_tmp, mnt_point / "etc" / "skel")


def process_copy(mnt_point, user_name: str, to_cp):
    chown_ls = []
    for folder, files_list in to_cp:
        mnt_dir = mnt_point / "home" / user_name / folder
        for f in files_list:
            dest = mnt_dir / f
            copy_file(Path(f"/root/{sc.usb_key_dir}/{f}"), dest)
            chown_line = f"chown {user_name}:{user_name} {dest.relative_to(mnt_point)}"
            chown_ls.append(chown_line)
            ind_key_permission(dest / f)
        ind_key_permission(dest / f)
    return chown_ls


###########################################################
# Installer
###########################################################
def perform_installation(mountpoint) -> None:
    config = arch_config_handler.config
    if not config.disk_config:
        log.error("No disk configuration provided")
        return
    disk_config = config.disk_config
    with Installer(mountpoint, disk_config, kernels=sc.kernel) as installation:
        ############-Ensure User Pass Exists-##########
        if not (pw := src_pass_file(sc.usb_key_dir, sc.my_pass)):
            pw = ask_pass(sc.user_name)
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
        installation.minimal_installation(
            hostname=sc.hostname,
            locale_config=LocaleConfiguration(sc.kb_layout, sc.sys_lang, sc.sys_enc),
        )
        ###############-Install reflector-###############
        installation.add_additional_packages("reflector")
        log.info("Updating mirror list.")
        options = sc.refl_options + ["--save /etc/pacman.d/mirrorlist"]
        run_chroot([f"reflector {' '.join(options)}"], mountpoint)
        ####################-Systemd-####################
        installation.add_bootloader(Bootloader.Systemd)
        modify_systemd(mountpoint)
        ###########-WiFi Pass and Time Zone-############
        installation.copy_iso_network_config()
        installation.set_timezone(sc.timezone)
        #############-Pkg Management-###############
        config_pac_conf(mountpoint, 10, sc.noextract_lines)
        chaotic_repo(mountpoint)
        installation.add_additional_packages(
            sc.amd_pkgs
            + sc.nvidia_pkgs
            + sc.pipewire_pkgs
            + sc.hardware_pkgs
            + sc.basic_pkgs
            + sc.android_pkgs
            + sc.network_pkgs
            + sc.lang_pkgs
            + sc.media_pkgs
            + sc.hyprland_pkgs
            + sc.office_pkgs
            + sc.coding_pkgs
            + sc.mariadb_pkgs
            + sc.pydep_pkgs
            + sc.gaming_pkgs
            + sc.chaotic_pkgs
        )
        #############-Etc Management-###############
        modify_mkinit(mountpoint, sc.mkinit_hooks)
        sys_dots(mountpoint, script_d, sc.script_pwd_to_cp)
        copy_dir(Path("/root") / sc.wireguard_dir, mountpoint / "etc" / "wireguard")
        installation.enable_service(sc.sys_services + sc.custom_services)
        run_chroot([f"systemctl disable {' '.join(sc.disable_svcs)}"], mountpoint)
        #############-User and Sudo-###############
        clone_dots_to_skel(mountpoint, sc.git_name, sc.dots_git)
        installation.create_users(User(sc.user_name, Password(pw), True, sc.groups))
        configure_sudo(sc.user_name, mountpoint, passwordless_sudo=False)
        run_chroot(
            [
                f"paru -S --noconfirm --needed {' '.join(sc.aur_pkgs)}",
                "xdg-user-dirs-update",
                f"mkdir -p /{user_home}/.cache/mpd",
            ],
            mountpoint,
            sc.user_name,
        )
        run_chroot(
            ["mariadb-install-db --user=mysql --basedir=/usr --datadir=/var/lib/mysql"],
            mountpoint,
            peek=False,
        )
        hide_apps(mountpoint, sc.user_name, sc.hide_apps)
        run_chroot(
            [f"chown -R {sc.user_name} /home/{sc.user_name}/.local/share/applications"],
            mountpoint,
            sc.user_name,
        )
        #############-Copy Keys and Script Dir-#############
        copy_dir(script_d, (mountpoint / user_home / script_d.name))
        installation.chown(sc.user_name, str(mountpoint / user_home / script_d.name))
        to_cp = (
            (".ssh", [sc.ssh_key]),
            (".gnupg", [sc.gpg_key]),
            (f"{script_d.name}", [sc.pass_pass]),
        )
        process_copy(mountpoint, sc.user_name, to_cp)
        user_service(mountpoint, sc.user_name)
        enable_user_serv(
            [sc.usr_srv_default, sc.usr_srv_sockets, sc.usr_srv_graphical],
            mountpoint,
            sc.user_name,
        )
        install_icon_theme(mountpoint)
        configure_sudo(sc.user_name, mountpoint, passwordless_sudo=True)
        #############-Own Everything and User Services-###############
        installation.genfstab()
        # modify_fstab(mountpoint)
        if not arch_config_handler.args.silent:
            with Tui():
                action = ask_post_installation()
            match action:
                case PostInstallationAction.EXIT:
                    pass
                case PostInstallationAction.REBOOT:
                    subprocess.run(["reboot"], check=True)
                case PostInstallationAction.CHROOT:
                    try:
                        installation.drop_to_shell()
                    except Exception:
                        pass


###########################################################
# Main
###########################################################
def _minimal() -> None:
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
                log.warning("Installation aborted")
                aborted = True
        if aborted:
            exit(0)
    if arch_config_handler.config.disk_config:
        fs_handler = FilesystemHandler(arch_config_handler.config.disk_config)
        fs_handler.perform_filesystem_operations()
    ref_cmd = ["reflector", *sc.refl_options, "--save", "/etc/pacman.d/mirrorlist"]
    run_cmd(ref_cmd)
    config_pac_conf(None, 10, sc.noextract_lines)
    chaotic_repo()
    perform_installation(mountpoint)


mnt_cp_keys(sc.usb_key_dir, sc.usb_cp_files, sc.wireguard_dir)
_minimal()
