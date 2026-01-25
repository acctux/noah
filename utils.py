import logging
from pathlib import Path
import subprocess
from getpass import getpass
import sys
import gnupg


#########################
# LOG
#########################
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",  # Cyan
        logging.INFO: "\033[34m",  # Blue
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",  # Red
        logging.CRITICAL: "\033[41m",  # Red background
    }
    RESET = "\033[0m"
    UNDERLINE = "\033[4m"

    def format(self, record):
        # Hide levelname for INFO
        message = f"{record.name}: {record.getMessage()}"
        color = self.COLORS.get(record.levelno, "")
        if color:
            message = f"{color}{message}{self.RESET}"
        if record.levelno == logging.CRITICAL:
            message = f"{self.UNDERLINE}{message}{self.RESET}"
        return message


def get_logger(name, level=logging.INFO, use_color=True):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        ColorFormatter()
        if use_color
        else logging.Formatter("%(name)s %(levelname)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


log = get_logger("Noah")
#########################


#########################
# PASSWORD
#########################
def src_pass_file(usb_key_dir: str, pass_file: str):
    key_path = Path("/root") / usb_key_dir / pass_file
    if key_path.exists():
        try:
            pw = key_path.read_text().strip()
            log.info(f"{key_path} loaded ")
            return pw
        except Exception as e:
            log.error(f"{e}")
    log.warning(f"{key_path} not found or unreadable.")


def ask_pass(prompt="Password: ", min_len=8, confirm=True, retries=3) -> str:
    for _ in range(retries):
        pwd = getpass(prompt)
        if len(pwd) < min_len:
            print(f"Password must be at least {min_len} characters.")
            continue
        if confirm and pwd != getpass("Confirm password: "):
            print("Passwords do not match.")
            continue
        return pwd
    raise ValueError("Too many failed attempts.")


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


def ping(host: str) -> bool:
    return (
        subprocess.run(
            ["ping", "-c", "1", host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def gpg_toggle(file_dir=Path.home(), dec_name="test.txt"):
    enc_name = f"{dec_name.split('.')[0]}.gpg"
    dec_path = file_dir / dec_name
    enc_path = file_dir / enc_name
    if enc_path.exists():
        gpg = gnupg.GPG()
        log.info(f"Decrypting: {enc_path.name}")
        with enc_path.open("rb") as f:
            passphrase = ask_pass(min_len=4, confirm=False)
            result = gpg.decrypt_file(f, passphrase=passphrase, output=str(dec_path))
        if not result.ok:
            log.error(f"Decryption failed: {result.status}")
        enc_path.unlink()
        log.info(f"Decrypted: {dec_path.name}")
    elif dec_path.exists():
        gpg = gnupg.GPG()
        log.info(f"Encrypting: {dec_path.name}")
        with dec_path.open("rb") as f:
            p = ask_pass(min_len=4)
            result = gpg.encrypt_file(
                f, recipients=None, symmetric=True, passphrase=p, output=str(enc_path)
            )
        if not result.ok:
            raise RuntimeError(f"Failed: {result.status}")
        dec_path.unlink()
        log.info(f"Encrypted: {enc_path.name}")
    else:
        log.info(f"Neither {dec_path} nor {enc_path} exists.")
