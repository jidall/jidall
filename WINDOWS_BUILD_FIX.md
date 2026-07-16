# Windows build fix 1.0.2

This branch replaces fragile CMD path handling with a PowerShell build pipeline that safely supports spaces and parentheses in project paths, writes `build_installer.log`, validates the PyInstaller executable, locates Inno Setup 6, validates the generated installer, and keeps the launcher window open on success or failure.
