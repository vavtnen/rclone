#!/usr/bin/env python3
"""
Alternative: Direct HTTP approach using /o/android/auth endpoint.
This tries to use the older Android auth flow which may not require JS challenges.
"""

import re
import json
import time
import random
import httpx
from urllib.parse import urlencode, parse_qs, urlparse

EMAIL = "your_email@gmail.com"
PASSWORD = "your_password"
ANDROID_ID = "de0a0dc373653ca4"  # 16 hex chars

# Chromecast app credentials (known working)
APP = "com.google.android.apps.chromecast.app"
CLIENT_SIG = "24bb24c05e47e0aefa68a58a766179d9b613a600"
GPS_VERSION = "240913000"

USER_AGENT = "GoogleAuth/1.4 (Nexus 5 LMY48M); gzip"


def method1_embedded_setup_flow(email: str, password: str) -> dict:
    """
    Try EmbeddedSetup flow via direct HTTP.
    This may fail due to JS challenges.
    """
    print("=" * 60)
    print("Method 1: EmbeddedSetup HTTP Flow")
    print("=" * 60)

    client = httpx.Client(follow_redirects=True, timeout=30.0)

    # Step 1: Load EmbeddedSetup
    print("\n[1] Loading EmbeddedSetup...")
    url = "https://accounts.google.com/EmbeddedSetup"
    params = {
        "source": "android",
        "xoauth_display_name": "Android Device",
        "lang": "en",
        "cc": "US",
    }
    response = client.get(url, params=params)
    print(f"  Status: {response.status_code}")

    # Extract tokens
    html = response.text
    f_sid = re.search(r'"FdrFJe":"(-?\d+)"', html)
    at_token = re.search(r'"SNlM0e":"([^"]+)"', html)
    bl = re.search(r'"cfb2h":"([^"]+)"', html)

    if f_sid:
        print(f"  f.sid: {f_sid.group(1)}")
    if at_token:
        print(f"  at: {at_token.group(1)[:30]}...")
    if bl:
        print(f"  bl: {bl.group(1)}")

    # Print cookies
    print("\n  Cookies:")
    for cookie in client.cookies.jar:
        print(f"    {cookie.name}: {cookie.value[:30]}...")

    client.close()
    return {}


def method2_android_auth_direct(email: str, password: str) -> dict:
    """
    Try older /o/android/auth flow with direct credentials.
    This is the flow that gpsoauth's perform_master_login uses.
    """
    print("\n" + "=" * 60)
    print("Method 2: Direct android.googleapis.com/auth")
    print("=" * 60)

    url = "https://android.googleapis.com/auth"

    # Build encrypted password (for gpsoauth compatibility)
    # Note: This requires the gpsoauth library's encryption
    # For now, try with plaintext password

    data = {
        "Email": email,
        "Passwd": password,  # Plain password
        "app": APP,
        "client_sig": CLIENT_SIG,
        "service": "ac2dm",  # Get master token
        "androidId": ANDROID_ID,
        "device_country": "us",
        "operatorCountry": "us",
        "lang": "en",
        "sdk_version": "28",
        "google_play_services_version": GPS_VERSION,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": USER_AGENT,
    }

    print("\n[1] Requesting master token with Passwd...")
    client = httpx.Client()
    response = client.post(url, data=data, headers=headers)

    print(f"  Status: {response.status_code}")
    print(f"  Response:\n{response.text[:500]}")

    result = {}
    for line in response.text.strip().split('\n'):
        if '=' in line:
            k, v = line.split('=', 1)
            result[k] = v

    if "Token" in result:
        print(f"\n  SUCCESS! Master token: {result['Token'][:40]}...")
    elif "Error" in result:
        print(f"\n  Error: {result['Error']}")
        if result.get("Error") == "NeedsBrowser":
            print("  -> Needs browser authentication (EmbeddedSetup)")
        elif result.get("Error") == "BadAuthentication":
            print("  -> Bad authentication (password may need encryption)")

    client.close()
    return result


def method3_gpsoauth_encrypted(email: str, password: str) -> dict:
    """
    Use gpsoauth library with proper encryption.
    """
    print("\n" + "=" * 60)
    print("Method 3: gpsoauth with proper encryption")
    print("=" * 60)

    try:
        import gpsoauth

        print("\n[1] Performing master login...")
        result = gpsoauth.perform_master_login(
            email=email,
            password=password,
            android_id=ANDROID_ID,
        )

        print(f"  Result keys: {list(result.keys())}")

        if "Token" in result:
            master_token = result["Token"]
            print(f"  Master token: {master_token[:40]}...")

            # Now try to get OAuthLogin token
            print("\n[2] Getting OAuthLogin token...")
            oauth_result = gpsoauth.perform_oauth(
                email=email,
                master_token=master_token,
                android_id=ANDROID_ID,
                service="oauth2:https://www.google.com/accounts/OAuthLogin",
                app=APP,
                client_sig=CLIENT_SIG,
            )

            print(f"  OAuth result keys: {list(oauth_result.keys())}")

            if "Auth" in oauth_result:
                auth_token = oauth_result["Auth"]
                print(f"  Auth token: {auth_token[:40]}...")

                # Now get uberauth
                print("\n[3] Getting uberauth...")
                client = httpx.Client(follow_redirects=True)
                uber_response = client.get(
                    "https://accounts.google.com/accounts/OAuthLogin",
                    params={"source": "hangups", "issueuberauth": "1"},
                    headers={"Authorization": f"Bearer {auth_token}"},
                )
                uberauth = uber_response.text.strip()
                print(f"  Uberauth: {uberauth[:40]}...")

                # Merge session
                print("\n[4] Merging session...")
                merge_response = client.get(
                    "https://accounts.google.com/MergeSession",
                    params={
                        "uberauth": uberauth,
                        "continue": "https://www.google.com/",
                    },
                    headers={"Authorization": f"Bearer {auth_token}"},
                )

                print(f"  Cookies:")
                cookies = {}
                for cookie in client.cookies.jar:
                    cookies[cookie.name] = cookie.value
                    print(f"    {cookie.name}: {cookie.value[:30]}...")

                client.close()
                return {"master_token": master_token, "cookies": cookies}

            else:
                print(f"  Error: {oauth_result.get('Error', 'Unknown')}")

        else:
            print(f"  Error: {result.get('Error', 'Unknown')}")
            if result.get("Error") == "NeedsBrowser":
                print("  -> Try using EmbeddedSetup flow with browser")

    except ImportError:
        print("  gpsoauth not installed. Run: pip install gpsoauth")
    except Exception as e:
        print(f"  Error: {e}")

    return {}


def method4_exchange_token(oauth_token: str, email: str) -> dict:
    """
    Exchange oauth_token (from EmbeddedSetup) for master token.
    Use this after getting oauth_token from browser login.
    """
    print("\n" + "=" * 60)
    print("Method 4: Exchange oauth_token for master token")
    print("=" * 60)

    if not oauth_token:
        print("  No oauth_token provided")
        return {}

    try:
        import gpsoauth

        print(f"\n[1] Exchanging oauth_token: {oauth_token[:40]}...")

        result = gpsoauth.exchange_token(
            email=email,
            token=oauth_token,
            android_id=ANDROID_ID,
        )

        print(f"  Result keys: {list(result.keys())}")

        if "Token" in result:
            print(f"  Master token: {result['Token'][:40]}...")
            return result
        else:
            print(f"  Error: {result.get('Error', 'Unknown')}")

    except ImportError:
        print("  gpsoauth not installed")
    except Exception as e:
        print(f"  Error: {e}")

    return {}


def main():
    # Try different methods
    method1_embedded_setup_flow(EMAIL, PASSWORD)
    method2_android_auth_direct(EMAIL, PASSWORD)
    method3_gpsoauth_encrypted(EMAIL, PASSWORD)

    # If you have oauth_token from Playwright/browser, use this:
    # oauth_token = "oauth2_4/0ASc3gC..."
    # method4_exchange_token(oauth_token, EMAIL)


if __name__ == "__main__":
    main()
