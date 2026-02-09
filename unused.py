import gnupg
import sys
from getpass import getpass
import logging
from pathlib import Path


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
            print(f"Password must be at least {min_len} characters.")
            continue
        if confirm and pwd != getpass("Confirm password: "):
            print("Passwords do not match.")
            continue
        return pwd
    raise ValueError("Too many failed attempts.")


#########################
# GNUPG
#########################
def gpg_toggle(file_dir=Path.home(), dec_name="test.txt"):
    enc_name = f"{dec_name.split('.')[0]}.gpg"
    dec_path = file_dir / dec_name
    enc_path = file_dir / enc_name
    if enc_path.exists():
        gpg = gnupg.GPG()
        log.info(f"Decrypting: {enc_path.name}")
        with enc_path.open("rb") as f:
            result = gpg.decrypt_file(
                f,
                passphrase=ask_pass(min_len=4, confirm=False),
                output=str(dec_path),
            )
        if not result.ok:
            log.error(f"Decryption failed: {result.status}")
        enc_path.unlink()
        log.info(f"Decrypted: {dec_path.name}")
    elif dec_path.exists():
        gpg = gnupg.GPG()
        log.info(f"Encrypting: {dec_path.name}")
        with dec_path.open("rb") as f:
            result = gpg.encrypt(
                f,
                recipients=None,
                symmetric=True,
                passphrase=ask_pass(min_len=4),
                output=str(enc_path),
            )
        if not result.ok:
            log.error(f"Failed: {result.status}")
        dec_path.unlink()
        log.info(f"Encrypted: {enc_path.name}")
    else:
        log.info(f"Neither {dec_path} nor {enc_path} exists.")
