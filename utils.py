import logging
from pathlib import Path
import subprocess
import sys
from pydantic import BaseModel


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


class UserSrv(BaseModel):
    target: str
    services: list[str]
    source_dir: Path = Path("/usr/lib/systemd/user")


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
