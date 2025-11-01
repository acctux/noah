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

    if ! pacman -Sy --noconfirm; then
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

    if ! pacman -S --noconfirm --needed git pacman-contrib; then
      echo "Package installation failed."
      ((tries++))
      sleep 5
      continue
    fi

    echo "Environment setup successful."
    return 0 # ✅ Exit function if everything succeeded
  done

  echo "All $max_tries attempts failed. Exiting."
  exit 1
}

clone_repo() {
  rm -rf "$CLONE_DIR"
  echo "Cloning repository..."
  if git clone "$REPO_URL" "$CLONE_DIR"; then
    cd "$CLONE_DIR" || exit 1
    chmod +x noah
    echo "Repository cloned successfully."
  else
    echo "Git clone failed."
    exit 1
  fi
}

#Main
setup_environment
clone_repo
cd $CLONE_DIR
git checkout -b py
echo "Welcome to Noah's Arch, you'll be swept away."
