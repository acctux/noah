from pathlib import Path
import gnupg
import sys

FILE_NAME = "test.txt"
PASSPHRASE = "mypassword"


def encrypt_file(input_path: Path, output_path: Path, gpg: gnupg.GPG) -> None:
    with input_path.open("rb") as f:
        status = gpg.encrypt_file(
            f,
            recipients=None,
            symmetric=True,
            passphrase=PASSPHRASE,
            output=str(output_path),
        )
    if not status.ok:
        raise RuntimeError(f"Encryption failed: {status.status}")


def decrypt_file(input_path: Path, output_path: Path, gpg: gnupg.GPG) -> None:
    with input_path.open("rb") as f:
        status = gpg.decrypt_file(f, passphrase=PASSPHRASE, output=str(output_path))
    if not status.ok:
        raise RuntimeError(f"Decryption failed: {status.status}")


def main():
    home = Path.home()
    plaintext = home / FILE_NAME
    encrypted = home / f"{FILE_NAME}.gpg"
    gpg = gnupg.GPG()
    try:
        if encrypted.exists():
            print("Encrypted file found → decrypting...")
            decrypt_file(encrypted, plaintext, gpg)
            encrypted.unlink()
            print(f"Decrypted and removed: {encrypted}")
        elif plaintext.exists():
            print("Plaintext file found → encrypting...")
            encrypt_file(plaintext, encrypted, gpg)
            plaintext.unlink()
            print(f"Encrypted and removed: {plaintext}")
        else:
            raise FileNotFoundError("Neither plaintext nor encrypted file exists")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

