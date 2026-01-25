from pathlib import Path
import gnupg

from utils import ask_pass

gpg = gnupg.GPG()

key_data = (Path.home() / ".gnupg" / "my_sec_gpg.asc").read_text()
import_result = gpg.import_keys(key_data, passphrase=ask_pass("GPG Password: ", 6))
print(import_result.results)
