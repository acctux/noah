from pathlib import Path
import shutil
from noah_lib.sys_functions import run_chroot
from utils import UserSrv, get_logger

log = get_logger("User")


def copy_dir(dir: str, dest: Path, own_it_by: str | bool = False, chmod_it=False):
    src = Path("/root") / dir
    if not src.is_dir():
        log.error(f"{src} does not exist")
    shutil.copytree(src, dest, dirs_exist_ok=True)
    for path in dest.rglob("*"):
        if own_it_by:
            shutil.chown(path, user=f"{own_it_by}", group=f"{own_it_by}")
        if chmod_it:
            path.chmod(0o600)
    if own_it_by:
        shutil.chown(dest, user=f"{own_it_by}", group=f"{own_it_by}")
    if chmod_it:
        dest.chmod(0o700)


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
            target_dir = base_dir / unit.target
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
ExecStart=/usr/bin/alacritty -e python {run_script}
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
