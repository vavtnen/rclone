import requests
import hashlib
import time
import re
import json
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

# Cookies should be provided via environment variable or command line
# Example: SAPISID=xxx; OSID=xxx; SID=xxx; ...
COOKIES = ""

def parse_cookies(cookie_str):
    cookies = {}
    for item in cookie_str.strip().split(';'):
        item = item.strip()
        if '=' in item:
            key, value = item.split('=', 1)
            cookies[key.strip()] = value.strip()
    return cookies

def generate_sapisidhash(sapisid, origin="https://photos.google.com"):
    timestamp = int(time.time())
    hash_input = f"{timestamp} {sapisid} {origin}"
    hash_value = hashlib.sha1(hash_input.encode()).hexdigest()
    return f"SAPISIDHASH {timestamp}_{hash_value}"

def get_at_token(session, cookies_dict, sapisid):
    url = "https://photos.google.com/unsupportedvideos"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Authorization": generate_sapisidhash(sapisid),
    }
    
    resp = session.get(url, headers=headers, cookies=cookies_dict)
    print(f"Page status: {resp.status_code}, length: {len(resp.text)}")
    
    # Check if we're logged in (look for PhotosUi, not AccountsSignInUi)
    if "AccountsSignInUi" in resp.text:
        print("ERROR: Got login page, not authenticated!")
        return None
    
    if "PhotosUi" in resp.text:
        print("SUCCESS: Got Photos page!")
    
    # Look for SNlM0e token
    match = re.search(r'"SNlM0e":"([^"]+)"', resp.text)
    if match:
        return match.group(1)
    
    return None

def fetch_unsupported_videos(cookies_str):
    cookies_dict = parse_cookies(cookies_str)
    sapisid = cookies_dict.get('SAPISID')
    
    if not sapisid:
        print("Error: SAPISID not found")
        return None
    
    session = requests.Session()
    
    # Get fresh at token
    at_token = get_at_token(session, cookies_dict, sapisid)
    if not at_token:
        print("Error: Could not get at token")
        return None
    
    print(f"Got at token: {at_token[:30]}...")
    
    url = "https://photos.google.com/_/PhotosUi/data/batchexecute"
    
    # Try different request formats
    rpc_data = [[["TLvKMb","[null,null]",None,"generic"]]]
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Authorization": generate_sapisidhash(sapisid),
        "Origin": "https://photos.google.com",
        "Referer": "https://photos.google.com/unsupportedvideos",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Same-Domain": "1",
    }
    
    f_req = json.dumps(rpc_data)
    data = {"f.req": f_req, "at": at_token}
    
    resp = session.post(url, headers=headers, cookies=cookies_dict, data=data)
    print(f"Batchexecute status: {resp.status_code}")
    print(f"Response: {resp.text[:1000] if resp.text else 'empty'}")
    
    return resp.text


@dataclass
class UnsupportedVideo:
    """Represents an unsupported video from Google Photos."""
    media_id: str
    filename: str
    size_bytes: int
    timestamp_ms: int
    thumbnail_url: str
    download_url: str
    checksum: str

    @property
    def date(self) -> datetime:
        """Convert timestamp to datetime."""
        return datetime.fromtimestamp(self.timestamp_ms / 1000)

    @property
    def size_human(self) -> str:
        """Human-readable file size."""
        size = self.size_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def __str__(self) -> str:
        return f"UnsupportedVideo(id={self.media_id[:20]}..., filename={self.filename}, size={self.size_human}, date={self.date})"


def parse_batchexecute_response(response_text: str) -> tuple[Optional[str], List[UnsupportedVideo]]:
    """
    Parse the batchexecute response and extract video entries.

    Returns:
        tuple: (page_token for pagination, list of UnsupportedVideo objects)
    """
    videos = []
    page_token = None

    if not response_text:
        return None, videos

    # Response starts with )]}' followed by newline
    # Find the actual JSON content
    lines = response_text.strip().split('\n')

    # Skip the )]}' prefix if present
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip().startswith(")]}'"):
            start_idx = i + 1
            break

    # Find the TLvKMb response data
    for line in lines[start_idx:]:
        line = line.strip()
        if not line:
            continue

        # Skip the content length line (just a number)
        if line.isdigit():
            continue

        # Look for the wrb.fr TLvKMb response
        if '"wrb.fr","TLvKMb"' in line:
            try:
                # Parse the outer array
                outer = json.loads(line)

                # The structure is [[["wrb.fr","TLvKMb","<inner_json>",...],...]]
                for item in outer:
                    if isinstance(item, list) and len(item) >= 3:
                        if item[0] == "wrb.fr" and item[1] == "TLvKMb":
                            # item[2] is a JSON string containing the actual data
                            inner_json = item[2]
                            if inner_json:
                                inner_data = json.loads(inner_json)

                                # inner_data[0] is the page token
                                if inner_data and len(inner_data) > 0:
                                    page_token = inner_data[0]

                                # inner_data[1] is the list of video entries
                                if inner_data and len(inner_data) > 1 and inner_data[1]:
                                    for entry in inner_data[1]:
                                        if isinstance(entry, list) and len(entry) >= 7:
                                            try:
                                                video = UnsupportedVideo(
                                                    media_id=entry[0],
                                                    filename=entry[1],
                                                    size_bytes=entry[2],
                                                    timestamp_ms=entry[3],
                                                    thumbnail_url=entry[4],
                                                    download_url=entry[5],
                                                    checksum=entry[6],
                                                )
                                                videos.append(video)
                                            except (IndexError, TypeError) as e:
                                                print(f"Warning: Failed to parse video entry: {e}")
                                                print(f"  Entry: {entry[:3]}...")
            except json.JSONDecodeError as e:
                print(f"Warning: JSON decode error: {e}")
                continue

    return page_token, videos


def parse_from_file(filepath: str) -> tuple[Optional[str], List[UnsupportedVideo]]:
    """Parse batchexecute response from a file (for testing)."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Find where the response data begins (after "response data" marker)
    marker = "response data"
    idx = content.find(marker)
    if idx != -1:
        content = content[idx + len(marker):].strip()

    return parse_batchexecute_response(content)


def print_video_info(videos: List[UnsupportedVideo], show_urls: bool = False):
    """Print parsed video information for verification."""
    print(f"\n{'='*60}")
    print(f"Found {len(videos)} unsupported videos")
    print(f"{'='*60}\n")

    for i, video in enumerate(videos, 1):
        print(f"Video {i}:")
        print(f"  Media ID: {video.media_id}")
        print(f"  Filename: {video.filename}")
        print(f"  Size: {video.size_bytes} bytes ({video.size_human})")
        print(f"  Date: {video.date}")
        print(f"  Timestamp: {video.timestamp_ms}")
        print(f"  Checksum: {video.checksum}")
        if show_urls:
            print(f"  Thumbnail: {video.thumbnail_url}")
            print(f"  Download: {video.download_url[:100]}...")
        print()


def validate_videos(videos: List[UnsupportedVideo]) -> bool:
    """Validate parsed video data for correctness."""
    print("\n--- Validation Results ---\n")
    all_valid = True
    vtt_count = 0
    video_count = 0

    for i, video in enumerate(videos, 1):
        issues = []

        # Check media_id format (should be alphanumeric with some special chars)
        if not video.media_id or not re.match(r'^[A-Za-z0-9_-]+$', video.media_id):
            issues.append(f"Invalid media_id format: {video.media_id[:30]}...")

        # Check filename is not empty (can be VTT or actual video file)
        if not video.filename:
            issues.append("Empty filename")
        else:
            # Categorize by type
            if video.filename.endswith('_thumbs.vtt'):
                vtt_count += 1
            else:
                video_count += 1

        # Check size is positive
        if video.size_bytes <= 0:
            issues.append(f"Invalid size: {video.size_bytes}")

        # Check timestamp is reasonable (after 2020, before 2030)
        min_ts = datetime(2020, 1, 1).timestamp() * 1000
        max_ts = datetime(2030, 1, 1).timestamp() * 1000
        if not (min_ts <= video.timestamp_ms <= max_ts):
            issues.append(f"Timestamp out of range: {video.timestamp_ms}")

        # Check thumbnail URL format
        if not video.thumbnail_url.startswith('https://photos.fife.usercontent.google.com/'):
            issues.append(f"Unexpected thumbnail URL: {video.thumbnail_url[:50]}...")

        # Check download URL format
        if not video.download_url.startswith('https://video-downloads.googleusercontent.com/'):
            issues.append(f"Unexpected download URL: {video.download_url[:50]}...")

        # Check checksum format (should be base64-like)
        if not video.checksum or not re.match(r'^[A-Za-z0-9_-]+$', video.checksum):
            issues.append(f"Invalid checksum format: {video.checksum}")

        if issues:
            all_valid = False
            print(f"Video {i} ({video.filename[:50]}): ISSUES FOUND")
            for issue in issues:
                print(f"  - {issue}")
        # Only print OK for first few and last few to reduce noise
        elif i <= 3 or i > len(videos) - 3:
            print(f"Video {i} ({video.filename[:50]}): OK")
        elif i == 4:
            print(f"  ... ({len(videos) - 6} more videos validated) ...")

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total entries: {len(videos)}")
    print(f"  VTT thumbnail files: {vtt_count}")
    print(f"  Actual video files: {video_count}")
    print(f"{'='*60}")
    if all_valid:
        print("All videos validated successfully!")
    else:
        print("Some videos have validation issues.")
    print(f"{'='*60}\n")

    return all_valid


if __name__ == "__main__":
    import sys
    import os

    # Check if we should parse from file or fetch live
    if len(sys.argv) > 1 and sys.argv[1] == "--from-file":
        filepath = sys.argv[2] if len(sys.argv) > 2 else "unsupportedvideos.txt"
        print(f"Parsing from file: {filepath}")
        page_token, videos = parse_from_file(filepath)

        if videos:
            print(f"\nPage token: {page_token[:50] if page_token else 'None'}...")
            print_video_info(videos, show_urls=False)
            validate_videos(videos)
        else:
            print("No videos found in response!")
    else:
        # Fetch live - get cookies from env or command line
        cookies = os.environ.get("GOOGLE_PHOTOS_COOKIES", "")
        if len(sys.argv) > 1:
            cookies = sys.argv[1]

        if not cookies:
            print("Error: No cookies provided.")
            print("Usage:")
            print("  python unsupportedvideos.py --from-file [filepath]  # Parse from saved response")
            print("  python unsupportedvideos.py <cookies>               # Fetch live with cookies")
            print("  GOOGLE_PHOTOS_COOKIES=<cookies> python unsupportedvideos.py")
            sys.exit(1)

        response = fetch_unsupported_videos(cookies)
        if response:
            page_token, videos = parse_batchexecute_response(response)
            if videos:
                print(f"\nPage token: {page_token[:50] if page_token else 'None'}...")
                print_video_info(videos, show_urls=False)
                validate_videos(videos)
            else:
                print("No videos found in response!")
