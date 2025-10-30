pass_files_to_user() {
  rsync -a "$HOME/$INSTALL_SCRIPT/" "$USER_HOME/$INSTALL_SCRIPT/"
  rsync -a "$HOME/$KEY_DIR/" "$USER_HOME/$KEY_DIR/"

  chmod 600 "$USER_HOME/$KEY_DIR/$SSH_KEYFILE"
  chmod 600 "$USER_HOME/$KEY_DIR/$GPG_KEYFILE"
  chown -R "$USER_NAME:$USER_NAME" "$USER_HOME/$INSTALL_SCRIPT" "$USER_HOME/$KEY_DIR"
}

create_autostart() {
  local autostart_dir="$USER_HOME/.config/autostart"
  local desktop_file="$autostart_dir/post.desktop"
  local post_script="$USER_HOME/$INSTALL_SCRIPT/no_moah"
  local exec_command="alacritty -e \"$post_script\""

  mkdir -p "$autostart_dir"
  chmod +x "$post_script"

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
user_files_and_autostart() {
  pass_files_to_user
  create_autostart
}
