#!/usr/bin/env python3
"""
Complete EmbeddedSetup flow using Playwright.
Gets oauth_token and exchanges it for master token and web cookies.

Install:
    pip install playwright gpsoauth httpx
    playwright install chromium
"""

import asyncio
import httpx
from playwright.async_api import async_playwright

# Configuration - UPDATE THESE
EMAIL = "your_email@gmail.com"
PASSWORD = "your_password"  # Use app password if 2FA enabled
ANDROID_ID = "de0a0dc373653ca4"  # Your device's android_id

# App credentials
APP = "com.google.android.apps.chromecast.app"
CLIENT_SIG = "24bb24c05e47e0aefa68a58a766179d9b613a600"
GPS_VERSION = "240913000"


async def get_oauth_token(email: str, password: str, headless: bool = True) -> str:
    """Get oauth_token via EmbeddedSetup browser flow."""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; Pixel 4) AppleWebKit/537.36",
            viewport={"width": 412, "height": 915},
            is_mobile=True,
        )
        page = await context.new_page()

        print("[1/4] Loading EmbeddedSetup...")
        await page.goto(
            "https://accounts.google.com/EmbeddedSetup?"
            "source=android&xoauth_display_name=Android+Device"
        )
        await page.wait_for_load_state("networkidle")

        print(f"[2/4] Entering email: {email}")
        await page.fill('input[type="email"]', email)
        await page.click('#identifierNext, button:has-text("Next")')
        await asyncio.sleep(3)

        print("[3/4] Entering password...")
        await page.wait_for_selector('input[type="password"]', timeout=10000)
        await page.fill('input[type="password"]', password)
        await page.click('#passwordNext, button:has-text("Next")')
        await asyncio.sleep(3)

        print("[4/4] Handling consent...")
        try:
            agree = await page.wait_for_selector(
                'button:has-text("I agree"), button:has-text("Agree")',
                timeout=5000
            )
            if agree:
                await agree.click()
                await asyncio.sleep(2)
        except:
            pass

        # Extract oauth_token
        oauth_token = None
        for cookie in await context.cookies():
            if cookie["name"] == "oauth_token":
                oauth_token = cookie["value"]
                print(f"\noauth_token: {oauth_token[:50]}...")
                break

        await browser.close()
        return oauth_token


def exchange_for_master_token(oauth_token: str, email: str, android_id: str) -> str:
    """Exchange oauth_token for master token."""

    print("\n[Exchange] oauth_token -> master_token")

    url = "https://android.googleapis.com/auth"
    data = {
        "Token": oauth_token,
        "Email": email,
        "service": "ac2dm",
        "app": APP,
        "client_sig": CLIENT_SIG,
        "androidId": android_id,
        "device_country": "us",
        "lang": "en",
        "sdk_version": "28",
        "google_play_services_version": GPS_VERSION,
    }

    response = httpx.post(url, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "GoogleAuth/1.4 (Nexus 5 LMY48M); gzip",
    })

    result = {}
    for line in response.text.strip().split('\n'):
        if '=' in line:
            k, v = line.split('=', 1)
            result[k] = v

    if "Token" in result:
        print(f"Master token: {result['Token'][:40]}...")
        return result["Token"]
    else:
        print(f"Error: {result.get('Error', response.text)}")
        return None


def get_oauthlogin_token(master_token: str, email: str, android_id: str) -> str:
    """Get OAuthLogin scoped token from master token."""

    print("\n[OAuthLogin] master_token -> access_token")

    url = "https://android.googleapis.com/auth"
    data = {
        "Token": master_token,
        "Email": email,
        "service": "oauth2:https://www.google.com/accounts/OAuthLogin",
        "app": APP,
        "client_sig": CLIENT_SIG,
        "androidId": android_id,
        "device_country": "us",
        "lang": "en",
        "sdk_version": "28",
        "google_play_services_version": GPS_VERSION,
    }

    response = httpx.post(url, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "GoogleAuth/1.4 (Nexus 5 LMY48M); gzip",
    })

    result = {}
    for line in response.text.strip().split('\n'):
        if '=' in line:
            k, v = line.split('=', 1)
            result[k] = v

    if "Auth" in result:
        print(f"Access token: {result['Auth'][:40]}...")
        return result["Auth"]
    else:
        print(f"Error: {result.get('Error', response.text)}")
        return None


def get_web_cookies(access_token: str) -> dict:
    """Get web cookies via uberauth + MergeSession."""

    print("\n[Uberauth] Getting uberauth token...")

    client = httpx.Client(follow_redirects=True)

    # Get uberauth
    response = client.get(
        "https://accounts.google.com/accounts/OAuthLogin",
        params={"source": "hangups", "issueuberauth": "1"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    uberauth = response.text.strip()
    print(f"Uberauth: {uberauth[:40]}...")

    # Merge session
    print("\n[MergeSession] Getting web cookies...")
    response = client.get(
        "https://accounts.google.com/MergeSession",
        params={"uberauth": uberauth, "continue": "https://www.google.com/"},
    )

    cookies = {}
    for cookie in client.cookies.jar:
        cookies[cookie.name] = cookie.value

    client.close()
    return cookies


async def main():
    print("=" * 60)
    print("EmbeddedSetup -> Master Token -> Web Cookies")
    print("=" * 60)

    # Step 1: Get oauth_token via browser
    oauth_token = await get_oauth_token(EMAIL, PASSWORD, headless=True)
    if not oauth_token:
        print("Failed to get oauth_token")
        return

    # Step 2: Exchange for master token
    master_token = exchange_for_master_token(oauth_token, EMAIL, ANDROID_ID)
    if not master_token:
        print("Failed to get master_token")
        return

    # Step 3: Get OAuthLogin token
    access_token = get_oauthlogin_token(master_token, EMAIL, ANDROID_ID)
    if not access_token:
        print("Failed to get access_token")
        return

    # Step 4: Get web cookies
    cookies = get_web_cookies(access_token)

    # Results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\nMaster Token:\n{master_token}")
    print(f"\nWeb Cookies:")
    for name in ["SID", "HSID", "SSID", "SAPISID", "APISID"]:
        if name in cookies:
            print(f"  {name}: {cookies[name][:30]}...")
        else:
            print(f"  {name}: NOT FOUND")


if __name__ == "__main__":
    asyncio.run(main())
