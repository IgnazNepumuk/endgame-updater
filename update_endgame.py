#!/usr/bin/env python3
import json
import shutil
import string
import sys
import tempfile
import time
import argparse
import hashlib
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime

OWNER = "efogtech"
REPO = "endgame-trackball-config"
API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
POLL_SECONDS = 1
TIMEOUT_SECONDS = 120
HTTP_TIMEOUT_SECONDS = 30

headers={
    "Accept": "application/vnd.github+json",
    "User-Agent": "endgame-trackball-updater"
}

def confirm_action(prompt="Do you want to proceed? (y/n): "):
    while True:
        choice = input(prompt).lower().strip()
        if choice in ['y', 'yes']:
            return True
        if choice in ['n', 'no']:
            return False
        print("Please enter 'y' or 'n'.")


def print_date(asset_date):
    release_date = datetime.strptime(asset_date, "%Y-%m-%dT%H:%M:%SZ")
    release_date = release_date.strftime("%Y-%m-%d")
    return release_date

def get_release(headers: dict = None) -> dict:
    if headers is None:
        headers = {}
    request = Request(
        API_URL,
        data=None,
        headers=headers
    )
    with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        return json.load(response)

def pick_asset(release: dict, is_3395: bool) -> dict:
    wanted = "endgame-paw3395-" if is_3395 else "endgame-"
    blocked = "paw3395"

    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if not name.endswith(".uf2"):
            continue
        if is_3395 and name.startswith(wanted):
            return asset
        if not is_3395 and name.startswith(wanted) and blocked not in name:
            return asset

    variant = "3395" if is_3395 else "normal"
    raise RuntimeError(f"Could not find {variant} firmware in latest release")

def get_specific_release(version_tag, headers: dict = None) -> dict:
    version_tag = "endgame-" +  version_tag
    API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/tags/{version_tag}"
    if headers is None:
        headers = {}
    request = Request(
        API_URL,
        data=None,
        headers=headers
    )
    with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        return json.load(response)


def download_file(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "endgame-trackball-updater"})
    with (
        urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response,
        destination.open("wb") as output,
    ):
        shutil.copyfileobj(response, output)


def is_uf2_drive(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    if (path / "INFO_UF2.TXT").exists():
        return True
    name = path.name.upper()
    return name in {"RPI-RP2", "UF2BOOT"}


def candidate_mount_points() -> list[Path]:
    candidates: list[Path] = []

    if sys.platform.startswith("win"):
        for drive in string.ascii_uppercase:
            candidates.append(Path(f"{drive}:/"))
    else:
        candidates.extend(Path("/media").glob("*/*"))
        candidates.extend(Path("/media").glob("*"))
        candidates.extend(Path("/run/media").glob("*/*"))
        candidates.extend(Path("/run/media").glob("*"))
        candidates.extend(Path("/Volumes").glob("*"))
        candidates.append(Path("/mnt"))
        candidates.extend(Path("/mnt").glob("*"))

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def wait_for_uf2_drive() -> Path:
    print("Put the trackball into reset/bootloader mode now.")
    print("Waiting for the UF2 drive to appear...")

    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        for path in candidate_mount_points():
            if is_uf2_drive(path):
                return path
        time.sleep(POLL_SECONDS)

    raise RuntimeError("Timed out waiting for the UF2 drive")

def calculate_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file:
        while True:
            data = file.read(65536)  # Read the file in 64KB chunks.
            if not data:
                break
            sha256_hash.update(data)
    return sha256_hash.hexdigest()

def verify_hash(downloaded_file, expected_hash):
    calculated_hash = calculate_hash(downloaded_file)
    return calculated_hash == expected_hash


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--paw3395', action='store_true', help='use firmware variant for the PAW3395 sensors')
    parser.add_argument('--version', '-v', type=str, help='specific version to download')
    args = parser.parse_args()

    is_3395 = args.paw3395

    release = latest_release = get_release(headers)

    if args.version:
        release = get_specific_release(args.version, headers)

    print("Checking latest firmware release...")
    asset = pick_asset(release, is_3395)
    asset_name = asset["name"]
    asset_url = asset["browser_download_url"]
    asset_date = asset["updated_at"]
    latest = latest_release.get("tag_name", "unknown")
    latest_date = latest_release.get("created_at")
    asset_digest = asset["digest"].removeprefix("sha256:")
    tag = release.get("tag_name", "unknown")

    print(f"\nLatest release ({print_date(latest_date)}): {latest}")
    print(f"Selected firmware ({print_date(asset_date)}): {asset_name}\n")

    if confirm_action("Do you want to download the selected firmware and copy it to your device? (y/n): "):
        pass
    else:
        print("Action cancelled.")
        sys.exit()

    with tempfile.TemporaryDirectory(prefix="endgame-fw-") as temp_dir:
        firmware_path = Path(temp_dir) / asset_name
        print("Downloading firmware...")
        download_file(asset_url, firmware_path)
        print("Verifying downloaded firmware...")
        if verify_hash(firmware_path, asset_digest):
            print("Downloaded firmware verified successfully.")
        else:
            print("Downloaded file could not be verified, update failed!")
            return 1

        drive = wait_for_uf2_drive()
        target_path = drive / asset_name
        print(f"Copying firmware to {drive}...")
        shutil.copyfile(firmware_path, target_path)

    print("Done. The device should reboot after the copy finishes.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
