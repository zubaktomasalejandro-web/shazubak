#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

runtime="$PWD/build/runtime"
mkdir -p "$runtime"
ffmpeg_archive="ffmpeg-9.0.2.tar.xz"
deno_archive="deno-2.9.8-arm64.zip"
deno_release="https://github.com/denoland/deno/releases/download/v2.9.8"

download() {
    local url="$1" file="$2" checksum="$3"
    if [[ ! -f "$runtime/$file" ]]; then
        curl -fLsS --retry 2 "$url" -o "$runtime/$file.part"
        mv "$runtime/$file.part" "$runtime/$file"
    fi
    (cd "$runtime"; printf '%s  %s\n' "$checksum" "$file" | shasum -a 256 -c)
}

download "https://ffmpeg.org/releases/$ffmpeg_archive" "$ffmpeg_archive" \
    8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e
download "$deno_release/deno-aarch64-apple-darwin.zip" "$deno_archive" \
    9f0bf660393da2eaff044cdc7444cb08c73f235849b61d224d825a194ce7c98e
if [[ ! -f "$runtime/deno-LICENSE.md" ]]; then
    curl -fLsS --retry 2 https://raw.githubusercontent.com/denoland/deno/v2.9.8/LICENSE.md \
        -o "$runtime/deno-LICENSE.md"
fi

source="$runtime/ffmpeg-source/ffmpeg-9.0.2"
mkdir -p "$runtime/ffmpeg-source" "$runtime/ffmpeg-standalone"
if [[ ! -d "$source" ]]; then
    tar xf "$runtime/$ffmpeg_archive" -C "$runtime/ffmpeg-source"
fi

ffmpeg_prefix="$runtime/ffmpeg-stage/usr/local"
ffmpeg_options=(
    --prefix=/usr/local --install-name-dir=@loader_path
    --enable-shared --disable-static --disable-autodetect --enable-securetransport
    --enable-zlib --enable-bzlib --disable-ffplay --disable-doc --disable-debug
    --disable-gpl --disable-nonfree
)
(
    cd "$runtime/ffmpeg-standalone"
    export MACOSX_DEPLOYMENT_TARGET=12.0
    if [[ ! -f ffbuild/config.mak ]]; then
        "$source/configure" "${ffmpeg_options[@]}"
    fi
    make -j"$(getconf _NPROCESSORS_ONLN)"
    make install DESTDIR="$runtime/ffmpeg-stage"
)

./build_mac.sh
stage="$(mktemp -d "$PWD/build/dmg.XXXXXXXX")"
trap 'rm -rf "$stage"' EXIT
app="$stage/Shazubak.app"
ditto dist/Shazubak.app "$app"
resources="$app/Contents/Resources"
bin="$resources/bin"
notices="$resources/ThirdParty"
mkdir -p "$bin" "$notices/FFmpeg" "$notices/Deno"
cp "$ffmpeg_prefix/bin/ffmpeg" "$ffmpeg_prefix/bin/ffprobe" "$bin/"
cp -P "$ffmpeg_prefix/lib/"*.dylib "$bin/"
unzip -o "$runtime/$deno_archive" deno -d "$bin"
chmod +x "$bin/"{deno,ffmpeg,ffprobe}

for executable in "$bin/"*; do
    if [[ ! -L "$executable" ]]; then
        codesign --force --sign - "$executable"
    fi
done
cp "$source/COPYING.LGPLv2.1" "$runtime/$ffmpeg_archive" "$notices/FFmpeg/"
{
    printf 'MACOSX_DEPLOYMENT_TARGET=12.0 ./configure'
    printf ' %s' "${ffmpeg_options[@]}"
    printf '\nmake\n'
} > "$notices/FFmpeg/build-config.txt"
cp "$runtime/deno-LICENSE.md" "$notices/Deno/LICENSE.md"
cp LICENSE "$resources/LICENSE"

.venv/bin/python - "$notices" <<'PY'
from importlib.metadata import distributions
from pathlib import Path
from shutil import copy2
import sys
import sysconfig

notices = Path(sys.argv[1])
copy2(Path(sysconfig.get_path("stdlib")) / "LICENSE.txt", notices / "Python-LICENSE.txt")
for distribution in distributions():
    name = distribution.metadata["Name"]
    if name.lower() in {"pip", "mutagen", "pyside6-essentials", "shiboken6"}:
        continue
    for entry in distribution.files or ():
        if not entry.parts[0].endswith(".dist-info"):
            continue
        if "licenses" in entry.parts or entry.name.startswith(("LICENSE", "COPYING", "NOTICE")):
            target = notices / "Python packages" / name / Path(*entry.parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            copy2(entry.locate(), target)
PY

codesign --force --sign - "$app"
codesign --verify --deep --strict "$app"
ln -s /Applications "$stage/Applications"
cat > "$stage/Instalar.txt" <<'INSTALL'
Shazubak para Mac con Apple Silicon
Los binarios tienen macOS 12 como objetivo mínimo.

1. Arrastra Shazubak a Applications (Aplicaciones).
2. Abre Shazubak desde Aplicaciones. Se abrirá Terminal.
3. Pega un enlace de YouTube o SoundCloud y pulsa Intro.

No requiere Homebrew ni instalar Python, FFmpeg, FFprobe o Deno.
La descarga y el reconocimiento de canciones requieren Internet.
La app lleva firma local ad hoc y carece de notarización de Apple.
INSTALL

hdiutil create -ov -format UDZO -fs HFS+ -volname Shazubak \
    -srcfolder "$stage" dist/Shazubak-macOS-arm64.dmg
hdiutil verify dist/Shazubak-macOS-arm64.dmg
