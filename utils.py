import logging
import subprocess
from getpass import getpass
import sys


#########################
# LOG
#########################
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",
        logging.INFO: "\033[34m",
        logging.WARNING: "\033[93m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[41m",
    }
    RESET = "\033[0m"
    UNDERLINE = "\033[4m"
    NAME_COLOR = "\033[93m"

    def format(self, record):
        message = f"{self.NAME_COLOR}{record.name}{self.RESET}: {record.getMessage()}"
        color = self.COLORS.get(record.levelno, "")
        if color:
            message = f"{color}{message}{self.RESET}"
        if record.levelno == logging.CRITICAL:
            message = f"{self.UNDERLINE}{message}{self.RESET}"
        return message


def get_logger(log_name: str | None = None, level=logging.INFO):
    logger = logging.getLogger(log_name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ColorFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


log = get_logger("Noah")


#########################
# ASK PASSWORD
#########################
def ask_pass(prompt="Password: ", confirm=True, min_len=6, retries=3) -> str:
    for _ in range(retries):
        pwd = getpass(prompt)
        if len(pwd) < min_len:
            log.warning(f"Password must be at least {min_len} characters.")
            continue
        if confirm and pwd != getpass("Confirm password: "):
            log.warning("Passwords do not match.")
            continue
        return pwd
    raise ValueError("Too many failed attempts.")


def run_dmc(
    cmd: list[str],
    check: bool = False,
    input_text: str = "",
    shell: bool = False,
    cwd=None,
    interactive=False,
):
    if interactive:
        return subprocess.Popen(cmd).wait()
    log = get_logger("Run CMD")
    try:
        log.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            text=True,
            check=check,
            capture_output=True,
            input=input_text,
            shell=shell,
            cwd=cwd,
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


def yes_no(prompt: str, default: bool = True) -> bool:
    while True:
        r = (
            input(f"\033[92m{prompt} {'(Y/n)' if default else '(y/N)'}: \033[0m")
            .strip()
            .lower()
        )
        if r == "":
            return default
        if r in ("y"):
            return True
        if r in ("n"):
            return False
        log.warning("Please enter 'y' or 'n'.")


def ping(host: str = "google.com") -> bool:
    cmd = ["ping", "-c", "1", host]
    return (
        subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
        == 0
    )
