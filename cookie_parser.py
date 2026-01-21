#!/usr/bin/env python3
"""
Cookie Parser for rclone mediavfs configuration.

This script takes browser cookies and outputs them in the format needed
for the mediavfs web_cookies config option.

Usage:
    1. Run: python cookie_parser.py
    2. Paste your cookies when prompted
    3. Copy the output to your rclone config as web_cookies value
"""

import sys


def main():
    print("Paste your cookies (from browser, one line, then press Enter):", file=sys.stderr)
    print("(Get cookies from browser DevTools > Application > Cookies > photos.google.com)", file=sys.stderr)
    print("", file=sys.stderr)

    cookie_str = input().strip()

    if not cookie_str:
        print("ERROR: No cookies provided", file=sys.stderr)
        sys.exit(1)

    # Validate that we have the required cookies
    cookies = {}
    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            key, value = item.split('=', 1)
            cookies[key.strip()] = value.strip()

    # Check for required cookies
    required = ['SAPISID', 'SID']
    missing = [c for c in required if c not in cookies]

    if missing:
        print(f"WARNING: Missing required cookies: {', '.join(missing)}", file=sys.stderr)
        print("The unsupported videos feature may not work without these.", file=sys.stderr)
        print("", file=sys.stderr)

    print(f"# Found {len(cookies)} cookies", file=sys.stderr)
    print("", file=sys.stderr)
    print("# Add this to your rclone config [remote] section:", file=sys.stderr)
    print("# --------------------------------------------------------", file=sys.stderr)
    print("")
    print(f"web_cookies = {cookie_str}")


if __name__ == '__main__':
    main()
