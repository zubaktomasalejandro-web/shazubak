# shazubak

A free command-line tool for Windows and macOS that scans long DJ sets from YouTube or SoundCloud, identifies tracks with Shazam, and generates a timestamped tracklist.

## Features

- Automatic track recognition for long DJ sets
- YouTube and SoundCloud support
- Timestamped tracklists
- Low-confidence detections separated automatically
- Portable Windows release and self-contained macOS disk image
- Optional temporary YouTube login for restricted videos
- Temporary Firefox login data is deleted after the authenticated download attempt

## How it works

Shazubak analyzes a 12-second audio sample every 30 seconds.

Tracks identified more than once are added to the main tracklist.

Tracks identified only once are listed under:

`LOW RELIABILITY`

These detections may still be correct, but may also correspond to samples, short overlaps, or false positives.

## Windows version

Download the Windows ZIP from [Shazubak 1.0.0](https://github.com/zubaktomasalejandro-web/shazubak/releases/tag/V1.0.0).

Extract the ZIP and run:

`shazubak.exe`

Do not move or delete the `program files` folder.

## macOS version

Download `Shazubak-macOS-arm64.dmg` from [GitHub Releases](https://github.com/zubaktomasalejandro-web/shazubak/releases).
Mount the disk image, drag Shazubak to Applications, and open the app to paste a set link in Terminal.

The disk image includes Python, FFmpeg, FFprobe, and Deno. It targets Apple Silicon and macOS 12 or later and was tested on macOS 26.6. The app uses an ad hoc signature and is not notarized, so Gatekeeper may block its first launch.

## Restricted YouTube videos

Most videos work without authentication.

If YouTube requires you to sign in, shazubak first lets the normal download process fail completely and then checks whether the error is actually authentication-related.

On macOS, enter the name of your browser to authorize use of its current session for that download. Press Enter to cancel. Shazubak does not export a cookie file.

On Windows, Shazubak offers to open the included Firefox Portable instance.

1. Log in to YouTube in Firefox Portable.
2. Confirm that you can open the restricted video.
3. Close Firefox Portable completely.
4. Return to Shazubak and press ENTER.

The program then temporarily uses that Firefox session for the download.

After the authenticated download attempt, the temporary Firefox profile is deleted automatically.

## Output

On macOS, tracklists are saved in `~/Music/Shazubak/tracklists/`. On Windows, they go in `tracklists/` beside the executable.

Example:

```text
TRACKLIST
==================================================

00:30 — Artist - Track
04:00 — Artist - Track
08:30 — Artist - Track


LOW RELIABILITY
==================================================

12:00 — Artist - Track
```

## Running from source

Requirements:

- Python 3.12 or 3.13
- FFmpeg
- FFprobe
- Deno

Install the Python dependencies with:

```bash
pip install -r requirements.txt
```

On Windows, the portable executables go in:

```text
program files/
├── ffmpeg.exe
├── ffprobe.exe
├── deno.exe
└── FirefoxPortable/
```

## macOS Apple Silicon

Build the command-line executable and the Finder app on an Apple Silicon Mac:

```bash
brew install ffmpeg deno
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./build_mac.sh
```

Double-click `dist/Shazubak.app` in Finder to open Shazubak in Terminal. You can also run `./dist/shazubak` directly. The executable includes Python dependencies and looks for `ffmpeg`, `ffprobe` and `deno` on your PATH or in `/opt/homebrew/bin`.

### Self-contained macOS disk image

On an Apple Silicon Mac, install the Xcode Command Line Tools and the Python
requirements above, then run `./build_dmg.sh`. It downloads and verifies the
pinned FFmpeg source and Deno release, builds FFmpeg, and creates
`dist/Shazubak-macOS-arm64.dmg`.

Internet access is required to download media and recognize tracks.

## Building the Windows executable

```bash
pyinstaller --onefile --collect-data yt_dlp_ejs --name shazubak shazubak.py
```

The executable will be created inside:

`dist/`

## Notes

Track timestamps are approximate and correspond to the first moment at which the track was detected.

Music recognition depends on Shazam and may not identify unreleased, heavily edited, obscure, or highly overlapped tracks.

Use Shazubak only with content you are permitted to access and download. Users are responsible for complying with applicable copyright law and the terms of the source platform.

## License

MIT

---

*hope your set is fire.*  
**tomás zubak**
