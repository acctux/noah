from pathlib import Path
import shutil
from pydantic import BaseModel
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


class UserSrv(BaseModel):
    target: str
    services: list[str]
    source_dir: Path = Path("/usr/lib/systemd/user")


def enable_user_services(
    user_home: str,
    units: UserSrv | list[UserSrv],
    mnt_point: Path,
    user_name: str,
) -> None:
    if isinstance(units, UserSrv):
        units = [units]
    user_commands: list[str] = []
    base_dir = Path(f"/{user_home}") / ".config/systemd/user"
    for unit in units:
        for service in unit.services:
            target_dir = base_dir / unit.target
            user_commands.append(f"mkdir -p {target_dir}")
            src = unit.source_dir / service
            dst = target_dir / service
            user_commands.append(f"ln -sf {src} {dst}")
    run_cc(user_commands, mnt_point, user_name)


def user_service(
    script_dir: str,
    mnt_point: Path,
    user_name: str,
    user_home: str,
    user_setup_script: str = "user_setup.py",
) -> None:
    run_script = Path(f"/{user_home}") / script_dir / user_setup_script
    service_dir = Path(f"{user_home}/.config/systemd/user")
    (mnt_point / service_dir).mkdir(parents=True, exist_ok=True)
    svc_name = f"{run_script.stem}.service"
    (mnt_point / service_dir / svc_name).write_text(f"""[Unit]
Description=Open Alacritty running {run_script} on login
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/usr/bin/alacritty -e python {run_script}
Restart=no

[Install]
WantedBy=graphical-session.target
""")
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


def copy_file_list(
    user_name: str,
    mnt_point: Path,
    key_files: list[str],
    usb_key_dir: str,
    gpg_key: str = "my_sec_gpg.asc",
    ssh_key: str = "id_ed25519",
):
    mnt_home = mnt_point / "home" / user_name
    ssh_dir = mnt_home / ".ssh"
    gpg_dir = mnt_home / ".gnupg"
    for d in [ssh_dir, gpg_dir]:
        d.mkdir(parents=True, exist_ok=True)
        d.chmod(0o700)
    src = Path("/root") / usb_key_dir
    if not src.is_dir():
        log.error(f"{src} does not exist")
        return
    for name in key_files[:3]:
        src_file = src / name
        dest = mnt_home / usb_key_dir / name
        if name == ssh_key:
            dest = ssh_dir / name
        if name == gpg_key:
            dest = gpg_dir / name
        dest.mkdir(parents=True, exist_ok=True)
        if not src_file.is_file():
            log.error(f"{src_file} does not exist")
            continue
        shutil.copy2(src_file, dest)
        if name == ssh_key:
            dest.chmod(0o600)
