import getpass
import logging
import subprocess
import sys
from conf import user_name


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.INFO: "\033[34m",
        logging.ERROR: "\033[31m",
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        return f"{color}{super().format(record)}{self.RESET}"


def get_logger(name):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ColorFormatter("%(name)s %(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


log = get_logger("Noah")


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


def ask_pass() -> str:
    while True:
        pwd1 = getpass.getpass(f"Enter password for {user_name}: ")
        pwd2 = getpass.getpass("Re-enter password: ")
        if not pwd1:
            print("Password cannot be empty. Try again.")
            continue
        if pwd1 != pwd2:
            print("Passwords do not match. Try again.")
            continue
        return pwd1
