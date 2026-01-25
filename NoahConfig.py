from pathlib import Path
from typing import Any, Callable, List
import json


class NoahConfig:
    def __init__(self, file_path: str):
        self._file_path = Path(file_path)
        self._config: dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        # Check if the file exists and log the resolved path
        resolved_path = self._file_path.resolve()
        print(f"Looking for config at: {resolved_path}")

        if not resolved_path.exists():
            print(f"Config file does not exist: {resolved_path}")
            return

        # Try loading the JSON file
        try:
            print(f"Loading config from: {resolved_path}")
            self._config = json.loads(resolved_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in {resolved_path}: {e}")
        except Exception as e:
            print(f"Error loading config file: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        value: Any = self._config
        for key in key_path.split("."):
            try:
                value = value[key] if isinstance(value, dict) else value[int(key)]
            except (KeyError, IndexError, ValueError, TypeError):
                return default
        return value

    def _objects(self, key: str, factory: Callable[[dict], Any]) -> List[Any]:
        return [factory(item) for item in self.get(key, [])]

    # Top-level access methods
    def user_name(self) -> str:
        return self.get("user_name", "")

    def hostname(self) -> str:
        return self.get("hostname", "")

    def password(self) -> str:
        return self.get("password", "")

    def kernel(self) -> List[str]:
        return self.get("kernel", [])

    def kb_layout(self) -> str:
        return self.get("kb_layout", "")

    def sys_lang(self) -> str:
        return self.get("sys_lang", "")

    def sys_enc(self) -> str:
        return self.get("sys_enc", "")

    def timezone(self) -> str:
        return self.get("timezone", "")

    def groups(self) -> List[str]:
        return self.get("groups", [])

    # Services configurations
    def user_services(self) -> List[dict]:
        return self._objects(
            "services.user",
            lambda s: {
                "target": s["target"],
                "services": s["services"],
                "source_dir": Path(s["source_dir"]),
            },
        )

    def system_services(self) -> dict:
        return self.get("services.system", {})

    # Git repository configurations
    def git_repos(self) -> List[dict]:
        return self._objects(
            "git.repos",
            lambda r: {"target_dir": r["target_dir"], "repos": r["repos"]},
        )

    # Other configurations
    def mkinitcpio(self) -> dict:
        return self.get("mkinitcpio", {})

    def script_pwd_to_copy(self) -> dict:
        return self.get("script_pwd_to_copy", {})

    def reflector(self) -> dict:
        return self.get("reflector", {})

    def usb(self) -> dict:
        return self.get("usb", {})

    def icons(self) -> dict:
        return self.get("icons", {})

    def symlinks(self) -> dict:
        return self.get("symlinks", {})

    def hide_apps(self) -> List[str]:
        return self.get("hide_apps", [])

    # Add new lists
    def noextract_lines(self) -> List[str]:
        return [
            "NoExtract = etc/xdg/autostart/firewall-applet.desktop",
            "NoExtract = usr/share/icons/capitaine-cursors/*",
        ]

    def pkgs(self) -> List[str]:
        return [
            # Amd packages
            "mesa",
            "xf86-video-amdgpu",
            "xf86-video-ati",
        ]


# Example usage:
cfg = NoahConfig("/home/nick/Lit/Noah/noah.json")

# Access and print some basic configurations
print(f"User Name: {cfg.user_name}")
print(f"Hostname: {cfg.hostname}")
print(f"Kernel: {cfg.kernel}")
print(f"Keyboard Layout: {cfg.kb_layout}")
print(f"System Language: {cfg.sys_lang}")
print(f"System Encoding: {cfg.sys_enc}")
print(f"Timezone: {cfg.timezone}")
print(f"Groups: {', '.join(cfg.groups())}")
print(f"script_pwd_to_copy: {', '.join(cfg.script_pwd_to_copy())}")
print(f"Password: {cfg.password}")
# Example: Access services
system_services = cfg.system_services()
print(f"Enabled Services: {system_services.get('enable', [])}")
print(f"Disabled Services: {system_services.get('disable', [])}")
# Example: Git Repositories
git_repos = cfg.git_repos()
for repo in git_repos:
    print(f"Repo Directory: {repo['target_dir']}, Repos: {', '.join(repo['repos'])}")
# Example: User Services
user_services = cfg.user_services()
for srv in user_services:
    print(
        f"User Service Target: {srv['target']}, Services: {', '.join(srv['services'])}"
    )
# Example: Other configurations (mkinitcpio, reflector, etc.)
print(f"mkinitcpio Hooks: {cfg.mkinitcpio().get('hooks', [])}")
print(f"Reflector Options: {cfg.reflector().get('options', [])}")
print(f"USB Config: {cfg.usb().get('fs_type', 'N/A')}")
