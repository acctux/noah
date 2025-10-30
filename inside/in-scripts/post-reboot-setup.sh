pass_files_to_user() {
  rsync -ac --no-owner --no-group "$HOME/$INSTALL_SCRIPT/" "$USER_HOME/$INSTALL_SCRIPT/"
  rsync -ac --no-owner --no-group "$HOME/$KEY_DIR/" "$USER_HOME/$KEY_DIR/"
  chmod 600 "$USER_HOME/$KEY_DIR/$SSH_KEYFILE"
  chmod 600 "$USER_HOME/$KEY_DIR/$GPG_KEYFILE"
  chown -R "$USER_NAME:$USER_NAME" "$USER_HOME/$INSTALL_SCRIPT" "$USER_HOME/$KEY_DIR"
}

create_autostart() {
  local autostart_dir="$USER_HOME/.config/autostart"
  local desktop_file="$autostart_dir/post.desktop"
  local exec_command="alacritty -e \"$POST_SCRIPT\""

  mkdir -p "$autostart_dir"
  chmod +x "$POST_SCRIPT"

  cat >"$desktop_file" <<EOF
[Desktop Entry]
Type=Application
Name=Final touches
Exec=sh -c 'sleep 5 && $exec_command'
Terminal=false
NoDisplay=true
EOF

  success "Created: $desktop_file"
}

userfiles_and_autostart() {
  pass_files_to_user
  create_autostart
}
