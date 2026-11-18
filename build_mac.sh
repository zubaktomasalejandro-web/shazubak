#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p build/cli-spec
PYINSTALLER_CONFIG_DIR="$PWD/build/cache" .venv/bin/python -m PyInstaller \
    --noconfirm --onefile --target-arch arm64 --collect-data yt_dlp_ejs --exclude-module mutagen \
    --specpath build/cli-spec --workpath build/cli --name shazubak "$PWD/shazubak.py"

contents="dist/Shazubak.app/Contents"
mkdir -p "$contents/MacOS" "$contents/Resources"
cp dist/shazubak "$contents/MacOS/shazubak.command"
cp assets/shazubak.icns "$contents/Resources/"

cat > "$contents/MacOS/launch" <<'LAUNCH'
#!/bin/sh
exec /usr/bin/open -b com.apple.Terminal "${0%/*}/shazubak.command"
LAUNCH
chmod +x "$contents/MacOS/launch"

cat > "$contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Shazubak</string>
    <key>CFBundleIdentifier</key>
    <string>com.zubaktomasalejandro.shazubak</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>launch</string>
    <key>CFBundleIconFile</key>
    <string>shazubak.icns</string>
    <key>LSBackgroundOnly</key>
    <true/>
</dict>
</plist>
PLIST

/usr/bin/codesign --force --sign - dist/Shazubak.app
