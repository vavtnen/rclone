#!/usr/bin/env python3
"""
EmbeddedSetup login using Playwright (headless browser).
This handles all the JavaScript challenges automatically.

Install: pip install playwright && playwright install chromium
"""

import asyncio
import re
from playwright.async_api import async_playwright

# Configuration
EMAIL = "your_email@gmail.com"
PASSWORD = "your_password"


async def embedded_login(email: str, password: str, headless: bool = True) -> dict:
    """
    Perform EmbeddedSetup login and return oauth_token and cookies.

    Args:
        email: Google account email
        password: Google account password
        headless: Run browser in headless mode (no GUI)

    Returns:
        dict with oauth_token, user_id, and all cookies
    """
    async with async_playwright() as p:
        # Launch browser with Android-like settings
        browser = await p.chromium.launch(headless=headless)

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36",
            viewport={"width": 412, "height": 915},
            device_scale_factor=2.625,
            is_mobile=True,
            has_touch=True,
        )

        page = await context.new_page()

        result = {
            "oauth_token": None,
            "user_id": None,
            "cookies": {},
        }

        try:
            print("=" * 60)
            print("EmbeddedSetup Login (Playwright)")
            print("=" * 60)

            # Step 1: Navigate to EmbeddedSetup
            print("\n[Step 1] Loading EmbeddedSetup page...")
            await page.goto(
                "https://accounts.google.com/EmbeddedSetup?"
                "source=android&xoauth_display_name=Android+Device&"
                "lang=en&cc=US&langCountry=en_US"
            )
            await page.wait_for_load_state("networkidle")
            print("  Page loaded")

            # Step 2: Enter email
            print(f"\n[Step 2] Entering email: {email}")
            email_input = await page.wait_for_selector('input[type="email"]', timeout=10000)
            await email_input.fill(email)
            await page.click('button:has-text("Next"), #identifierNext')
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)  # Wait for transition
            print("  Email submitted")

            # Step 3: Enter password
            print("\n[Step 3] Entering password...")
            password_input = await page.wait_for_selector('input[type="password"]', timeout=10000)
            await password_input.fill(password)
            await page.click('button:has-text("Next"), #passwordNext')
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            print("  Password submitted")

            # Step 4: Handle consent/agreement page
            print("\n[Step 4] Looking for consent page...")
            try:
                # Wait for either "I agree" button or oauth_token cookie
                agree_button = await page.wait_for_selector(
                    'button:has-text("I agree"), button:has-text("Accept"), '
                    'button:has-text("Agree"), span:has-text("I agree")',
                    timeout=5000
                )
                if agree_button:
                    print("  Found 'I agree' button, clicking...")
                    await agree_button.click()
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)
            except:
                print("  No consent button found (may already be accepted)")

            # Step 5: Extract cookies
            print("\n[Step 5] Extracting cookies...")
            cookies = await context.cookies()

            for cookie in cookies:
                result["cookies"][cookie["name"]] = cookie["value"]
                if cookie["name"] == "oauth_token":
                    result["oauth_token"] = cookie["value"]
                    print(f"  oauth_token: {cookie['value'][:50]}...")
                elif cookie["name"] == "user_id":
                    result["user_id"] = cookie["value"]
                    print(f"  user_id: {cookie['value']}")

            # If no oauth_token in cookies, check if we need more steps
            if not result["oauth_token"]:
                print("\n  Waiting for oauth_token...")
                # Wait a bit more and try again
                await asyncio.sleep(3)
                cookies = await context.cookies()
                for cookie in cookies:
                    result["cookies"][cookie["name"]] = cookie["value"]
                    if cookie["name"] == "oauth_token":
                        result["oauth_token"] = cookie["value"]
                        print(f"  oauth_token: {cookie['value'][:50]}...")

            # Print all cookies
            print("\n  All cookies:")
            for name, value in result["cookies"].items():
                display_value = value[:30] + "..." if len(value) > 30 else value
                print(f"    {name}: {display_value}")

        except Exception as e:
            print(f"\nError: {e}")
            # Take screenshot for debugging
            await page.screenshot(path="error_screenshot.png")
            print("Screenshot saved to error_screenshot.png")
            raise

        finally:
            await browser.close()

        return result


async def main():
    result = await embedded_login(EMAIL, PASSWORD, headless=True)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    if result["oauth_token"]:
        print(f"\noauth_token:\n{result['oauth_token']}")
        print(f"\nuser_id: {result['user_id']}")
        print("\nNow you can use this oauth_token with gpsoauth to get master token:")
        print("""
import gpsoauth
master = gpsoauth.exchange_token(
    email='{email}',
    token='{token}',
    android_id='your_android_id'
)
print(master)
""".format(email=EMAIL, token=result['oauth_token'][:30] + "..."))
    else:
        print("\nFailed to obtain oauth_token")
        print("Check error_screenshot.png for debugging")


if __name__ == "__main__":
    asyncio.run(main())
