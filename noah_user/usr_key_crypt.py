import os
import getpass
from pathlib import Path
from noah_conf.conf import HOME
from utils import get_logger, run_cmd

log = get_logger("Noah")


def import_ssh_key(key_file: str):
    key_path = HOME / ".ssh" / key_file
    socket = f"/run/user/{os.getuid()}/gcr/ssh"
    os.environ["SSH_AUTH_SOCK"] = socket
    if not Path(socket).exists():
        run_cmd(["systemctl", "--user", "enable", "gcr-ssh-agent.socket"])
        run_cmd(["systemctl", "--user", "start", "gcr-ssh-agent.socket"])
    if run_cmd(["ssh-add", str(key_path)], check=True):
        log.info(f"SSH key {key_path} added or already present.")
    else:
        log.error(f"Failed to add SSH key {key_path}.")


def import_gpg_key(gpg_path: Path):
    if run_cmd(["gpg", "--import", str(gpg_path)], True).returncode != 0:
        log.error(f"Failed to import GPG key from {gpg_path}.")
    else:
        log.info(f"GPG key imported from {gpg_path}.")


def initialize_gocrypt(enc_dir: Path):
    enc_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"gocryptfs directory {enc_dir} created.")
    while True:
        pw1 = getpass.getpass("Enter new gocryptfs password: ")
        pw2 = getpass.getpass("Confirm password: ")
        if pw1 == pw2 and pw1:
            break
        log.warning("Passwords do not match or empty. Try again.\n")
    cmd = ["gocryptfs", "-init", "--passfile", "/dev/stdin", str(enc_dir)]
    run_cmd(cmd, check=True, input_text=pw1)
    log.info(f"gocryptfs initialized at {enc_dir}.")
