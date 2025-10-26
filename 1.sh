#!/bin/bash

REPO_URL="https://github.com/acctux/noah.git"
CLONE_DIR="$HOME/noah"

setup_environment() {
	local tries=0
	local max_tries=5

	while ((tries < max_tries)); do
		echo "Attempt $((tries + 1)) of $max_tries..."

		if ! ping -c 1 archlinux.org &>/dev/null; then
			echo "Network unavailable. Retrying..."
			((tries++))
			sleep 5
			continue
		fi

		if ! pacman -Sy; then
			echo "pacman -Sy failed."
			((tries++))
			sleep 5
			continue
		fi

		if ! pacman-key --init; then
			echo "pacman-key --init failed."
			((tries++))
			sleep 5
			continue
		fi

		if ! pacman -S --noconfirm archlinux-keyring; then
			echo "Installing archlinux-keyring failed."
			((tries++))
			sleep 5
			continue
		fi

		if ! pacman -S --noconfirm --needed git	pacman-contrib; then
			echo "Package installation failed."
			((tries++))
			sleep 5
			continue
		fi
	done

	echo "All $max_tries attempts failed. Exiting."
	exit 1
}
setup_environment

clone_repo() {
	rm -rf "$CLONE_DIR"
	echo "Cloning repository..."
	if git clone "$REPO_URL" "$CLONE_DIR"; then
		cd "$CLONE_DIR"
		chmod +x noah
	else
		echo "Git clone failed."
		return 1
	fi
}
clone_repo

echo "Welcome to Noah's Arch, you'll be swept away."


