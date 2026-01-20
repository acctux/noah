import logging
from pathlib import Path
import subprocess
import sys
from noah_lib.conf import UserSrv


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.INFO: "\033[34m",  # Blue
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",  # Red
    }
    RESET = "\033[0m"

    def format(self, record):
        message = super().format(record)
        color = self.COLORS.get(record.levelno, "")
        if color:
            message = f"{color}{message}{self.RESET}"
        return message


def get_logger(name, level=logging.INFO, use_color=True):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stderr)
    fmt = "%(name)s %(levelname)s: %(message)s"
    if use_color:
        handler.setFormatter(ColorFormatter(fmt))
    else:
        handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def run_cmd(cmd: list[str], check=False, input_text: str | None = None):
    log = get_logger("Run CMD")
    try:
        log.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            text=True,
            check=check,
            capture_output=True,
            input=input_text,
        )
        if result.stdout:
            log.info(f"stdout: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        log.error(f"Command failed: {' '.join(cmd)} (exit {e.returncode})")
        if e.stdout:
            log.info(f"stdout: {e.stdout.strip()}")
        if e.stderr:
            log.error(f"stderr: {e.stderr.strip()}")
        return e


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


def setup_alacritty_auto(
    usr: str,
    user_setup_script: str,
    mnt_point: Path | None = None,
) -> None:
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
    if not mnt_point:
        run_cmd([f"systemctl --user enable {svc_name}"])
    else:
        service_path.chmod(0o644)
        enable_user_services(
            usr,
            mnt_point,
            [
                UserSrv(
                    target="graphical-session.target.wants",
                    services=["pipewire-pulse.service"],
                    source_dir=(home / ".config" / "systemd" / "user"),
                )
            ],
        )
