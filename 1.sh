#!/bin/bash

REPO_URL="https://github.com/acctux/noah.git"
CLONE_DIR="$HOME/archinstall"
DEPENDENCIES=("git" "pacman-contrib" "python-pyyaml")
JSON_FILE="$HOME/user_config.json"

setup_environment() {
  local tries=0
  local max_tries=5
  while ((tries < max_tries)); do
    if ! pacman-key --init; then
      echo "pacman-key --init failed."
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
    if ! pacman -S --noconfirm archlinux-keyring; then
      echo "Installing archlinux-keyring failed."
      ((tries++))
      sleep 5
      continue
    fi
    if ! pacman -S --noconfirm --needed "${DEPENDENCIES[@]}"; then
      echo "Package installation failed."
      ((tries++))
      sleep 5
      continue
    fi
    echo "Environment setup successful."
    return 0
  done
  echo "All $max_tries attempts failed. Exiting."
  exit 1
}

clone_repo() {
  rm -rf "$CLONE_DIR"
  echo "Cloning repository..."
  if git clone "$REPO_URL" "$CLONE_DIR"; then
    echo "Repository cloned successfully."
  else
    echo "Git clone failed."
    exit 1
  fi
}

add_user() {
    read -p "Enter username: " username
    while true; do
        read -s -p "Enter password: " password
        echo
        read -s -p "Confirm password: " password_confirm
        echo
        if [ "$password" == "$password_confirm" ]; then
            break
        else
            echo "Passwords do not match. Please try again."
        fi
    done
    hashed_pass=$(openssl passwd -6 "$password")
    if [ -f "$JSON_FILE" ]; then
        jq --arg u "$username" --arg p "$hashed_pass" \
           '.users[0].username = $u | .users[0].enc_password = $p' \
           "$JSON_FILE" > tmp.json && mv tmp.json "$JSON_FILE"
        echo "User updated successfully."
    else
        echo "JSON file not found!"
        exit 1
    fi
}

setup_environment
clone_repo
add_user
echo "Download complete. Run 'python archinstall/sys_setup.py'"
