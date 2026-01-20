import subprocess
from pathlib import Path
import shlex
import shutil
import getpass
import textwrap
from archinstall.lib.args import (
    Password,
    User,
    arch_config_handler,
)
from archinstall.lib.configuration import ConfigurationOutput
from archinstall.lib.disk.filesystem import FilesystemHandler
from archinstall.lib.global_menu import DiskLayoutConfigurationMenu
from archinstall.lib.installer import Bootloader, Installer, SysCommand
from archinstall.lib.interactions.general_conf import (
    PostInstallationAction,
    ask_post_installation,
)
from archinstall.lib.models.device import DiskLayoutType, EncryptionType
from archinstall.tui import Tui
import noah_lib.conf as nl
from noah_lib.usb_mnt_cp import mnt_cp_keys
from noah_lib.utils import (
    run_cmd,
    get_logger,
)
from noah_lib.conf import UserSrv

###########-SET VARS-###########
script_dir = Path(__file__).resolve().parent
user_home = f"home/{nl.user_name}"
log = get_logger("Noah")


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
    chroot_path.chmod(0o755)
    cmd = f"bash /{script_path}"
    if user_name:
        cmd = f"su - {user_name} -c {shlex.quote(cmd)}"
    SysCommand(f"arch-chroot -S {mnt_point} {cmd}")
    chroot_path.unlink()


def sys_dots(mnt_point: Path, script_dir: Path, sys_dir_cp: list[str]):
    for dir_name in sys_dir_cp:
        source_dir = script_dir.parent / dir_name
        target_dir = mnt_point / dir_name
        if not source_dir.exists():
            log.error(f"{source_dir} not found.")
            continue
        shutil.copytree(
            source_dir, target_dir, dirs_exist_ok=True, copy_function=shutil.copy2
        )


def chaotic_repo(mnt_point: Path | None = None):
    log.info("Setting up Chaotic-AUR repository.")
    chaotic_key_id = "3056513887B78AEB"
    key_serv = "keyserver.ubuntu.com"
    chaotic_web = "https://cdn-mirror.chaotic.cx/chaotic-aur"
    cmds_setup = [
        ["pacman-key", "--init"],
        ["pacman-key", "--recv-key", chaotic_key_id, "--keyserver", key_serv],
        ["pacman-key", "--lsign-key", chaotic_key_id],
        [
            "pacman",
            "-U",
            "--noconfirm",
            "--needed",
            f"{chaotic_web}/chaotic-keyring.pkg.tar.zst",
        ],
        [
            "pacman",
            "-U",
            "--noconfirm",
            "--needed",
            f"{chaotic_web}/chaotic-mirrorlist.pkg.tar.zst",
        ],
    ]
    cmds_update = ["pacman", "-Sy"]
    if mnt_point:
        for cmd in cmds_setup:
            run_cc([" ".join(cmd)], mnt_point)
        pacman_conf = mnt_point / "etc/pacman.conf"
        run_cc([" ".join(cmds_update)], mnt_point)
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
    loader_file.chmod(0o644)
    log.info(f"Modified {loader_file}")


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
        run_cmd(["pacman", "-Sy"], True)


def copy_dir(dir: str, dest: Path, set_root: bool = False):
    src = Path("/root") / dir
    if not src.is_dir():
        log.error(f"{src} does not exist")
    shutil.copytree(src, dest, dirs_exist_ok=True)
    if set_root:
        for path in dest.rglob("*"):
            shutil.chown(path, user="root", group="root")
            if path.is_file():
                path.chmod(0o600)
        shutil.chown(dest, user="root", group="root")
        dest.chmod(0o700)


def copy_scripts(
    mnt_point: Path,
    script_dir: Path,
    lib_dir: str,
    user_name: str,
    user_script: str,
    dest: Path | None = None,
):
    if dest is None:
        dest = mnt_point / f"/home/{user_name}"
    src_dir = script_dir / lib_dir
    if not src_dir.is_dir():
        raise FileNotFoundError(f"{src_dir} does not exist")
    shutil.copytree(src_dir, dest, dirs_exist_ok=True)
    src_file = script_dir / user_script
    if not src_file.is_file():
        raise FileNotFoundError(f"{src_file} does not exist")
    shutil.copy2(src_file, dest / src_file.name)
    for path in dest.rglob("*"):
        if path.is_symlink():
            continue
        shutil.chown(path, user=user_name)
        if path.is_dir():
            path.chmod(0o755)
        else:
            path.chmod(0o644)
    shutil.chown(dest, user=user_name)
    dest.chmod(0o755)


def enable_user_services(
    user_home: str,
    units: UserSrv | list[UserSrv],
    mnt_point: Path,
    user_name: str,
) -> None:
    units = [units] if isinstance(units, UserSrv) else units
    commands: list[str] = []
    for unit in units:
        target_path = Path(user_home) / ".config/systemd/user" / unit.target
        commands.append(f"mkdir -p {target_path}")
        for service in unit.services:
            unit_file = unit.source_dir / service
            commands.append(f"ln -sf {unit_file} {target_path / service}")
    run_cc(commands, mnt_point, user_name)


def user_service_file(
    usr: str,
    user_setup_script: str,
    mnt_point: Path | None = None,
) -> Path:
    home = Path(f"/home/{usr}") if mnt_point is None else mnt_point / "home" / usr
    run_script = home / user_setup_script
    service_dir = home / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True)
    svc_name = f"{run_script.stem}.service"
    service_path = service_dir / svc_name
    service_path.write_text(f"""[Unit]
Description=Open Alacritty running {run_script} on login
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/usr/bin/alacritty -e python {run_script}
Restart=no

[Install]
WantedBy=graphical-session.target
""")
    return service_path


def get_password(usb_key_dir: str, key_files: list[str], user_name: str) -> str:
    key_path = Path("/root") / usb_key_dir / key_files[3]

    def prompt_password() -> str:
        while True:
            pwd1 = getpass.getpass(f"Enter password for {user_name}: ")
            pwd2 = getpass.getpass("Re-enter password: ")
            if not pwd1 or pwd1 != pwd2:
                print("Try again.")
                continue
            return pwd1

    if key_path.exists():
        try:
            pw = key_path.read_text().strip()
            log.info(f"Password loaded from '{key_path}'.")
            return pw
        except Exception as e:
            log.error(f"Failed to read password from '{key_path}': {e}")
    log.warning(f"Password file '{key_path}' not found or unreadable.")
    return prompt_password()


##############################################################
def perform_installation(mountpoint=Path("/mnt")) -> None:
    config = arch_config_handler.config
    if not config.disk_config:
        log.error("No disk configuration provided")
        return
    disk_config = config.disk_config

    with Installer(mountpoint, disk_config, [], ["linux"]) as installation:
        pw = get_password(nl.usb_key_dir, nl.key_files, nl.user_name)
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
        installation.minimal_installation([], True, nl.host, nl.my_locale)
        installation.add_additional_packages("reflector")
        ref_cmd = [
            f"reflector {' '.join(nl.reflector_opts)} --save /etc/pacman.d/mirrorlist"
        ]
        run_cc(ref_cmd, mountpoint)
        installation.add_bootloader(Bootloader.Systemd)
        installation.copy_iso_network_config(enable_services=False)
        installation.set_timezone("US/Eastern")
        installation.add_additional_packages(nl.pkgs)
        installation.create_users(User(nl.user_name, Password(pw), True, nl.groups))
        sys_dots(mountpoint, script_dir, nl.sys_cp)
        installation.enable_service(nl.sys_services)
        run_cc([f"systemctl disable {' '.join(nl.disable_svcs)}"], mountpoint)
        configure_sudo(nl.user_name, mountpoint, pwd_require=False)
        config_pac_conf(mountpoint)
        chaotic_repo(mountpoint)
        systemd_modify(mountpoint)
        usr_cmd = [
            "xdg-user-dirs-update",
            f"mkdir -p /{user_home}/.cache/mpd/playlists /{user_home}/.cache/mpd/state",
        ]
        run_cc(usr_cmd, mountpoint, nl.user_name)
        enable_user_services(user_home, nl.user_services, mountpoint, nl.user_name)
        copy_dir(nl.usb_key_dir, mountpoint / user_home / ".ssh")
        copy_dir(nl.wireguard_dir, mountpoint / "etc" / "wireguard", set_root=True)
        copy_scripts(mountpoint, script_dir, "noah_lib", nl.user_name, nl.user_script)
        user_service_file(nl.user_name, nl.user_script, mountpoint)
        run_cc([f"chown -R {nl.user_name}:{nl.user_name} /{user_home}"], mountpoint)
        installation.genfstab()
        modify_fstab(mountpoint)
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
    mnt_cp_keys(
        nl.min_usb_size, nl.usb_fs_type, nl.usb_key_dir, nl.key_files, nl.wireguard_dir
    )
    ref_cmd = ["reflector", *nl.reflector_opts, "--save", "/etc/pacman.d/mirrorlist"]
    run_cmd(ref_cmd)
    config_pac_conf()
    chaotic_repo()
    perform_installation(Path("/mnt"))


# _minimal()
copy_scripts(Path("/mnt"), script_dir, "noah_lib", nl.user_name, nl.user_script)
