from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SystemHardwareInfo:
    nvidia: bool
    cpu_vendor: str | None
    amd: bool
    is_vm: bool
    has_bat: bool

    @classmethod
    def from_sys_info(cls, sys_info) -> "SystemHardwareInfo":
        vendor = sys_info.cpu_vendor()
        return cls(
            nvidia=sys_info.has_nvidia_graphics(),
            cpu_vendor=vendor.value if hasattr(vendor, "value") else vendor,
            amd=sys_info.has_amd_graphics(),
            is_vm=sys_info.is_vm(),
            has_bat=sys_info.has_battery(),
        )


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
        """
        Return Paths relative to 'HOME'.
        """
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
class CopySpec:
    source: str
    target: str
    names: list[str]


@dataclass
class CopyConfiguration:
    specs: list[CopySpec] | None = None
    usb: Path = Path("/mnt/usb")
    root: Path = Path("/root/copyfiles")

    @classmethod
    def from_arg(cls, arg: Any) -> "CopyConfiguration":
        specs = []
        if isinstance(arg, list):
            for entry in arg:
                source = entry.get("source", "")
                for target_item in entry.get("targets", []):
                    specs.append(
                        CopySpec(source, target_item["dest"], target_item["names"])
                    )
        # Added: explicitly return the instance with the populated specs
        return cls(specs=specs)

    def _resolve(
        self, src_base: Path, dst_base: Path, username: str | None = None
    ) -> list[tuple[Path, Path]] | None:
        """Core internal resolution logic."""
        results = []
        home_base = Path(f"/home/{username}") if username else Path.home()

        if not self.specs:
            return None

        for spec in self.specs:
            for name in spec.names:
                src = src_base / spec.source / name

                # Handle '~' expansion
                dest_str = spec.target.replace("~", str(home_base))

                # Check if the target is already absolute (e.g., '/etc')
                path_obj = Path(dest_str)

                if path_obj.is_absolute():
                    # If it's absolute, we don't prepend dst_base
                    dst = path_obj / name
                else:
                    # If it's relative, we join it with dst_base
                    dst = dst_base / path_obj / name

                results.append((src, dst))
        return results

    def resolve_usb_to_root(self) -> list[tuple[Path, Path]] | None:
        """Resolves paths for moving data from USB to local staging."""
        return self._resolve(self.usb, self.root)

    def resolve_root_to_mnt(
        self, mnt_point: Path, username: str
    ) -> list[tuple[Path, Path]] | None:
        """Resolves paths for moving data from staging to the target mount."""
        return self._resolve(self.root, mnt_point, username=username)


@dataclass(slots=True)
class UserService:
    source: str
    target: str
    serv: list[str]

    @classmethod
    # Change type hint to list[dict[str, Any]] to match the argument passed in NoahConfig
    def from_arg(cls, v: list[dict[str, Any]]) -> "UserService":
        """
        Adapts the full list of services into a single container
        that handles the aggregation internally.
        """
        # Create a 'master' object to hold the collection
        master = cls("", "", [])
        master._all_services = []

        # Process the full list passed from NoahConfig
        for entry in v:
            source = entry.get("source", "")
            for target_name, services in entry.get("targets", {}).items():
                master._all_services.append(UserService(source, target_name, services))
        return master

    # Internal storage for the collection
    _all_services: list["UserService"] | None = None

    def source_paths(self, username: str) -> list[Path]:
        # If this is the master object, aggregate paths from all_services
        if self._all_services is not None:
            all_paths = []
            for svc in self._all_services:
                all_paths.extend(svc.source_paths(username))
            return all_paths

        # Original logic for individual objects
        base = Path(self.source)
        if not base.is_absolute():
            base = Path("/home") / username / base
        return [base / s for s in self.serv]

    def target_paths(self, username: str) -> list[Path]:
        if self._all_services is not None:
            all_paths = []
            for svc in self._all_services:
                all_paths.extend(svc.target_paths(username))
            return all_paths

        # Original logic for individual objects
        base = (
            Path("/home")
            / username
            / f".config/systemd/user/{self.target}.target.wants"
        )
        return [base / s for s in self.serv]

    @staticmethod
    def from_list(arg: list[dict[str, Any]] | None) -> list["UserService"] | None:
        """Original from_list logic preserved."""
        if not arg:
            return None
        services: list[UserService] = []
        for v in arg:
            if not v:
                continue
            # Note: For flat entries, this still works, but for your nested
            # structure, NoahConfig calls from_arg directly on the list.
            svc = UserService.from_arg([v])
            if svc is not None:
                services.append(svc)
        return services or None


# =============================================================================
# Main Config
# =============================================================================
@dataclass
class NoahConfig:
    terminal: str = "kitty"
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
    additional_usb_to_cp: CopyConfiguration | None = None
    user_services_config: UserService | None = None

    @classmethod
    def from_config(cls, args: dict[str, Any]) -> "NoahConfig":
        noah = cls()

        if "terminal" in args:
            noah.terminal = args["terminal"]

        if "parallel_downloads" in args:
            noah.parallel_downloads = args["parallel_downloads"]

        if "firefox_browser" in args:
            noah.firefox_browser = args["firefox_browser"]

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
            noah.disable_svcs = args["mask_svcs"]

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
            noah.user_services_config = UserService.from_arg(us)

        if gr := args.get("git_repo_config"):
            noah.git_repos_config = GitReposConfiguration.from_arg(gr)

        return noah
