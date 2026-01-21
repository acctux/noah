from pathlib import Path
import shutil
from utils import UserSrv
from noah_lib.sys_functions import run_cc
from utils import get_logger

log = get_logger("User")


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


def enable_user_services(
    user_home: str,
    units: UserSrv | list[UserSrv],
    mnt_point: Path,
    user_name: str,
) -> None:
    if isinstance(units, UserSrv):
        units = [units]

    commands: list[str] = []
    base_dir = Path("/") / user_home / ".config/systemd/user"

    for unit in units:
        target_dir = base_dir / unit.target
        commands.append(f"mkdir -p {target_dir}")

        for service in unit.services:
            src = unit.source_dir / service
            dst = target_dir / service
            commands.append(f"ln -sf {src} {dst}")

    run_cc(commands, mnt_point, user_name)


def user_service(
    user_setup_script: str,
    mnt_point: Path,
    user_name: str,
    user_home: str,
) -> None:
    home = mnt_point / user_home
    run_script = Path(f"/{user_home}") / user_setup_script
    service_dir = home / ".config/systemd/user"
    service_dir.mkdir(parents=True, exist_ok=True)

    svc_name = f"{run_script.stem}.service"
    service_path = service_dir / svc_name

    service_path.write_text(
        f"""[Unit]
Description=Open Alacritty running {run_script} on login
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/usr/bin/alacritty -e python {run_script}
Restart=no

[Install]
WantedBy=graphical-session.target
"""
    )

    enable_user_services(
        user_home=user_home,
        units=UserSrv(
            target="graphical-session.target.wants",
            services=[svc_name],
            source_dir=service_dir,
        ),
        mnt_point=mnt_point,
        user_name=user_name,
    )


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


def copy_scripts(
    mnt_point: Path,
    script_dir: Path,
    lib_dir: str,
    user_name: str,
    user_home: str,
    user_script: str,
    dest: Path | None = None,
):
    if dest is None:
        dest = mnt_point / user_home
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
