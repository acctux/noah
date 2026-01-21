from pathlib import Path


HOME = Path.home()
###########-SYMLINK-############
# Polka Config
dots_dir = HOME / "Polka"
dirs_to_link = ["config/systemd/user", "config/nvim", "local/bin"]
base_dir = HOME / "Lit/Docs/base"
ind_dirs = [
    ((base_dir / "fonts"), (HOME / ".local" / "share" / "fonts")),
    ((base_dir / "task"), (HOME / ".config" / "task")),
    ((base_dir / "zsh"), (HOME / ".config" / "zsh")),
]
