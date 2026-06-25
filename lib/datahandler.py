from dataclasses import dataclass
from pathlib import Path
from typing import Any


# =============================================================================
# Leaf Models
# =============================================================================
@dataclass
class GitRepo:
    username: str
    repos: dict[str, str]

    @property
    def full_repos(self) -> list[str]:
        repos = []
        for repo in self.repos.keys():
            repos.append(f"{self.username}/{repo}")
        return repos

    def local_paths(self, HOME: Path) -> list[Path]:
        dest_paths = []
        for partial_dest_str in self.repos.values():
            dest_paths.append(HOME / partial_dest_str)
        return dest_paths


# =============================================================================
# Configurations
# =============================================================================
@dataclass
class GitReposConfiguration:
    repositories: list[GitRepo]

    @classmethod
    def from_arg(cls, arg: dict[str, Any]) -> GitReposConfiguration | None:
        if not arg or not isinstance(arg, dict):
            return None
        username = arg.get("user_name")
        repos = arg.get("repos")
        if not username or not repos:
            return None
        return cls([GitRepo(username, repos)])


@dataclass
class AuthConfig:
    source: str
    name: str
    root_path: Path = Path("/root")
    usb: Path = Path("/mnt/usb")

    @classmethod
    def from_arg(cls, arg: dict[str, Any]) -> AuthConfig:
        return cls(source=arg.get("source", ""), name=arg.get("name", ""))

    def resolve_usb_to_root(self) -> tuple[Path, Path]:
        src = self.usb / self.source / self.name
        dst = self.root_path / self.name
        return (src, dst)


@dataclass
class CopySpec:
    source: str
    target: str
    names: list[str]
    key_type: str = "default"


@dataclass
class CopyConfiguration:
    specs: list[CopySpec] | None = None
    root_path: Path = Path("/root")
    usb: Path = Path("/mnt/usb")

    @classmethod
    def from_arg(cls, arg: list[dict[str, Any]]) -> CopyConfiguration:
        specs = []
        for entry in arg:
            source = entry.get("source", "")
            k_type = entry.get("type", "")
            for target_item in entry.get("targets", []):
                specs.append(
                    CopySpec(
                        source=source,
                        target=target_item["dest"],
                        names=target_item["names"],
                        key_type=k_type,
                    )
                )
        return cls(specs=specs)

    def resolve_usb_to_root(self) -> list[tuple[Path, Path]]:
        results = []
        if not self.specs:
            return results
        for spec in self.specs:
            for name in spec.names:
                src = self.usb / spec.source / name
                dst = self.root_path / spec.target.lstrip("/") / name
                results.append((src, dst))
        return results

    def resolve_root_to_mnt(
        self, mnt_point: Path, username: str
    ) -> list[tuple[Path, Path]]:
        results = []
        if not self.specs:
            return results
        home_base = f"home/{username}"
        for spec in self.specs:
            for name in spec.names:
                src = self.root_path / spec.target.lstrip("/") / name
                dst = mnt_point / spec.target.replace("~", home_base).lstrip("/") / name
                results.append((src, dst))
        return results

    def user_space_resolve_by_type(self, key_type: str, HOME: Path) -> list[Path]:
        """Filters paths by key_type and returns as Path objects."""
        results = []
        if self.specs:
            for spec in self.specs:
                if spec.key_type == key_type:
                    for name in spec.names:
                        raw_target = spec.target.replace("~", str(HOME))
                        dst = Path(raw_target) / name
                        results.append((dst))
        return results


@dataclass(frozen=True, slots=True)
class UserService:
    source: str
    target: str
    services: list[str]

    def get_source_paths(self, username: str) -> list[Path]:
        base = Path(self.source)
        if not base.is_absolute():
            base = Path("/home") / username / base
        return [base / s for s in self.services]

    def get_target_paths(self, username: str) -> list[Path]:
        base = (
            Path("/home")
            / username
            / f".config/systemd/user/{self.target}.target.wants"
        )
        return [base / s for s in self.services]


@dataclass
class UserServiceConfiguration:
    services: list[UserService] | None = None

    @classmethod
    def from_arg(
        cls, data: list[dict[str, Any]] | None
    ) -> UserServiceConfiguration | None:
        if not data:
            return None
        extracted = []
        for entry in data:
            source = entry.get("source", "")
            for target_name, services in entry.get("targets", {}).items():
                if services:
                    extracted.append(UserService(source, target_name, services))
        return cls(services=extracted) if extracted else None

    def get_all_source_paths(self, username: str) -> list[Path]:
        if self.services:
            return [p for svc in self.services for p in svc.get_source_paths(username)]
        else:
            return []

    def get_all_target_paths(self, username: str) -> list[Path]:
        if self.services:
            return [p for svc in self.services for p in svc.get_target_paths(username)]
        else:
            return []


# =============================================================================
# Main Config
# =============================================================================
@dataclass
class NoahConfig:
    terminal: str = "kitty"
    logitech_mouse: bool = False
    parallel_downloads: int = 10
    firefox_browser: str | None = None
    dotfiles_dir: str | None = None
    secret_dotfiles_dir: str | None = None
    dots_git_user_repo: str | None = None
    encrypted_dir: str | None = None
    reflector_options: list[str] | None = None
    disable_svcs: list[str] | None = None
    sudo_defaults: list[str] | None = None
    mask_svcs: list[str] | None = None
    apps_to_hide: list[str] | None = None
    no_extracts: list[str] | None = None
    yazi_plugins: list[str] | None = None
    dirs_icons: dict[str, str] | None = None
    git_repos_config: GitReposConfiguration | None = None
    dotdirs_to_link: list[str] | None = None
    copy_config: CopyConfiguration | None = None
    user_services_config: UserServiceConfiguration | None = None
    auth_config: AuthConfig | None = None

    @classmethod
    def from_config(cls, args: dict[str, Any]) -> "NoahConfig":
        noah = cls()

        if "terminal" in args:
            noah.terminal = args["terminal"]

        if "parallel_downloads" in args:
            noah.parallel_downloads = args["parallel_downloads"]

        if "firefox_browser" in args:
            noah.firefox_browser = args["firefox_browser"]

        if "logitech_mouse" in args:
            noah.logitech_mouse = args["logitech_mouse"]

        if "dotfiles_dir" in args:
            noah.dotfiles_dir = args["dotfiles_dir"]

        if "secret_dotfiles_dir" in args:
            noah.secret_dotfiles_dir = args["secret_dotfiles_dir"]

        if "dots_git_user_repo" in args:
            noah.dots_git_user_repo = args["dots_git_user_repo"]

        if "encrypted_dir" in args:
            noah.encrypted_dir = args["encrypted_dir"]

        if "disable_svcs" in args:
            noah.disable_svcs = args["disable_svcs"]

        if "mask_svcs" in args:
            noah.mask_svcs = args["mask_svcs"]

        if "sudo_defaults" in args:
            noah.sudo_defaults = args["sudo_defaults"]

        if "reflector_options" in args:
            noah.reflector_options = args["reflector_options"]

        if "apps_to_hide" in args:
            noah.apps_to_hide = args["apps_to_hide"]

        if "no_extracts" in args:
            noah.no_extracts = args["no_extracts"]

        if "yazi_plugins" in args:
            noah.yazi_plugins = args["yazi_plugins"]

        if "dirs_icons" in args:
            noah.dirs_icons = args["dirs_icons"]

        if "dotdirs_to_link" in args:
            noah.dotdirs_to_link = args["dotdirs_to_link"]

        if cc := args.get("copy_config"):
            noah.copy_config = CopyConfiguration.from_arg(cc)

        if us := args.get("user_services"):
            noah.user_services_config = UserServiceConfiguration.from_arg(us)

        if auth := args.get("auth_conf"):
            noah.auth_config = AuthConfig.from_arg(auth)

        if gr := args.get("git_repo_config"):
            noah.git_repos_config = GitReposConfiguration.from_arg(gr)

        return noah
