import os
import getpass
from pathlib import Path
import logging
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def run_cmd(command, check=False, input_text=None):
    """Helper function to run a command and capture its output."""
    try:
        result = subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            check=check,
        )
        return result
    except subprocess.CalledProcessError as e:
        log.error(f"Command failed: {' '.join(command)}\n{e.stderr}")
        return None


def import_ssh_key(key_path: Path):
    """Imports an SSH key if it doesn't exist in the SSH agent."""
    if not key_path.exists():
        log.error(f"SSH key file {key_path} does not exist.")
        return
    if key_path.stat().st_mode & 0o777 != 0o600:
        os.chmod(key_path, 0o600)
        log.info(f"SSH key permissions for {key_path} set to 600.")
    socket = f"/run/user/{os.getuid()}/gcr/ssh"
    os.environ["SSH_AUTH_SOCK"] = socket
    if not Path(socket).exists():
        log.info("Starting gcr-ssh-agent.socket...")
        run_cmd(["systemctl", "--user", "enable", "gcr-ssh-agent.socket"])
        run_cmd(["systemctl", "--user", "start", "gcr-ssh-agent.socket"])
    keygen = run_cmd(["ssh-keygen", "-lf", str(key_path)])
    if not keygen or not keygen.stdout:
        log.error("Failed to read SSH key fingerprint.")
        return
    ssh_list = run_cmd(["ssh-add", "-l"])
    if ssh_list and keygen.stdout.strip().split()[1] in ssh_list.stdout:
        log.info("SSH key already imported.")
        return
    run_cmd(["ssh-add", str(key_path)], True)
    log.info("SSH key added.")


def import_gpg_key(gpg_key: str):
    """Imports a GPG key and sets trust if not already imported."""
    if not Path(gpg_key).exists():
        log.error(f"GPG key file {gpg_key} does not exist.")
        return
    show = run_cmd(
        ["gpg", "--import-options", "show-only", "--import", "--with-colons", gpg_key]
    )
    if not show or not show.stdout:
        log.error(f"Failed to extract fingerprint from GPG key {gpg_key}.")
        return
    fingerprint = next(
        (
            line.split(":")[9]
            for line in show.stdout.splitlines()
            if line.startswith("fpr")
        ),
        None,
    )
    if not fingerprint:
        log.error("Could not extract GPG fingerprint from the key.")
        return
    key_list = run_cmd(["gpg", "--list-keys", fingerprint])
    if key_list is None:
        log.error("Failed to check GPG key list.")
        return
    if key_list.returncode == 0:
        log.info(f"GPG key {fingerprint} already imported.")
        return
    if run_cmd(["gpg", "--import", gpg_key], check=True) is None:
        log.error("Failed to import GPG key.")
        return
    trust = run_cmd(
        ["gpg", "--import-ownertrust"],
        input_text=f"{fingerprint}:6:\n",
    )
    if not trust or trust.returncode != 0:
        log.error("Failed to set trust for GPG key.")
        return
    log.info(f"GPG key imported and trusted (ultimate): {fingerprint}")


def initialize_gocrypt(enc_dir: Path):
    """Initializes a gocryptfs encrypted directory."""
    if enc_dir.exists() and len(list(enc_dir.iterdir())) > 0:
        log.info(f"gocryptfs directory {enc_dir} already initialized.")
        return
    enc_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"gocryptfs directory {enc_dir} created.")
    while True:
        pw1 = getpass.getpass("Enter new gocryptfs password: ")
        pw2 = getpass.getpass("Confirm password: ")
        if pw1 == pw2 and pw1:
            break
        log.warning("Passwords do not match or empty. Try again.\n")
    run_cmd(
        ["gocryptfs", "-init", "--passfile", "/dev/stdin", str(enc_dir)],
        check=True,
        input_text=pw1,
    )
    log.info(f"gocryptfs initialized at {enc_dir}.")
