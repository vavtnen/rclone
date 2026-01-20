#!/usr/bin/env python3
"""
Complete EmbeddedSetup Android login flow.
Simulates Android device login to obtain oauth_token.
"""

import re
import json
import time
import random
import httpx
from urllib.parse import urlencode, quote

# Configuration
EMAIL = "your_email@gmail.com"
PASSWORD = "your_password"

# Android device simulation
USER_AGENT = "Mozilla/5.0 (Linux; Android 10; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36"

BASE_URL = "https://accounts.google.com"
BATCHEXECUTE_URL = f"{BASE_URL}/v3/signin/_/AccountsSignInUi/data/batchexecute"


class EmbeddedSetupLogin:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.client = httpx.Client(follow_redirects=False, timeout=30.0)

        # Session state
        self.gaps_cookie = None
        self.f_sid = None
        self.at_token = None
        self.dsh = None
        self.tl_token = None
        self.bl = None
        self.req_id = 0

    def _get_headers(self, include_goog_ext: bool = True) -> dict:
        """Get common headers for batchexecute requests."""
        headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Same-Domain": "1",
        }
        if include_goog_ext:
            headers["X-Goog-Ext-278367001-Jspb"] = '["EmbeddedSetupAndroid"]'
            if self.dsh:
                headers["X-Goog-Ext-391502476-Jspb"] = f'["{self.dsh}"]'
        return headers

    def _next_req_id(self) -> int:
        """Generate next request ID."""
        if self.req_id == 0:
            self.req_id = random.randint(10000, 99999)
        self.req_id += 100000
        return self.req_id

    def _parse_batchexecute_response(self, text: str) -> list:
        """Parse batchexecute response format."""
        # Remove )]}' prefix
        text = text.lstrip(")]}'").strip()

        results = []
        lines = text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.isdigit():
                # Next line is JSON data of that length
                length = int(line)
                i += 1
                if i < len(lines):
                    json_str = lines[i].strip()
                    try:
                        data = json.loads(json_str)
                        results.append(data)
                    except json.JSONDecodeError:
                        pass
            i += 1
        return results

    def _extract_from_page(self, html: str):
        """Extract session tokens from initial page HTML."""
        # Extract f.sid
        match = re.search(r'"FdrFJe":"(-?\d+)"', html)
        if match:
            self.f_sid = match.group(1)

        # Extract at token
        match = re.search(r'"SNlM0e":"([^"]+)"', html)
        if match:
            self.at_token = match.group(1)

        # Extract dsh
        match = re.search(r'"S[^"]*:\d+"', html)
        if match:
            self.dsh = match.group(0).strip('"')

        # Alternative dsh extraction
        match = re.search(r'data-initial-setup-data="([^"]+)"', html)
        if match:
            import html as html_module
            data = html_module.unescape(match.group(1))
            dsh_match = re.search(r'"(S-\d+:\d+)"', data)
            if dsh_match:
                self.dsh = dsh_match.group(1)

        # Extract bl (build label)
        match = re.search(r'"cfb2h":"([^"]+)"', html)
        if match:
            self.bl = match.group(1)

        print(f"  f.sid: {self.f_sid}")
        print(f"  at: {self.at_token[:30] if self.at_token else None}...")
        print(f"  dsh: {self.dsh}")
        print(f"  bl: {self.bl}")

    def step0_load_embedded_setup(self) -> bool:
        """Load EmbeddedSetup page to get initial tokens."""
        print("\n[Step 0] Loading EmbeddedSetup page...")

        url = f"{BASE_URL}/EmbeddedSetup"
        params = {
            "source": "android",
            "xoauth_display_name": "Android Device",
        }

        response = self.client.get(url, params=params)
        print(f"  Status: {response.status_code}")

        # Get GAPS cookie
        for cookie in self.client.cookies.jar:
            if "GAPS" in cookie.name:
                self.gaps_cookie = f"{cookie.name}={cookie.value}"
                print(f"  GAPS: {cookie.value[:30]}...")

        # Extract tokens from HTML
        self._extract_from_page(response.text)

        # Generate dsh if not found
        if not self.dsh:
            timestamp = int(time.time() * 1000)
            self.dsh = f"S{random.randint(100000000, 999999999)}:{timestamp}"
            print(f"  Generated dsh: {self.dsh}")

        return bool(self.f_sid and self.at_token)

    def step1_initial_check(self) -> bool:
        """UEkKwb - Initial page check."""
        print("\n[Step 1] Initial check (UEkKwb)...")

        params = {
            "rpcids": "UEkKwb",
            "source-path": "/v3/signin/identifier",
            "f.sid": self.f_sid,
            "bl": self.bl or "boq_identityfrontendauthuiserver_20260111.08_p0",
            "hl": "en-US",
            "_reqid": self._next_req_id(),
            "rt": "c",
        }

        # Request data
        req_data = json.dumps([[self.dsh, "0"]])
        f_req = json.dumps([[["UEkKwb", req_data, None, "generic"]]])

        data = {
            "f.req": f_req,
            "at": self.at_token,
        }

        response = self.client.post(
            BATCHEXECUTE_URL,
            params=params,
            data=data,
            headers=self._get_headers(),
        )

        print(f"  Status: {response.status_code}")
        results = self._parse_batchexecute_response(response.text)
        print(f"  Response: {results}")

        return response.status_code == 200

    def step2_submit_email(self) -> bool:
        """MI613e - Submit email address."""
        print(f"\n[Step 2] Submitting email (MI613e): {self.email}")

        params = {
            "rpcids": "MI613e",
            "source-path": "/v3/signin/identifier",
            "f.sid": self.f_sid,
            "bl": self.bl or "boq_identityfrontendauthuiserver_20260111.08_p0",
            "hl": "en-US",
            "_reqid": self._next_req_id(),
            "rt": "c",
        }

        # Build the complex request structure
        continue_url = "https://accounts.google.com/o/android/auth?lang=en&cc=US&langCountry=en_US&xoauth_display_name=Android+Device&tmpl=new_account&source=android&return_user_id=true"

        flow_params = [
            ["flowName", "EmbeddedSetupAndroid"],
            ["continue", continue_url],
            ["dsh", self.dsh],
        ]

        inner_data = [
            None, self.email, 1, None, None, 1, 1, None, None, None, None, None,
            None, None, None, None, None, None, None, None, "", "US", None, None,
            None, None, None, None, 7, None, None, None, None, None, None, None, None,
            [self.dsh, [None, None, None, None, None, None, None, 1, 0, 1, "", None, None, 2, 1, 2],
             [["identity-signin-identifier", ""], None, [None, "AccountLookupWizRpc", 5, 0]],
             [[None, None, None, None, continue_url],
              [None, None, self.dsh, None, continue_url, None, flow_params],
              None, None, None, [None, None, None, None, None, [None, flow_params, continue_url], None, self.dsh]
             ], ""],
        ]

        req_data = json.dumps(inner_data)
        f_req = json.dumps([[["MI613e", req_data, None, "generic"]]])

        data = {
            "f.req": f_req,
            "at": self.at_token,
        }

        response = self.client.post(
            BATCHEXECUTE_URL,
            params=params,
            data=data,
            headers=self._get_headers(),
        )

        print(f"  Status: {response.status_code}")

        # Extract TL token from response
        results = self._parse_batchexecute_response(response.text)
        for result in results:
            result_str = json.dumps(result)
            tl_match = re.search(r'"TL","([^"]+)"', result_str)
            if tl_match:
                self.tl_token = tl_match.group(1)
                print(f"  TL token: {self.tl_token[:40]}...")
                break

        return bool(self.tl_token)

    def step3_submit_password(self) -> bool:
        """B4hajb - Submit password."""
        print(f"\n[Step 3] Submitting password (B4hajb)...")

        params = {
            "rpcids": "B4hajb",
            "source-path": "/v3/signin/challenge/pwd",
            "f.sid": self.f_sid,
            "bl": self.bl or "boq_identityfrontendauthuiserver_20260111.08_p0",
            "hl": "en-US",
            "TL": self.tl_token,
            "_reqid": self._next_req_id(),
            "rt": "c",
        }

        continue_url = "https://accounts.google.com/o/android/auth?lang=en&cc=US&langCountry=en_US&xoauth_display_name=Android+Device&tmpl=new_account&source=android&return_user_id=true"

        flow_params = [
            ["TL", self.tl_token],
            ["cid", "2"],
            ["continue", continue_url],
            ["dsh", self.dsh],
            ["flowName", "EmbeddedSetupAndroid"],
        ]

        inner_data = [
            1, 2, None,
            [1, None, None, None, [self.password, None, 1]],
            [None, None, None, None, continue_url],
            None,
            [flow_params, "accounts.google.com", "/v3/signin/challenge/pwd"],
            None,
            [["identity-signin-password", ""], None, [None, "ProcessChallengeWizRpc", 5, 0]],
        ]

        req_data = json.dumps(inner_data)
        f_req = json.dumps([[["B4hajb", req_data, None, "generic"]]])

        data = {
            "f.req": f_req,
            "at": self.at_token,
        }

        response = self.client.post(
            BATCHEXECUTE_URL,
            params=params,
            data=data,
            headers=self._get_headers(),
        )

        print(f"  Status: {response.status_code}")

        # Check for redirect to consent page
        results = self._parse_batchexecute_response(response.text)
        for result in results:
            result_str = json.dumps(result)
            if "embeddedsigninconsent" in result_str:
                print("  -> Redirecting to consent page")
                return True
            if "INCORRECT_ANSWER_ENTERED" in result_str or "error" in result_str.lower():
                print("  -> Password incorrect or error")
                return False

        return True

    def step4_consent(self) -> str:
        """ihzRS - Submit consent and get oauth_token."""
        print("\n[Step 4] Submitting consent (ihzRS)...")

        params = {
            "rpcids": "ihzRS",
            "source-path": "/v3/signin/speedbump/embeddedsigninconsent",
            "f.sid": self.f_sid,
            "bl": self.bl or "boq_identityfrontendauthuiserver_20260111.08_p0",
            "hl": "en-US",
            "TL": self.tl_token,
            "_reqid": self._next_req_id(),
            "rt": "c",
        }

        continue_url = "https://accounts.google.com/o/android/auth?lang=en&cc=US&langCountry=en_US&xoauth_display_name=Android+Device&tmpl=new_account&source=android&return_user_id=true"

        inner_data = [
            [
                [["TL", self.tl_token],
                 ["continue", continue_url],
                 ["dsh", self.dsh],
                 ["flowName", "EmbeddedSetupAndroid"]],
                "accounts.google.com",
                "/v3/signin/speedbump/embeddedsigninconsent"
            ]
        ]

        req_data = json.dumps(inner_data)
        f_req = json.dumps([[["ihzRS", req_data, None, "generic"]]])

        data = {
            "f.req": f_req,
            "at": self.at_token,
        }

        response = self.client.post(
            BATCHEXECUTE_URL,
            params=params,
            data=data,
            headers=self._get_headers(),
        )

        print(f"  Status: {response.status_code}")

        # Check for oauth_token in cookies
        oauth_token = None
        user_id = None

        for cookie in self.client.cookies.jar:
            if cookie.name == "oauth_token":
                oauth_token = cookie.value
                print(f"  oauth_token: {oauth_token[:50]}...")
            elif cookie.name == "user_id":
                user_id = cookie.value
                print(f"  user_id: {user_id}")

        # Also check Set-Cookie headers
        if "set-cookie" in response.headers:
            cookies_header = response.headers.get_list("set-cookie")
            for cookie_str in cookies_header:
                if "oauth_token=" in cookie_str:
                    match = re.search(r'oauth_token=([^;]+)', cookie_str)
                    if match:
                        oauth_token = match.group(1)
                        print(f"  oauth_token (header): {oauth_token[:50]}...")

        return oauth_token

    def login(self) -> str:
        """Execute full login flow and return oauth_token."""
        print("=" * 60)
        print("EmbeddedSetup Android Login Flow")
        print("=" * 60)

        if not self.step0_load_embedded_setup():
            print("Failed to load EmbeddedSetup page")
            return None

        if not self.step1_initial_check():
            print("Failed initial check")
            return None

        if not self.step2_submit_email():
            print("Failed to submit email")
            return None

        if not self.step3_submit_password():
            print("Failed to submit password")
            return None

        oauth_token = self.step4_consent()

        if oauth_token:
            print("\n" + "=" * 60)
            print("SUCCESS!")
            print("=" * 60)
            print(f"oauth_token: {oauth_token}")
            return oauth_token
        else:
            print("\nFailed to obtain oauth_token")
            return None

    def close(self):
        self.client.close()


def main():
    login = EmbeddedSetupLogin(EMAIL, PASSWORD)
    try:
        oauth_token = login.login()
        if oauth_token:
            print(f"\n\nFinal oauth_token:\n{oauth_token}")
    finally:
        login.close()


if __name__ == "__main__":
    main()
