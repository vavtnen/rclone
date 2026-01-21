import requests
import hashlib
import time
import re
import json

COOKIES = """__Secure-BUCKET=CPUG; HSID=AG1S3Xmv-h_Vjx9Oh; SSID=AK5qHCg0yqr9jkyQg; APISID=J7ZQzlbVGXh5EEOE/ADz98yL7gajCNrm4_; SAPISID=c1oWdehmelMskfwd/Aty5j9Q2nbGGpmiN9; __Secure-1PAPISID=c1oWdehmelMskfwd/Aty5j9Q2nbGGpmiN9; __Secure-3PAPISID=c1oWdehmelMskfwd/Aty5j9Q2nbGGpmiN9; OSID=g.a0005giSGx8qjd3ROUlmf0TykLbZi3hidiqmg8TpbCBrw7FvAVjEjMvF-DxX_VmDKKRTld2fZwACgYKASwSAQ0SFQHGX2MiYsqsKWAW8CCYGMB67nL5RBoVAUF8yKqGDIhGblwZTs43Rf_MRUyz0076; __Secure-OSID=g.a0005giSGx8qjd3ROUlmf0TykLbZi3hidiqmg8TpbCBrw7FvAVjElV9jdtQiV0Ex0NRhUfcrXAACgYKARISAQ0SFQHGX2MizrtSzy1QQ3wISYW02oJ2qxoVAUF8yKrKsqIdS58Gy6EZAFBsCfH80076; SID=g.a0005giSG3V-5nmvrFhktt_0GF6hx9amPHxxKuNyaHhsJhTyS4GlDHK8FsxwSxntnF8_o7a87AACgYKAc8SAQ0SFQHGX2MiQqSs95ToZpmrcFBSwfGs3xoVAUF8yKo2nyrK50HxBins5bS-T1HM0076; __Secure-1PSID=g.a0005giSG3V-5nmvrFhktt_0GF6hx9amPHxxKuNyaHhsJhTyS4GlOPe2D12Vb1CC-6zo5aTqtQACgYKAZESAQ0SFQHGX2Mi79y365bNjAqGHgqcSPU4hxoVAUF8yKqJfN9U74kRUEIHqT5lSTQK0076; __Secure-3PSID=g.a0005giSG3V-5nmvrFhktt_0GF6hx9amPHxxKuNyaHhsJhTyS4GlFtqPjLvoDIAyqsZd7vHqTwACgYKAasSAQ0SFQHGX2Mi5F2fW8d1suT5EKYMm3dr9RoVAUF8yKoGlPsroPt47mi-_G5L8fwK0076; SEARCH_SAMESITE=CgQI9Z8B; OTZ=8444134_76_76_104100_72_446760; NID=528=gyH61HVuWJLXG8gSNZw8LARLby6rGx33dvuTc3ONee4r9rZMQcGvkelifZMH4jzJk0XtAhhsobLMzimlMdSY4YCwRzEWmmh-3T4hRosnk37ifZo_xCW2hh8p7ig08xj7XvEoR2lGFNDrYdzzz9n7kXIkivvZQzI9A2c9RTcQrI0NtiDQC1RBL3YyDfSYVxWQoWynTSDMaNDeFNl5nC7J7tU6q2T4vHbbT0oC8-WBGsc2owz1tMJbFbC3-i-f60BTBHbjKGj7dLkCIKMYVCCdToDMJn-UqgppIV6aN5HbVJViKZMB4wTByN0TYyGPDnu8bdNs_MAoZ1vNeWoxneFU5Uyzq_embKb_Y3SDrw1zXwgFzqnqolquPSASKiDjFoIbLav1udZyAAw8LUwGRGM9xiBMyU3MzL3auOEVgDwjXSad7Xkugo9v97AuPJkpI3xvdgouQRsTgUCtscziy-RvgiJpdlxi_Uko2PFy4y8ynfyP-sz-RADHERa6Ob48uq66IzO3dKl6H-8mJ-1KJr897RLXntzsFSTsam3OVDYX2wHN-hHvuzdbB3dMzSWC0WRA8WoEyZDiuEY-jtljKjBS2-d720csx7aQ2mHATJ8X71JX-pdb18lSuXaDFOuQxbISmJ9Ro3Su4PsH-uCUr7Me8Eu3xBF4XEWHyN9BO_nrCmk-pxORs2yQNBbtUzQh7KFtHyaiIDEuctFnZm-mRT6cmubXv9q-jnuseTlkovoS2m7GfuX11bEbt57GXZtwuAHPrE0V8Rn0eIx_An2NRMDqpHEaLSKtoOekZnfjPqHcc5sAqnjyqddZYTAKCxwm58iiZ_I9asKUoFg3Ddb14290JNreavdh2Pa1uauc_zX_1x2GGUl3bEBjlQ1Yb9Pw_XhaMg_QFFDsHVK3tKFtah3jZUS1jh1bjsNclSWl_3crqa6MlmmVPzxj0zwHtFZbWwypGdOKsilByvIMPtXhdHDRVMgQOQaxPWQiqAkRp1b628s2Nch1d7frRmn7-EOEBX6A_5W_PHWDDbDkCKdn8qfmjYWH22uwucqxXnjtkD5OZiHjHxHAcYXT3C7wqibfTaCQ5n5OgjVfI1n6ItJoBao7Nc7Kjp8gJzhq7K7UmJlK0dQS5ieJZV7B4Wqnh-12NxizkCzh-MLTw1A3JeZkh5nh0xVg5lX4kA3060w_b6HDUXhVgw1GeN7dwNuN5GaSPaO90kLEOXanfV4mHIDw4jtwwEojbksqmiAVbMqNPBFmIQmP-WPRI9b2kcv1KEwdKYp-AJE3dniLmIBej2ebe_9DLzwqUqQq_FE_ktMoguJgbk4ZVfa2SlbafU0exv0ugnR4pp87UJmwfeqBG8WxBK2td48OQeETamX3HVUrOOCpopiZ4VfkqQAtTgmQ3P4O2lt0lK3n-cNDPtdueK9Ewj5ogMF6XdzPrMVypI3FkhuXInItS2A9jVWRJFTIP3nSznLrlusM-bT0WV7YoWti8U50hs_68Nfieg1gAxb19k8NDMUzNMstNBVrMAOx1T9et_ssN8_xg93TEsulQ0ki6QmgYzihNYXdMUmvFrVTEoGYOeclmo5uURrQCW1359NLvc27grLEFR8BSHyQ0eqck7N8PGRUOH7JOFLxoUMkkCVIqyEYunNk8wpqnIgrwKhkoSbzlocz6nyoZS0EBqjnlxr3yOZs12Zg6pzGmWfrjmxB2ntZHapoxKZIGHWemLoOejyiSxRdNHBufARbBxlqr0xeXh41I8Mo-Sf6CK4iJ_L4jzq2I9NcOKDlmn0COkewTZNozWrEr-GvTfGMOvtut_tMIECxG63_-8wxVJhVy5ltwV_rBcvy6it8RGBsGmMU6ngtO1fA4OOFAbQLildbjdd4aGtrwwMSbm0HGbTi-M5WSICO3Qbw6bboj5qozS76ke8bFpahPfWY3dBFcCy4Hiq2HQAxsSkuOKK-g82fpWrVp4TfrvGSP1kHslxkUwzqRtP5Kg75UmYgYIlKs3BNwInQf1we0sRR4tXhzGC3JwQUgRXWNrA3li_uTiX8LiyEWNYFoLLlF16XrAiTxMkoC6bzdCC60EB1PZGoo6dOztt91fw7vSjKvRwHbrgleczWm-QbZLKmWFKkIqcvtHRj-MmWETLhrZlFVk93saLmkOTs1sf6HZWv68awdFHlwUBXJYLTp4o_R6HQiRYn9NWKsJMSpEj_hqtNZQe_7DR1xLAyzZTWrIDWgdH3Y7agMpYism2V1TU9Vy20oy9ex2JKb6pjJ50j1ngYX79NUWbN8XqSwyIa3bFiIJdRthzznttmIxlU0Mth8_BzSjBtEvIbFzM8SV3zmw7XjducfWEKBTW6TwSU9aSTG0-ujAbhnRv0RE-uQHX2Am-d9tsUdr9VYTj1QMAkVml69dQmvs2fpa-9ojJVqIbkL65E6yCMoV7Qh-_npIIoasZfHTLEBBGDyLxKLeQNfx3eIigrWIsAdB-gVOfd49DGqvn7N9tknpCK2uH78mslczBTYR2AR5REqYYyBIxhKv1gybDDTFmdqHPTRmOUZs7HHmcE3FMo4CNpf4ySldr3p0KBW0m8_mU3_0fv7nNfEJfcfDTVEjkjxkTee6loUrlOeHlIv9YoAoWMVADBZXW-CCJ4HOeh4kwCr0jOjdxI_sbz7UXRdsfI2MqOhrr97m_JqRT0TyDSM24lmaIoiKr0x8E2_N7YJqxV_CBMcwCrw_H4YtVp6dK8tJA0gtTugo9LXRNIasi0_Ok0rmlJeffqp9bdQdTvFQVkIKyCadROnbN2UwdRJakBj5iFNzsri2IO8SQD-8z5OO6W0TRLZuNLZ8jrXUNn4je7OgdEDUK94fHe7kO-QOrdXpM-ddIK_tx6BCf3et1Zb4BiFDdEwmWYVVuyzTNaZV0M800exPmz_rLP0kqZBEYEmTqIl1j5U3fq93zOJu0R4OXoTByiFrygBCoR4raavVhorFqYIwXxZWvBfzswa2W-1IrdphwVtBva89oSSnegxzD8liu52LuMbUr4zuJoY75eQPdHr-Iucr958fbqTo_oumIi4ymufmjBitGwKN80L3hy; __Secure-STRP=AD6Dogvh0dGGWWrnOPQere1YXMFIu0PgtmjP57U_Cfn_sFR2meTBeIbOyov0EZKioXKNhMzm-mvhTBwyoBK5hHgQVM0ojQak-UMv; AEC=AaJma5vU2uVdmWZ8cPIhQM8TZaD9iqB309pR4t-lJXZdNvMiJQmIay7-5Q; COMPASS=photos-ui=CgAQh-vAywYaVwAJa4lXEHHhIzu3CVQbCdOlPkR3XBDY2GiiTz2FbIBaoI-ou1v8lvt_gIg-GUFU-cpYaR19zLL47g55BdWQM4LJ3pCkWfzb8OJP2DiqcqK148UW8qvXaTAB; __Secure-1PSIDTS=sidts-CjIB7I_69PoHkyIYVrpPwcKx81v33rXW4Yg7pXIq-LXrK4trbT3ua69ptfeOp6GHV_SnDRAA; __Secure-3PSIDTS=sidts-CjIB7I_69PoHkyIYVrpPwcKx81v33rXW4Yg7pXIq-LXrK4trbT3ua69ptfeOp6GHV_SnDRAA; SIDCC=AKEyXzWJcMXQxiU7KlcdXSniEiCTojvsn_sNq5layUXV_KJxMFQgypLC8DsrmeijI9nXHelDNb8a; __Secure-1PSIDCC=AKEyXzWMSJvjcjCnoIWzHt8IldoD7g7DV4--L-qw34pGGFjDkH7k9nKWnirW4xRZwOdQ27zthz8K; __Secure-3PSIDCC=AKEyXzX4DSo3R_KUpLcgAmccblkf-rA7G2JzkRQt7U5SXqOEinnaoJhCIEMBzX05YSsVERzbx3I"""

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

if __name__ == "__main__":
    fetch_unsupported_videos(COOKIES)
