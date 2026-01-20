#################-MAIN FUNCTIONS-#################
import getpass
from pathlib import Path
import shlex
import shutil
from noah_lib.conf import UserSrv
from noah_lib.utils import get_logger
from archinstall.lib.installer import SysCommand

log = get_logger("User")


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


def copy_file_list(key_files: list[str], usb_key_dir: str, dest: Path):
    src = Path("/root") / usb_key_dir
    if not src.is_dir():
        log.error(f"{src} does not exist")
        return
    dest.mkdir(parents=True, exist_ok=True)
    dest.chmod(0o700)
    for name in key_files[:3]:
        src_file = src / name
        if not src_file.is_file():
            log.error(f"{src_file} does not exist")
            continue
        dest_file = dest / name
        shutil.copy2(src_file, dest_file)
        if name in key_files[:2]:
            dest_file.chmod(0o600)


def modify_systemd(
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
    dest.chmod(0o755)
    for path in dest.rglob("*"):
        if path.is_symlink():
            continue
        if path.is_dir():
            path.chmod(0o755)
        else:
            path.chmod(0o644)
    cmd = [f"chown -R {user_name}:{user_name} {dest}"]
    run_cc(cmd, mnt_point, None, True)


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


def type_password(user_name: str) -> str:
    while True:
        pwd1 = getpass.getpass(f"Enter password for {user_name}: ")
        pwd2 = getpass.getpass("Re-enter password: ")
        if not pwd1 or pwd1 != pwd2:
            log.info("Try again.")
            continue
        return pwd1


def ensure_password(usb_key_dir: str, key_files: list[str], user_name: str) -> str:
    key_path = Path("/root") / usb_key_dir / key_files[3]

    if key_path.exists():
        try:
            pw = key_path.read_text().strip()
            log.info(f"Password loaded from '{key_path}'.")
            return pw
        except Exception as e:
            log.error(f"Failed to read password from '{key_path}': {e}")
    log.warning(f"Password file '{key_path}' not found or unreadable.")
    return type_password(user_name)
