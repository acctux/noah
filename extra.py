from dataclasses import dataclass
import os
import shlex
from pathlib import Path

from archinstall.lib.installer import SysCommand, info, error, shutil, subprocess


def run_cmd(cmd, check=False):
    try:
        info(f"Running: {cmd}")
        result = subprocess.run(cmd, text=True, shell=True, check=check)
        return result
    except subprocess.CalledProcessError as e:
        error(f"Failed: {cmd}\nExit code: {e.returncode}")
        return e


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


def system_dotfiles_handling(git_name: str, sys_dots: str, mnt_point: Path):
    temp_dir = Path(f"/root/{sys_dots}")
    directories_to_copy = ["etc", "usr", "root"]
    if not (temp_dir).exists():
        run_cmd([f"git clone https://github.com/{git_name}/{sys_dots}.git {temp_dir}"])
    for dir_name in directories_to_copy:
        source_dir = temp_dir / dir_name
        target_dir = mnt_point / dir_name
        if source_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            for item in source_dir.iterdir():
                dest = target_dir / item.name
                if item.is_dir():
                    shutil.copytree(
                        item, dest, dirs_exist_ok=True, copy_function=shutil.copy2
                    )
                    info(f"Copying {item} -> {dest}")
                else:
                    shutil.copy2(item, dest)
                    info(f"Copying {item} -> {dest}")
        else:
            error(f"Source directory {source_dir} not found. Skipping.")


@dataclass(slots=True, frozen=True)
class UserUnit:
    name: str
    target: str
    location: str


def enable_user_services(
    user_home: str,
    units: UserUnit | list[UserUnit],
    mnt_point: Path,
    user_name: str,
) -> None:
    if isinstance(units, UserUnit):
        units = [units]

    commands: list[str] = []

    for unit in units:
        target_path = f"/{user_home}/.config/systemd/user/{unit.target}"
        unit_file = f"{unit.location}/{unit.name}"

        commands.extend(
            [
                f"mkdir -p {target_path}",
                f"ln -sf {unit_file} {target_path}/{unit.name}",
            ]
        )

    run_cc(commands, mnt_point, user_name)

