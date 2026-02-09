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

###########################################################
import subprocess
from pathlib import Path
import json
import re
import shlex
import shutil
import textwrap
from utils import log, UserSrv, src_pass_file, ask_pass, run_cmd
from noah_conf.pkg import noextract_lines, pkgs, aur_pkgs
from noah_conf.conf import (
    usb_key_dir,
    user_name,
    usb_cp_files,
    hostname,
    refl_options,
    sys_lang,
    sys_enc,
    mkinit_hooks,
    wireguard_dir,
    timezone,
    sec_conf_file,
    kb_layout,
    sys_services,
    script_pwd_to_cp,
    disable_svcs,
    kernel,
    groups,
    min_usb_size,
    usb_fs_type,
)

###########################################################
# CONSTANTS
###########################################################
script_dir = Path(__file__).resolve().parent
user_home = f"home/{user_name}"
HOME = Path.home()


#########################
# USB CP
##########################
def usb_run_cmd(cmd, check=False):
    try:
        log.info(f"Running: {cmd}")
        result = subprocess.run(cmd, text=True, shell=True, check=check)
        return result
    except subprocess.CalledProcessError as e:
        log.error(f"Failed: {cmd}\nExit code: {e.returncode}")
        return e


def yes_no_prompt(prompt: str) -> bool:
    while True:
        response = input(f"{prompt} (y/n): ").strip().lower()
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'.")


def check_usb_files(key_dir, key_files) -> list[str]:
    missing_files = []
    for key_file in key_files:
        file_path = Path(f"/root/{key_dir}/{key_file}")
        if not file_path.exists():
            missing_files.append(file_path)
    log.warning(f"Needed: {', '.join(map(str, missing_files))}")
    return missing_files


def check_wireguard_dir():
    wireguard_dir = Path("/root/wireguard")
    if not wireguard_dir.is_dir():
        log.warning(f"Needed: {wireguard_dir} is not a directory")
        return True
    if not any(wireguard_dir.iterdir()):
        log.warning(f"Needed: {wireguard_dir} is empty")
        return True
    return False


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
            log.error("Not a number.")
            continue
        choice_num = int(choice)
        if not (1 <= choice_num <= len(candidates)):
            log.error("Out of range.")
            continue
        selected_path = f"/dev/{candidates[choice_num - 1][0]}"
        break
    usb_mnt.mkdir(parents=True, exist_ok=True)
    try:
        usb_run_cmd([f"mount {selected_path} {usb_mnt}"], check=True)
        return selected_path
    except subprocess.CalledProcessError as e:
        log.error(f"Failed to mount {selected_path}: {e}")


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
                log.info(f"Copied {key_file} to {dest}")
            except FileNotFoundError:
                log.error(f"Source file {src} not found on USB.")
        else:
            log.error(f"{key_file} already exists in {dest_dir}, skipping copy.")


def usb_cp_folder(usb_mount, folder_name):
    log.info("Preparing to copy folder from USB...")
    src_dir = Path(usb_mount) / folder_name
    dest_dir = Path.home() / folder_name
    if not dest_dir.exists():
        try:
            shutil.copytree(src_dir, dest_dir)
            log.info(f"Copied folder {folder_name} to {dest_dir}")
        except FileNotFoundError:
            log.error(f"Source folder {src_dir} not found on USB.")
        except Exception as e:
            log.error(f"Failed to copy folder {folder_name} from USB: {e}")


def unmount_partition(usb_mount: Path):
    usb_run_cmd(["umount", f"{usb_mount}"], check=True)
    log.info(f"Unmounted USB from {usb_mount}.")
    if usb_mount.exists():
        try:
            Path(usb_mount).unlink()
        except OSError:
            pass


def mnt_cp_keys(
    min_size: str,
    usb_fs_type: str,
    key_dir: str | None = None,
    key_files: list[str] | None = None,
    wireguard_dir: str | None = None,
    usb_mnt=Path("/mnt/usb"),
):
    if key_dir and key_files or wireguard_dir:
        if check_usb_files(key_dir, key_files):
            if yes_no_prompt(
                "Do you want to mount a USB drive to check for missing files?"
            ):
                mnt_keys_partition(usb_mnt, min_size, usb_fs_type)
                if key_dir and key_files:
                    usb_cp_keys(usb_mnt, key_dir, key_files)
                if wireguard_dir:
                    usb_cp_folder(usb_mnt, wireguard_dir)
                unmount_partition(usb_mnt)
    else:
        log.info("All required files present.")


#########################
# GNUPG
#########################
def run_chroot(
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
    chroot_path.chmod(0o755)
    cmd = f"bash /{script_path}"
    if user_name:
        cmd = f"su - {user_name} -c {shlex.quote(cmd)}"
    SysCommand(f"arch-chroot -S {mnt_point} {cmd}")
    chroot_path.unlink()


#########################
# USR_SVC
#########################
def enable_user_services(
    units: UserSrv | list[UserSrv],
    mnt_point: Path,
    user_name: str,
) -> None:
    if isinstance(units, UserSrv):
        units = [units]
    user_commands: list[str] = []
    base_dir = Path(f"/home/{user_name}/.config/systemd/user")
    for unit in units:
        for service in unit.services:
            target_dir = base_dir / f"{unit.target}.target.wants"
            user_commands.append(f"mkdir -p {target_dir}")
            src = unit.source_dir / service
            dst = target_dir / service
            user_commands.append(f"ln -sf {src} {dst}")
    run_chroot([f"chown -R {user_name}:{user_name} /home/{user_name}/"], mnt_point)
    run_chroot(user_commands, mnt_point, user_name)


def user_service(
    script_dir: str,
    mnt_point: Path,
    user_name: str,
    user_setup_script: str = "user_setup.py",
) -> None:
    serv_dir = f"home/{user_name}/.config/systemd/user"
    (mnt_point / serv_dir).mkdir(parents=True, exist_ok=True)
    run_script = f"/home/{user_name}/{script_dir}/{user_setup_script}"
    svc_name = f"{user_setup_script.partition('.')[0]}.service"
    (mnt_point / serv_dir / svc_name).write_text(f"""[Unit]
Description=Open Alacritty running {run_script} on login
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/usr/bin/kitty python {run_script}
Restart=no

[Install]
WantedBy=graphical-session.target
""")
    enable_user_services(
        units=UserSrv(
            target="graphical-session.target.wants",
            services=[svc_name],
            source_dir=Path(f"/{serv_dir}"),
        ),
        mnt_point=mnt_point,
        user_name=user_name,
    )


#########################
# PACMAN
#########################
def chaotic_repo(mnt_point: Path | None = None):
    log.info("Setting up Chaotic-AUR repository.")
    chaotic_key_id = "3056513887B78AEB"
    key_serv = "keyserver.ubuntu.com"
    chaotic_web = "https://cdn-mirror.chaotic.cx/chaotic-aur/"
    cmds_setup = [
        ["pacman-key", "--init"],
        ["pacman-key", "--recv-key", chaotic_key_id, "--keyserver", key_serv],
        ["pacman-key", "--lsign-key", chaotic_key_id],
        ["pacman", "-U", "--noconfirm", f"{chaotic_web}chaotic-keyring.pkg.tar.zst"],
        ["pacman", "-U", "--noconfirm", f"{chaotic_web}chaotic-mirrorlist.pkg.tar.zst"],
    ]
    cmds_update = ["pacman", "-Sy"]
    if mnt_point:
        for cmd in cmds_setup:
            run_chroot([" ".join(cmd)], mnt_point)
        pacman_conf = mnt_point / "etc/pacman.conf"
        run_chroot([" ".join(cmds_update)], mnt_point)
    else:
        for cmd in cmds_setup:
            run_cmd(cmd, check=True)
        pacman_conf = Path("/etc/pacman.conf")
        run_cmd(cmds_update, check=True)
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
    pacman_conf_path = Path("/etc/pacman.conf")
    if mnt_point:
        pacman_conf_path = mnt_point / "etc/pacman.conf"
    pacman_conf_path.write_text(pacman_content.strip())
    if mnt_point:
        run_chroot(["pacman -Sy"], mnt_point)
    else:
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


def configure_sudo(user_name: str, mnt_point: Path, pwd_require: bool = True):
    sudoers_file = mnt_point / f"etc/sudoers.d/00_{user_name}"
    if not pwd_require:
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


def copy_dir(dir: Path, dest: Path) -> None:
    src = Path("/root") / dir
    if not src.is_dir():
        log.error(f"{src} does not exist")
        return
    shutil.copytree(src, dest, dirs_exist_ok=True)


def apply_ownership(path: Path, owner: str) -> None:
    for p in path.rglob("*"):
        shutil.chown(p, user=owner, group=owner)
    shutil.chown(path, user=owner, group=owner)


def apply_permissions(path: Path, file_mode=0o600, dir_mode=0o700) -> None:
    for p in path.rglob("*"):
        if p.is_file():
            p.chmod(file_mode)
    path.chmod(dir_mode)


###########################################################
# Installer
###########################################################
def perform_installation(mountpoint=Path("/mnt")) -> None:
    config = arch_config_handler.config
    if not config.disk_config:
        log.error("No disk configuration provided")
        return
    disk_config = config.disk_config
    with Installer(mountpoint, disk_config, [], kernel) as installation:
        ############-Ensure User Pass Exists-##########
        if not (pw := src_pass_file(usb_key_dir, sec_conf_file)):
            pw = ask_pass(user_name)
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
            [], True, hostname, LocaleConfiguration(kb_layout, sys_lang, sys_enc)
        )
        ###############-Install reflector-###############
        installation.add_additional_packages("reflector")
        ref_cmd = f"reflector {' '.join(refl_options)} --save /etc/pacman.d/mirrorlist"
        log.info("Running reflector to update mirror list.")
        run_chroot([ref_cmd], mountpoint)
        ####################-System D-####################
        installation.add_bootloader(Bootloader.Systemd)
        modify_systemd(mountpoint)
        ###########-WiFi Pass and Time Zone-############
        installation.copy_iso_network_config()
        installation.set_timezone(timezone)
        #############-Pkg Management-###############
        config_pac_conf(mountpoint, 10, noextract_lines)
        chaotic_repo(mountpoint)
        installation.add_additional_packages(pkgs)
        #############-Etc Management-###############
        modify_mkinit(mountpoint, mkinit_hooks)
        sys_dots(mountpoint, script_dir, script_pwd_to_cp)
        copy_dir(Path("/root") / wireguard_dir, mountpoint / "etc" / "wireguard")
        installation.enable_service(sys_services)
        run_chroot([f"systemctl disable {' '.join(disable_svcs)}"], mountpoint)
        #############-User and Sudo-###############
        installation.create_users(User(user_name, Password(pw), True, groups))
        configure_sudo(user_name, mountpoint, pwd_require=False)
        usr_cmd = [
            f"sudo paru -S {' '.join(aur_pkgs)}",
            "xdg-user-dirs-update",
            f"mkdir -p /{user_home}/.cache/mpd",
        ]
        run_chroot(usr_cmd, mountpoint, user_name)
        #############-Copy Keys-#############
        copy_dir(Path(f"/root/{usb_key_dir}"), mountpoint / user_home / usb_key_dir)
        apply_ownership(mountpoint / user_home / usb_key_dir, user_name)
        apply_permissions(mountpoint / user_home / usb_key_dir)
        #############-Copy Script-#############
        copy_dir(script_dir, (mountpoint / user_home / script_dir.name))
        apply_ownership(mountpoint / user_home / script_dir.name, user_name)
        #############-Own Everything and User Services-###############
        # Untested
        # usr_cmd = [
        #     f"git clone https://github.com/acctux/polka.git /home/{user_name}/Folka",
        #     "hyprctl reload "
        #     f"python /home/{user_name}/Folka/local/bin/dotsync/dotsync.py",
        # ]
        # run_chroot(usr_cmd, mountpoint, user_name, peek=False)
        user_service(script_dir.name, mountpoint, user_name, user_home)
        configure_sudo(user_name, mountpoint, pwd_require=True)
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
    mnt_cp_keys(min_usb_size, usb_fs_type, usb_key_dir, usb_cp_files, wireguard_dir)
    ref_cmd = ["reflector", *refl_options, "--save", "/etc/pacman.d/mirrorlist"]
    run_cmd(ref_cmd)
    config_pac_conf(None, 10, noextract_lines)
    chaotic_repo()
    perform_installation(Path("/mnt"))


_minimal()
