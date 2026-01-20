from pathlib import Path
import os
import getpass
from utils import get_logger, run_cmd

log = get_logger("Noah")


def import_ssh_key(key_path: Path):
    if key_path.stat().st_mode & 0o777 != 0o600:
        os.chmod(key_path, 0o600)
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


def import_gpg_key(gpg_key: str):
    show = run_cmd(
        ["gpg", "--import-options", "show-only", "--import", "--with-colons", gpg_key]
    )
    fingerprint = next(
        (
            line.split(":")[9]
            for line in show.stdout.splitlines()
            if line.startswith("fpr")
        ),
        None,
    )
    if not fingerprint:
        log.error("Could not extract GPG fingerprint.")
        return
    if run_cmd(["gpg", "--list-keys", fingerprint]).returncode == 0:
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
    enc_dir.mkdir(parents=True, exist_ok=True)
    while True:
        pw1 = getpass.getpass("Enter new gocryptfs password: ")
        pw2 = getpass.getpass("Confirm password: ")
        if pw1 == pw2 and pw1:
            break
        print("Passwords do not match or empty. Try again.\n")
    run_cmd(
        ["gocryptfs", "-init", "--passfile", "/dev/stdin", str(enc_dir)],
        check=True,
        input_text=pw1,
    )
