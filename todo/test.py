from pathlib import Path
import gnupg
import sys

input = "test.txt"


def encrypt_file_symmetric(
    input_path: Path,
    passphrase: str,
    output_path: Path | None = None,
    gpg: gnupg.GPG | None = None,
) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    gpg = gpg or gnupg.GPG()
    output_path = output_path or input_path.with_suffix(input_path.suffix + ".gpg")
    with input_path.open("rb") as f:
        status = gpg.encrypt_file(
            f,
            recipients=None,
            symmetric=True,
            passphrase=passphrase,
            output=str(output_path),
        )
    if not status.ok:
        raise RuntimeError(f"Encryption failed: {status.status}")
    return output_path


def decrypt_file_symmetric(
    input_path: Path,
    passphrase: str,
    output_path: Path,
    gpg: gnupg.GPG | None = None,
) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    gpg = gpg or gnupg.GPG()
    with input_path.open("rb") as f:
        status = gpg.decrypt_file(
            f,
            passphrase=passphrase,
            output=str(output_path),
        )
    if not status.ok:
        raise RuntimeError(f"Decryption failed: {status.status}")
    return output_path


def main() -> None:
    home = Path.home()
    plaintext = home / input
    encrypted = home / f"{input}.gpg"
    decrypted = plaintext  # restore to original name
    passphrase = "mypassword"
    gpg = gnupg.GPG()
    try:
        if encrypted.exists():
            print("Encrypted file found → decrypting...")
            decrypt_file_symmetric(
                input_path=encrypted,
                passphrase=passphrase,
                output_path=decrypted,
                gpg=gpg,
            )
            encrypted.unlink()
            print(f"Decrypted and removed: {encrypted}")
        elif plaintext.exists():
            print("Plaintext file found → encrypting...")
            encrypt_file_symmetric(
                input_path=plaintext,
                passphrase=passphrase,
                output_path=encrypted,
                gpg=gpg,
            )
            plaintext.unlink()
            print(f"Encrypted and removed: {plaintext}")
        else:
            raise FileNotFoundError("Neither plaintext nor encrypted file exists")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
