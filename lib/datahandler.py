from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PathResolver:
    usb: Path = Path("/mnt/usb")
    root: Path = Path("/root")
    mnt: Path = Path("/mnt")

    def resolve_mnt_base(self, target_dir: str, username: str) -> Path:
        if not target_dir:
            return self.mnt / "home" / username
        target = Path(target_dir)
        if target.is_absolute():
            target = target.relative_to("/")
        else:
            target = Path("home") / username / target
        return self.mnt / target


# =============================================================================
# Leaf Models
# =============================================================================
@dataclass
class GitRepo:
    username: str
    repos: dict[str, str]

    @property
    def full_repos(self) -> list[str]:
        return [f"{self.username}/{repo}" for repo in self.repos.values()]


@dataclass
class UserService:
    source: str
    target: str
    serv: list[str]

    def source_paths(self, username: str) -> list[Path]:
        source = Path(self.source)
        if not source.is_absolute():
            source = Path("/home") / username / source
        return [source / s for s in self.serv]

    def target_paths(self, username: str) -> list[Path]:
        base = (
            Path("/home")
            / username
            / f".config/systemd/user/{self.target}.target.wants"
        )
        return [base / s for s in self.serv]


# =============================================================================
# Configurations
# =============================================================================
@dataclass
class GitReposConfiguration:
    repositories: list[GitRepo] = field(default_factory=list)

    @classmethod
    def parse_arg(cls, arg: dict[str, dict[str, str]]):
        return cls(
            repositories=[
                GitRepo(
                    username=username,
                    repos=repos,
                )
                for username, repos in arg.items()
            ]
        )


@dataclass
class KeyCopyConfiguration:
    source_dir: str
    target_dir: str
    keys: dict[str, str]

    resolver: PathResolver = field(default_factory=PathResolver)

    def usb_to_root(self) -> list[tuple[Path, Path]]:
        src_base = self.resolver.usb / self.source_dir
        dst_base = self.resolver.root / self.target_dir.lstrip("/")

        transfers: list[tuple[Path, Path]] = []
        for _, name in self.keys.items():
            transfers.append((src_base / name, dst_base / name))
        return transfers

    def root_to_mnt(self, username: str) -> list[tuple[Path, Path]]:
        src_base = self.resolver.root / self.target_dir.lstrip("/")
        dst_base = self.resolver.resolve_mnt_base(self.target_dir, username)

        transfers: list[tuple[Path, Path]] = []
        for _, name in self.keys.items():
            transfers.append((src_base / name, dst_base / name))
        return transfers

    @classmethod
    def parse_arg(cls, arg: dict[str, Any]):
        return cls(
            source_dir=arg["source_dir"],
            target_dir=arg["target_dir"],
            keys=arg["keys"],
        )


@dataclass
class FlatCopy:
    source_dir: str
    target_dir: str
    names: list[str]
    resolver: PathResolver = field(default_factory=PathResolver)

    def usb_to_root(self) -> list[tuple[Path, Path]]:
        src_base = self.resolver.usb / self.source_dir
        dst_base = self.resolver.root / self.target_dir.lstrip("/")
        return [(src_base / name, dst_base / name) for name in self.names]

    def root_expected(self) -> list[Path]:
        """What should exist under /root after copy."""
        base = self.resolver.root / self.target_dir
        return [base / name for name in self.names]

    def root_to_mnt(self, username: str) -> list[tuple[Path, Path]]:
        src_base = self.resolver.root / self.target_dir.lstrip("/")
        dst_base = self.resolver.resolve_mnt_base(self.target_dir, username)
        return [(src_base / name, dst_base / name) for name in self.names]


@dataclass
class ExtraCopyConfiguration:
    copies: list[FlatCopy] = field(default_factory=list)

    @classmethod
    def parse_arg(cls, arg: list[dict[str, Any]]):
        return cls(
            copies=[
                FlatCopy(
                    source_dir=v["source_dir"],
                    target_dir=v["target_dir"],
                    names=v["names"],
                )
                for v in arg
            ]
        )


@dataclass
class DirContentsCopyConfiguration:
    copies: list[FlatCopy] = field(default_factory=list)

    @classmethod
    def parse_arg(cls, arg: list[dict[str, Any]]):
        return cls(
            copies=[
                FlatCopy(
                    source_dir=v["source_dir"],
                    target_dir=v["target_dir"],
                    names=v["names"],
                )
                for v in arg
            ]
        )


@dataclass
class UserServicesConfiguration:
    services: list[UserService] = field(default_factory=list)

    @classmethod
    def parse_arg(cls, arg: list[dict[str, Any]]):
        return cls(
            services=[
                UserService(
                    source=v["source"],
                    target=v["target"],
                    serv=v.get("serv", v.get("servs", [])),
                )
                for v in arg
            ]
        )


# =============================================================================
# Main Config
# =============================================================================
@dataclass
class NoahConfig:
    terminal: str = "kitty"
    firefox_browser: str | None = None
    git_user: str | None = None
    dots_repo: str | None = None
    reflector_country: str | None = None
    encrypted_dir: str | None = None
    parallel_downloads: int = 10
    disable_svcs: list[str] = field(default_factory=list)
    sudo_defaults: list[str] = field(default_factory=list)
    apps_to_hide: list[str] = field(default_factory=list)
    no_extracts: list[str] = field(default_factory=list)
    yazi_plugins: list[str] = field(default_factory=list)
    dirs_to_link: list[str] = field(default_factory=list)
    dirs_icons: dict[str, str] = field(default_factory=dict)
    git_repos_config: GitReposConfiguration | None = None
    key_copy_config: KeyCopyConfiguration | None = None
    additional_usb_to_cp_config: ExtraCopyConfiguration | None = None
    dir_contents_to_cp_config: DirContentsCopyConfiguration | None = None
    user_services_config: UserServicesConfiguration | None = None

    @classmethod
    def from_config(cls, args_config: dict[str, Any]):
        config = cls()

        if terminal := args_config.get("terminal"):
            config.terminal = terminal

        if firefox_browser := args_config.get("firefox_browser"):
            config.firefox_browser = firefox_browser

        if dots_repo := args_config.get("dots_repo"):
            config.dots_repo = dots_repo

        if reflector_country := args_config.get("reflector_country"):
            config.reflector_country = reflector_country

        if git_user := args_config.get("git_user"):
            config.git_user = git_user

        if encrypted_dir := args_config.get("encrypted_dir"):
            config.encrypted_dir = encrypted_dir

        if parallel_downloads := args_config.get("parallel_downloads"):
            config.parallel_downloads = parallel_downloads

        if disable_svcs := args_config.get("disable_svcs", []):
            config.disable_svcs = disable_svcs

        if sudo_defaults := args_config.get("sudo_defaults", []):
            config.sudo_defaults = sudo_defaults

        if apps_to_hide := args_config.get("apps_to_hide", []):
            config.apps_to_hide = apps_to_hide

        if no_extracts := args_config.get("no_extracts", []):
            config.no_extracts = no_extracts

        if yazi_plugins := args_config.get("yazi_plugins", []):
            config.yazi_plugins = yazi_plugins

        if dirs_to_link := args_config.get("dirs_to_link", []):
            config.dirs_to_link = dirs_to_link

        if dirs_icons := args_config.get("dirs_icons", {}):
            config.dirs_icons = dirs_icons

        if key_copy_config := args_config.get("key_copy_config"):
            config.key_copy_config = KeyCopyConfiguration.parse_arg(
                key_copy_config,
            )

        if additional_usb_to_cp := args_config.get("additional_usb_to_cp"):
            config.additional_usb_to_cp_config = ExtraCopyConfiguration.parse_arg(
                additional_usb_to_cp,
            )

        if dir_contents_to_cp := args_config.get("dir_contents_to_cp"):
            config.dir_contents_to_cp_config = DirContentsCopyConfiguration.parse_arg(
                dir_contents_to_cp,
            )

        if user_services := args_config.get("user_services"):
            config.user_services_config = UserServicesConfiguration.parse_arg(
                user_services,
            )

        if git_repos := args_config.get("git_repos"):
            config.git_repos_config = GitReposConfiguration.parse_arg(
                git_repos,
            )

        return config
