#!/usr/bin/env python3
"""
Cookie Parser for rclone mediavfs configuration.

This script parses browser cookies and outputs them in rclone config format
for the mediavfs unsupported videos feature.

Usage:
    1. Copy cookies from browser (as string or from exported file)
    2. Run: python cookie_parser.py "cookie_string_here"
    3. Copy output to rclone config

Or paste cookies interactively:
    python cookie_parser.py
"""

import sys
import re


# Mapping of browser cookie names to rclone config option names
COOKIE_TO_CONFIG = {
    'SAPISID': 'web_sapisid',
    'SID': 'web_sid',
    'HSID': 'web_hsid',
    'SSID': 'web_ssid',
    'OSID': 'web_osid',
    '__Secure-1PSID': 'web_1psid',
    '__Secure-3PSID': 'web_3psid',
    'APISID': 'web_apisid',
    '__Secure-1PAPISID': 'web_1papisid',
    '__Secure-3PAPISID': 'web_3papisid',
}

# Required cookies for the API to work
REQUIRED_COOKIES = ['SAPISID', 'SID', 'HSID', 'SSID']


def parse_cookies(cookie_str: str) -> dict:
    """Parse cookie string into dictionary."""
    cookies = {}
    for item in cookie_str.strip().split(';'):
        item = item.strip()
        if '=' in item:
            key, value = item.split('=', 1)
            cookies[key.strip()] = value.strip()
    return cookies


def cookies_to_rclone_config(cookies: dict) -> str:
    """Convert cookies dict to rclone config format."""
    lines = []
    missing = []

    for cookie_name, config_name in COOKIE_TO_CONFIG.items():
        value = cookies.get(cookie_name, '')
        if value:
            lines.append(f'{config_name} = {value}')
        elif cookie_name in REQUIRED_COOKIES:
            missing.append(cookie_name)

    if missing:
        print(f"WARNING: Missing required cookies: {', '.join(missing)}", file=sys.stderr)
        print("The unsupported videos feature may not work without these.", file=sys.stderr)
        print("", file=sys.stderr)

    return '\n'.join(lines)


def main():
    if len(sys.argv) > 1:
        # Cookie string provided as argument
        cookie_str = sys.argv[1]
    else:
        # Read from stdin
        print("Paste your cookies (from browser, one line, then press Enter):", file=sys.stderr)
        print("(You can get cookies from browser DevTools > Application > Cookies)", file=sys.stderr)
        print("", file=sys.stderr)
        cookie_str = input()

    cookies = parse_cookies(cookie_str)

    if not cookies:
        print("ERROR: No cookies found in input", file=sys.stderr)
        sys.exit(1)

    print(f"# Found {len(cookies)} cookies", file=sys.stderr)
    print(f"# Mapped {sum(1 for c in COOKIE_TO_CONFIG if c in cookies)} to rclone config", file=sys.stderr)
    print("", file=sys.stderr)
    print("# Add these lines to your rclone config [remote] section:", file=sys.stderr)
    print("# --------------------------------------------------------", file=sys.stderr)
    print("")

    config = cookies_to_rclone_config(cookies)
    print(config)


if __name__ == '__main__':
    main()
