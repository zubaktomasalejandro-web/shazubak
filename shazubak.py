import os
import re
import json
import asyncio
import subprocess
import sys
import ssl
import shutil
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from pathlib import Path
import certifi
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


def get_app_directory():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


APP_DIR = get_app_directory()

PROGRAM_FILES_DIR = APP_DIR / "program files"
TRACKLISTS_DIR = (
    Path.home() / "Music" / "Shazubak" / "tracklists"
    if sys.platform == "darwin"
    else APP_DIR / "tracklists"
)


def tool_path(name):
    executable = f"{name}.exe" if os.name == "nt" else name
    folders = [PROGRAM_FILES_DIR]
    if sys.platform == "darwin":
        folders.insert(0, APP_DIR.parent / "Resources" / "bin")

    for folder in folders:
        bundled = folder / executable
        if bundled.is_file() and os.access(bundled, os.X_OK):
            return str(bundled)

    path = shutil.which(name)
    if path:
        return path

    if sys.platform == "darwin":
        homebrew = Path("/opt/homebrew/bin") / name
        if homebrew.is_file() and os.access(homebrew, os.X_OK):
            return str(homebrew)

    raise FileNotFoundError(f"{name} was not found in {PROGRAM_FILES_DIR} or PATH.")

FIREFOX_PORTABLE_DIR = PROGRAM_FILES_DIR / "FirefoxPortable"
FIREFOX_PORTABLE = str(FIREFOX_PORTABLE_DIR / "FirefoxPortable.exe")
FIREFOX_PROFILE = FIREFOX_PORTABLE_DIR / "Data" / "profile"

# ============================================================
# CONFIGURATION
# ============================================================

# How often the set is analyzed
INTERVAL = 30

# Duration of the fragment sent to Shazam
SAMPLE_DURATION = 12

# If the same track reappears within this time window,
# it is considered part of the same group
MAX_TRACK_GAP = 120


# ============================================================
# UTILITIES
# ============================================================

def sanitize_filename(name):
    """
    Removes characters that Windows does not allow
    in file names.
    """

    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name)
    name = name.strip().rstrip(".")

    if not name:
        return "unknown"

    return name[:150]


def format_time(seconds):
    seconds = max(0, int(seconds))

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours:02}:{minutes:02}:{secs:02}"

    return f"{minutes:02}:{secs:02}"


def track_key(artist, title):
    return (
        artist.strip().lower(),
        title.strip().lower()
    )


# ============================================================
# YOUTUBE AUTHENTICATION HELPERS
# ============================================================

def is_youtube_url(url):
    host = urlsplit(url).hostname or ""
    return host in {"youtube.com", "youtu.be"} or host.endswith(".youtube.com")


def requires_youtube_auth(error):
    message = str(error).lower()

    auth_indicators = [
        "sign in",
        "login required",
        "login to confirm",
        "confirm your age",
        "age-restricted",
        "age restricted",
        "members-only",
        "members only",
        "private video",
        "this video is private",
        "authentication required",
        "cookies",
        "not a bot",
    ]

    return any(
        indicator in message
        for indicator in auth_indicators
    )


def open_firefox_for_login(url):

    if not os.path.exists(FIREFOX_PORTABLE):

        print()
        print(
            "ERROR: Could not find Firefox Portable."
        )

        print(
            "Expected path:"
        )

        print(
            f"  {FIREFOX_PORTABLE}"
        )

        return False

    print()
    print("=" * 70)
    print("YOUTUBE AUTHENTICATION")
    print("=" * 70)

    print()

    print(
        "Firefox Portable will now open."
    )

    print()

    print(
        "1. Log in to YouTube."
    )

    print(
        "2. Make sure you can open the video in Firefox."
    )

    print(
        "3. CLOSE Firefox Portable completely."
    )

    print(
        "4. Return to this window."
    )

    print()

    try:

        subprocess.Popen([
            FIREFOX_PORTABLE,
            url
        ])

    except Exception as e:

        print(
            "Could not open Firefox Portable:"
        )

        print(e)

        return False

    input(
        "Once Firefox is completely closed, "
        "press ENTER to continue..."
    )

    return True


def delete_firefox_credentials():

    print()

    print(
        "Removing temporary login data..."
    )

    try:

        if FIREFOX_PROFILE.exists():

            shutil.rmtree(
                FIREFOX_PROFILE
            )

        FIREFOX_PROFILE.mkdir(
            parents=True,
            exist_ok=True
        )

        print(
            "Login data removed."
        )

    except Exception as e:

        print()

        print(
            "WARNING: Could not completely remove "
            "Firefox Portable login data."
        )

        print(
            "Make sure Firefox is closed."
        )

        print(
            f"Details: {e}"
        )


# ============================================================
# DOWNLOAD
# ============================================================

def download_with_options(url, options):
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info), info.get("title", "unknown")


BROWSERS = ("Safari", "Chrome", "Firefox", "Edge", "Brave")


def ask_browser():
    return input(
        "YouTube requires authentication. To use your browser session for "
        f"this download, enter its name ({', '.join(BROWSERS)}), or press Enter to cancel: "
    ).strip()


def download_audio(url, temp_dir):
    options = {
        "format": "bestaudio/best",
        "outtmpl": str(temp_dir / "input_audio.%(ext)s"),
        "noplaylist": True,
        "cachedir": False,
        "ffmpeg_location": tool_path("ffmpeg"),
        "js_runtimes": {"deno": {"path": tool_path("deno")}},
    }

    print("\nDownloading audio...")
    try:
        return download_with_options(url, options)
    except DownloadError as error:
        if not is_youtube_url(url) or not requires_youtube_auth(error):
            raise

        if os.name != "nt":
            browser = ask_browser().lower()
            if browser not in {name.lower() for name in BROWSERS}:
                raise

            return download_with_options(
                url, {**options, "cookiesfrombrowser": (browser,)}
            )

        answer = input("Sign in using Firefox Portable? [Y/n]: ").strip().lower()
        if answer not in {"", "y", "yes"}:
            raise

    if not open_firefox_for_login(url):
        raise RuntimeError("Could not start Firefox Portable.")

    try:
        return download_with_options(
            url, {**options, "cookiesfrombrowser": ("firefox", str(FIREFOX_PROFILE))}
        )
    finally:
        delete_firefox_credentials()


def find_downloaded_audio(temp_dir):
    for path in temp_dir.glob("input_audio.*"):
        if not path.name.endswith((".part", ".ytdl")) and ".part-Frag" not in path.name:
            return path
    return None


# ============================================================
# FFMPEG
# ============================================================

def get_duration(filename):

    command = [
        tool_path("ffprobe"),
        "-v", "quiet",
        "-show_entries",
        "format=duration",
        "-of", "json",
        filename
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True
    )

    data = json.loads(
        result.stdout
    )

    return float(
        data["format"]["duration"]
    )


def extract_sample(
    filename,
    start_time,
    sample_path
):

    command = [
        tool_path("ffmpeg"),
        "-y",
        "-loglevel", "quiet",
        "-ss", str(start_time),
        "-i", filename,
        "-t", str(
            SAMPLE_DURATION
        ),
        "-vn",
        "-ac", "1",
        "-ar", "44100",
        sample_path
    ]

    subprocess.run(
        command,
        check=True
    )


# ============================================================
# SHAZAM
# ============================================================

async def recognize_sample(shazam, sample_path):
    from shazamio_core import SignatureError

    try:
        result = await shazam.recognize(sample_path)
    except SignatureError:
        return None

    track = result.get("track")
    if not track:
        return None

    return {
        "artist": track.get("subtitle", "Unknown artist"),
        "title": track.get("title", "Unknown title"),
    }


# ============================================================
# ANALYSIS
# ============================================================

async def analyze_audio(
    audio_file,
    sample_path,
):

    duration = get_duration(
        audio_file
    )

    print()
    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)

    print(
        f"File: {audio_file}"
    )

    print(
        f"Duration: {format_time(duration)}"
    )

    print()

    if sys.platform == "darwin" and ssl.get_default_verify_paths().cafile is None:
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())

    from aiohttp import ClientConnectionError, ClientSSLError
    from shazamio import Shazam

    detections = []

    current_time = 0

    async with Shazam() as shazam:
        while current_time < duration:
            timestamp = format_time(current_time)
            extract_sample(audio_file, current_time, sample_path)
            result = None
            for attempt in range(3):
                try:
                    result = await recognize_sample(shazam, sample_path)
                except ClientSSLError:
                    raise
                except (ClientConnectionError, TimeoutError):
                    if attempt == 2:
                        print(f"{timestamp}  →  Skipped (Shazam connection failed)")
                        break
                    await asyncio.sleep(2 ** attempt)
                else:
                    if result:
                        print(f"{timestamp}  →  {result['artist']} - {result['title']}")
                    else:
                        print(f"{timestamp}  →  Not identified")
                    break

            detections.append({
                "time": current_time,
                **(result or {"artist": None, "title": None}),
            })
            current_time += INTERVAL

    return detections


# ============================================================
# DETECTION GROUPING
# ============================================================

def summarize_detections(
    detections
):

    groups = []

    for detection in detections:

        if (
            detection["artist"]
            is None
        ):

            continue

        key = track_key(
            detection["artist"],
            detection["title"]
        )

        matching_group = None

        # Check whether the same track appeared recently.
        #
        # This allows cases such as:
        #
        # 32:00 Track A
        # 32:30 Track B
        # 33:00 Track C
        # 33:30 Track A
        #
        # Track A is still grouped together.

        for group in reversed(
            groups
        ):

            if (
                group["key"]
                != key
            ):

                continue

            gap = (
                detection["time"]
                -
                group["times"][-1]
            )

            if (
                gap
                <= MAX_TRACK_GAP
            ):

                matching_group = (
                    group
                )

            break

        if matching_group:

            matching_group[
                "times"
            ].append(
                detection["time"]
            )

        else:

            groups.append({

                "key":
                    key,

                "artist":
                    detection["artist"],

                "title":
                    detection["title"],

                "times": [
                    detection["time"]
                ]
            })

    groups.sort(
        key=lambda group:
            group["times"][0]
    )

    return groups


# ============================================================
# SAVE TRACKLIST
# ============================================================

def save_tracklist_txt(
    groups,
    filename
):

    reliable = [

        group
        for group in groups

        if len(
            group["times"]
        ) >= 2
    ]

    low_reliability = [

        group
        for group in groups

        if len(
            group["times"]
        ) == 1
    ]

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "TRACKLIST\n"
        )

        f.write(
            "=" * 50
        )

        f.write(
            "\n\n"
        )

        if reliable:

            for group in reliable:

                timestamp = (
                    format_time(
                        group[
                            "times"
                        ][0]
                    )
                )

                f.write(
                    f"{timestamp} — "
                    f"{group['artist']} - "
                    f"{group['title']}\n"
                )

        else:

            f.write(
                "No tracks with multiple "
                "detections were found.\n"
            )

        if low_reliability:

            f.write(
                "\n\n"
            )

            f.write(
                "LOW RELIABILITY\n"
            )

            f.write(
                "=" * 50
            )

            f.write(
                "\n\n"
            )

            for group in (
                low_reliability
            ):

                timestamp = (
                    format_time(
                        group[
                            "times"
                        ][0]
                    )
                )

                f.write(
                    f"{timestamp} — "
                    f"{group['artist']} - "
                    f"{group['title']}\n"
                )


# ============================================================
# DISPLAY RESULTS
# ============================================================

def print_tracklist(
    groups
):

    reliable = [

        group
        for group in groups

        if len(
            group["times"]
        ) >= 2
    ]

    low_reliability = [

        group
        for group in groups

        if len(
            group["times"]
        ) == 1
    ]

    print()
    print("=" * 70)
    print("TRACKLIST")
    print("=" * 70)

    if reliable:

        for group in reliable:

            timestamp = (
                format_time(
                    group["times"][0]
                )
            )

            print(
                f"{timestamp}  —  "
                f"{group['artist']} - "
                f"{group['title']} "
                f"({len(group['times'])} "
                "detections)"
            )

    else:

        print(
            "No tracks with multiple "
            "detections were found."
        )

    if low_reliability:

        print()
        print("-" * 70)
        print("LOW RELIABILITY")
        print("-" * 70)

        for group in (
            low_reliability
        ):

            timestamp = (
                format_time(
                    group["times"][0]
                )
            )

            print(
                f"{timestamp}  —  "
                f"{group['artist']} - "
                f"{group['title']} "
                "(1 detection)"
            )


# ============================================================
# MAIN
# ============================================================

async def main():

    print()
    print("=" * 70)
    print("SHAZUBAK")
    print("=" * 70)

    print(
        "hope your set is fire. "
        "tomás zubak"
    )

    print()

    url = input(
        "Paste a link:\n> "
    ).strip()

    if not url:

        print(
            "No link was entered."
        )

        return

    try:
        _, groups, filename = await run_analysis(url)
    except Exception as error:
        print(f"\nERROR: {error}")
        return

    print_tracklist(groups)
    print(f"\nTracklist saved to:\n  {filename}")


async def run_analysis(url):
    for name in ("ffmpeg", "ffprobe", "deno"):
        tool_path(name)

    with TemporaryDirectory(prefix="shazubak-") as directory:
        temp_dir = Path(directory)
        audio_file, title = download_audio(url, temp_dir)
        if not Path(audio_file).is_file():
            audio_file = find_downloaded_audio(temp_dir)
        if audio_file is None:
            raise FileNotFoundError("Could not find the downloaded audio.")

        print(f"\nTitle: {title}")
        detections = await analyze_audio(audio_file, str(temp_dir / "sample.wav"))

    groups = summarize_detections(detections)
    TRACKLISTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = TRACKLISTS_DIR / f"tracklist_{sanitize_filename(title)}.txt"
    save_tracklist_txt(groups, filename)
    return title, groups, filename


if __name__ == "__main__":
    asyncio.run(main())
