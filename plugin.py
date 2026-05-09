import archinstall
from archinstall.lib.installer import Installer

__version__ = 0.1


class Plugin:
    TEMPORARY_USER_NAME = "aurinstall"
    DEPENDENCIES = ["git"]
    AUR_HELPER_REPOSITORY = "https://aur.archlinux.org/paru-bin.git"

    def on_install(self, installer: Installer):
        packages = archinstall.arguments["packages_aur"]
        if len(packages) > 0:
            self.install_dependencies(installer)
            self.create_temporary_user(installer)
            self.enable_passwordless_sudo(installer)
            self.install_aur_helper(installer)
            self.install_aur_packages(packages, installer)
            self.disable_passwordless_sudo(installer)
            self.delete_temporary_user(installer)

    def install_dependencies(self, installer: Installer):
        installer.add_additional_packages(self.DEPENDENCIES)

    def create_temporary_user(self, installer: Installer):
        installer.create_users(self.TEMPORARY_USER_NAME)

    def delete_temporary_user(self, installer: Installer):
        installer.arch_chroot(f"userdel {self.TEMPORARY_USER_NAME}")

    def enable_passwordless_sudo(self, installer: Installer):
        installer.arch_chroot(
            r"sed -i 's/# \(%wheel ALL=(ALL) NOPASSWD: ALL\)/\1/' /etc/sudoers"
        )

    def disable_passwordless_sudo(self, installer: Installer):
        installer.arch_chroot(
            r"sed -i 's/# \(%wheel ALL=(ALL) NOPASSWD: ALL\)/\1/' /etc/sudoers"
        )

    def install_aur_helper(self, installer: Installer):
        installer.arch_chroot(
            f"su aurinstall -c 'cd $(mktemp -d) && git clone {self.AUR_HELPER_REPOSITORY} . && makepkg -sim --noconfirm'"
        )

    def install_aur_packages(self, packages, installer: Installer):
        installer.arch_chroot(
            f'su {self.TEMPORARY_USER_NAME} -c "paru -Sy --nosudoloop --needed --noconfirm {" ".join(packages)}"'
        )

    def on_pacstrap(self, installer: Installer):
        packages = archinstall.arguments["packages_aur"]
        if len(packages) > 0:
            self.dependencies(installer)
            self.temporary_user(installer)
            self.passwordless_sudo(installer)

    def dependencies(self, installer: Installer):
        installer.add_additional_packages(self.DEPENDENCIES)

    def temporary_user(self, installer: Installer):
        installer.create_users(self.TEMPORARY_USER_NAME)

    def on_genfstab(self, installer: Installer):
        installer.arch_chroot(
            r"sed -i 's/# \(%wheel ALL=(ALL) NOPASSWD: ALL\)/\1/' /etc/sudoers"
        )

    def on_mkinitcpio(self, installer: Installer):
        installer.arch_chroot(
            f"su aurinstall -c 'cd $(mktemp -d) && git clone {self.AUR_HELPER_REPOSITORY} . && makepkg -sim --noconfirm'"
        )

    def on_add_bootloader(self, packages, installer: Installer):
        installer.arch_chroot(
            f'su {self.TEMPORARY_USER_NAME} -c "paru -Sy --nosudoloop --needed --noconfirm {" ".join(packages)}"'
        )

