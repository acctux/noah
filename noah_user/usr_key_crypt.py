import os
import getpass
from pathlib import Path
import gnupg
from noah_conf.conf import HOME
from utils import get_logger, run_cmd

log = get_logger("Noah")


def import_ssh_key(key_file: str):
    key_path = HOME / ".ssh" / key_file
    if key_path.stat().st_mode & 0o777 != 0o600:
        os.chmod(key_path, 0o600)
        log.info(f"SSH key permissions for {key_path} set to 600.")
    socket = f"/run/user/{os.getuid()}/gcr/ssh"
    os.environ["SSH_AUTH_SOCK"] = socket
    if not Path(socket).exists():
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


def import_gpg_key(gpg_path: Path):
    if run_cmd(["gpg", "--import", str(gpg_path)], text=True).returncode != 0:
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
