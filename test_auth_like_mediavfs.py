#!/usr/bin/env python3
"""
Get web cookies using the same auth flow as mediavfs/gphoto/auth.go
Uses the exact parameters that work for Google Photos tokens.
"""

import httpx
import gzip

# From your working rclone config
MASTER_TOKEN = "aas_et/AKppINbxJUkqyuy_M4aaEgUbCrcvqH4Du6T_1CxsLBTuHZInXJefSHfjjV90a2-fIF5Q4XIPMLH3jFmAEVuq1PhVINyRyPz3Xhu6MuZ60zB-TN5jzIE0gxo_qtO3cIvvIxrWvwt70eQogJnjx13dVXY6CVF4rp94tVmo8BRX6vu4VtOGHqMjjhF6jfWckTuUfhxziduPB_QbCMu-ZarNEjs="
EMAIL = "tinhlo@gmail.com"
ANDROID_ID = "38106360b2a855e1"

# Constants from auth.go (lines 31-38)
GMS_VERSION = "254730032"  # google_play_services_version
SDK_VERSION = "33"
PHOTOS_VERSION = "51079550"
PHOTOS_CLIENT_SIG = "24bb24c05e47e0aefa68a58a766179d9b613a600"

AUTH_URL = "https://android.googleapis.com/auth"
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "GoogleAuth/1.4 (generic_x86 PPR1.180610.011); gzip",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
}


def parse_response(text: str) -> dict:
    """Parse key=value response."""
    result = {}
    for line in text.strip().split('\n'):
        if '=' in line:
            k, v = line.split('=', 1)
            result[k] = v
    return result


def test_photos_scope():
    """Test with the exact parameters from auth.go that work for Google Photos."""
    print("=" * 60)
    print("Test 1: Google Photos scope (should work)")
    print("=" * 60)

    data = {
        "androidId": ANDROID_ID,
        "lang": "en-US",
        "google_play_services_version": GMS_VERSION,
        "sdk_version": SDK_VERSION,
        "device_country": "us",
        "it_caveat_types": "2",
        "app": "com.google.android.apps.photos",
        "oauth2_foreground": "1",
        "Email": EMAIL,
        "pkgVersionCode": PHOTOS_VERSION,
        "has_permission": "1",
        "token_request_options": "CAA4AVABYAA=",
        "client_sig": PHOTOS_CLIENT_SIG,
        "Token": MASTER_TOKEN,
        "consumerVersionCode": PHOTOS_VERSION,
        "check_email": "1",
        "service": "oauth2:openid https://www.googleapis.com/auth/mobileapps.native https://www.googleapis.com/auth/photos.native",
        "callerPkg": "com.google.android.apps.photos",
        "check_tb_upgrade_eligible": "1",
        "callerSig": PHOTOS_CLIENT_SIG,
    }

    response = httpx.post(AUTH_URL, data=data, headers=HEADERS)

    # Handle gzip
    if response.headers.get("content-encoding") == "gzip":
        body = gzip.decompress(response.content).decode()
    else:
        body = response.text

    result = parse_response(body)
    print(f"Status: {response.status_code}")
    print(f"Keys: {list(result.keys())}")

    if "it" in result:
        print(f"SUCCESS! Token: {result['it'][:50]}...")
        return True
    else:
        print(f"Error: {result.get('Error', 'Unknown')}")
        return False


def test_oauthlogin_scope():
    """Test OAuthLogin scope with same parameters."""
    print("\n" + "=" * 60)
    print("Test 2: OAuthLogin scope (for web cookies)")
    print("=" * 60)

    data = {
        "androidId": ANDROID_ID,
        "lang": "en-US",
        "google_play_services_version": GMS_VERSION,
        "sdk_version": SDK_VERSION,
        "device_country": "us",
        "it_caveat_types": "2",
        "app": "com.google.android.apps.photos",
        "oauth2_foreground": "1",
        "Email": EMAIL,
        "pkgVersionCode": PHOTOS_VERSION,
        "has_permission": "1",
        "token_request_options": "CAA4AVABYAA=",
        "client_sig": PHOTOS_CLIENT_SIG,
        "Token": MASTER_TOKEN,
        "consumerVersionCode": PHOTOS_VERSION,
        "check_email": "1",
        # Changed service to OAuthLogin
        "service": "oauth2:https://www.google.com/accounts/OAuthLogin",
        "callerPkg": "com.google.android.apps.photos",
        "check_tb_upgrade_eligible": "1",
        "callerSig": PHOTOS_CLIENT_SIG,
    }

    response = httpx.post(AUTH_URL, data=data, headers=HEADERS)

    if response.headers.get("content-encoding") == "gzip":
        body = gzip.decompress(response.content).decode()
    else:
        body = response.text

    result = parse_response(body)
    print(f"Status: {response.status_code}")
    print(f"Response: {body[:500]}")

    if "Auth" in result:
        print(f"\nSUCCESS! Auth token: {result['Auth'][:50]}...")
        return result["Auth"]
    elif "it" in result:
        print(f"\nSUCCESS! Token (it): {result['it'][:50]}...")
        return result["it"]
    else:
        print(f"\nError: {result.get('Error', 'Unknown')}")
        return None


def test_oauthlogin_minimal():
    """Test OAuthLogin with minimal parameters."""
    print("\n" + "=" * 60)
    print("Test 3: OAuthLogin minimal parameters")
    print("=" * 60)

    data = {
        "Email": EMAIL,
        "Token": MASTER_TOKEN,
        "service": "oauth2:https://www.google.com/accounts/OAuthLogin",
        "app": "com.google.android.apps.photos",
        "client_sig": PHOTOS_CLIENT_SIG,
        "androidId": ANDROID_ID,
        "device_country": "us",
        "lang": "en-US",
        "sdk_version": SDK_VERSION,
        "google_play_services_version": GMS_VERSION,
    }

    response = httpx.post(AUTH_URL, data=data, headers=HEADERS)

    if response.headers.get("content-encoding") == "gzip":
        body = gzip.decompress(response.content).decode()
    else:
        body = response.text

    result = parse_response(body)
    print(f"Status: {response.status_code}")
    print(f"Response: {body[:500]}")

    if "Auth" in result:
        return result["Auth"]
    return None


def get_web_cookies(access_token: str):
    """Get web cookies via uberauth + MergeSession."""
    print("\n" + "=" * 60)
    print("Getting web cookies")
    print("=" * 60)

    client = httpx.Client(follow_redirects=True)

    # Get uberauth
    print("\n[1] Getting uberauth...")
    response = client.get(
        "https://accounts.google.com/accounts/OAuthLogin",
        params={"source": "hangups", "issueuberauth": "1"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    uberauth = response.text.strip()
    print(f"Uberauth: {uberauth[:60]}...")

    # Merge session
    print("\n[2] Merging session...")
    response = client.get(
        "https://accounts.google.com/MergeSession",
        params={"uberauth": uberauth, "continue": "https://www.google.com/"},
    )

    cookies = {}
    for cookie in client.cookies.jar:
        cookies[cookie.name] = cookie.value

    print("\n[3] Cookies obtained:")
    for name in ["SID", "HSID", "SSID", "SAPISID", "APISID"]:
        if name in cookies:
            print(f"  {name}: {cookies[name][:30]}...")
        else:
            print(f"  {name}: NOT FOUND")

    client.close()
    return cookies


def main():
    # First verify the photos scope works
    if not test_photos_scope():
        print("\nPhotos scope failed - master token may be invalid")
        return

    # Try OAuthLogin scope
    access_token = test_oauthlogin_scope()

    if not access_token:
        access_token = test_oauthlogin_minimal()

    if access_token:
        cookies = get_web_cookies(access_token)

        print("\n" + "=" * 60)
        print("FINAL RESULTS")
        print("=" * 60)
        if "SAPISID" in cookies:
            print("\nSuccess! You now have web cookies for batchexecute.")
            print(f"SAPISID: {cookies['SAPISID']}")
        else:
            print("\nPartial success - some cookies obtained but SAPISID missing")
    else:
        print("\nFailed to get OAuthLogin token")
        print("The master token may not have permission for OAuthLogin scope")


if __name__ == "__main__":
    main()
