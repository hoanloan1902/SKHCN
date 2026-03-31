import os
import json
import gspread
import telebot
import requests
import urllib3
import time
import re
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CAU HINH ---
USER_NAME = os.environ.get("SKHCN_USER")
PASS_WORD = os.environ.get("SKHCN_PASS")
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_JSON = os.environ.get("GSPREAD_SERVICE_ACCOUNT")
CHAT_ID = os.environ.get("CHAT_ID")
SHEET_NAME = "DANH_SACH_VAN_BAN"

# --- KIEM TRA BIEN MOI TRUONG ---
print(f"🔍 Kiem tra bien:")
print(f"   USER    = {'✅ OK' if USER_NAME else '❌ MISSING'}")
print(f"   PASS    = {'✅ OK' if PASS_WORD else '❌ MISSING'}")
print(f"   TOKEN   = {'✅ OK' if TOKEN else '❌ MISSING'}")
print(f"   CHAT_ID = {'✅ OK' if CHAT_ID else '❌ MISSING'}")
print(f"   GOOGLE  = {'✅ OK' if GOOGLE_JSON else '❌ MISSING'}")

if not TOKEN:
    print("❌ TELEGRAM_TOKEN chua duoc set! Dung lai.")
    exit(1)

bot = telebot.TeleBot(TOKEN)


def ket_noi_sheets():
    if not GOOGLE_JSON:
        print("❌ GSPREAD_SERVICE_ACCOUNT chua duoc set!")
        return None
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(GOOGLE_JSON)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        print("✅ Ket noi Google Sheets thanh cong!")
        return client.open(SHEET_NAME).sheet1
    except Exception as e:
        print(f"❌ Loi Sheets: {e}")
        return None


def quet_lotus_v18():
    base_url   = "https://hscvkhcn.dienbien.gov.vn"
    url_login  = f"{base_url}/qlvb/index.nsf/default?openform"   # trang lay cookie
    url_post   = f"{base_url}/names.nsf?Login"                    # action cua form
    url_target = f"{base_url}/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm"

    session = requests.Session()
    headers_get = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    headers_post = {
        **headers_get,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': base_url,
        'Referer': url_login,
    }

    try:
        # Buoc 1: Lay cookie tu trang login
        print("🌐 [B1] Lay cookie tu trang login...")
        r0 = session.get(url_login, headers=headers_get, verify=False, timeout=15)
        print(f"   Status: {r0.status_code} | URL: {r0.url}")

        # Buoc 2: POST dang nhap theo chuan Domino
        print("🔑 [B2] Dang nhap Domino...")
        login_data = {
            'Username': USER_NAME,
            'Password': PASS_WORD,
            'RedirectTo': '/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm',
        }
        res_login = session.post(url_post, data=login_data, headers=headers_post, verify=False, allow_redirects=True)
        print(f"   Status: {res_login.status_code} | URL cuoi: {res_login.url}")

        # Kiem tra da dang nhap chua
        if 'Username' in res_login.text or 'Password' in res_login.text or 'Dang nhap' in res_login.text:
            print("❌ Van con o trang dang nhap — sai user/pass hoac bi chan!")
            print("   HTML (500 ky tu):", res_login.text[:500])
            return []
        else:
            print("✅ Dang nhap thanh cong!")

        # Buoc 3: Truy cap trang van ban cho xu ly
        print("📄 [B3] Truy cap trang van ban...")
        response = session.get(url_target, headers=headers_get, verify=False, timeout=25)
        print(f"   Status: {response.status_code} | URL: {response.url}")

        # Parse du lieu
        soup = BeautifulSoup(response.text, 'html.parser')
        ds_van_ban = []
        rows = soup.find_all('tr')
        print(f"📊 Tim thay {len(rows)} dong <tr>")

        for row in rows:
            cols = row.find_all(['td', 'font'])
            txt = [re.sub(r'\s+', ' ', c.get_text().strip()) for c in cols if c.get_text().strip()]

            found_date = None
            for t in txt:
                if re.search(r'\d{2}/\d{2}/\d{4}', t):
                    found_date = t
                    break

            if found_date:
                so_hieu = ""
                noi_dung = ""
                for t in txt:
                    if "/" in t and t != found_date:
                        so_hieu = t
                    if len(t) > 25:
                        noi_dung = t
                if so_hieu:
                    ds_van_ban.append([so_hieu, found_date, noi_dung])

        print(f"✅ Parse xong: {len(ds_van_ban)} van ban")
        return ds_van_ban

    except requests.exceptions.ConnectionError as e:
        print(f"❌ Loi ket noi: {e}")
    except requests.exceptions.Timeout:
        print("❌ Timeout: server khong phan hoi")
    except Exception as e:
        print(f"❌ Loi khac: {e}")
    return []


if __name__ == "__main__":
    print(f"\n🚀 Robot HSCV bat dau: {time.strftime('%H:%M:%S')}")
    print("=" * 50)

    sheet = ket_noi_sheets()

    if sheet:
        danh_sach = quet_lotus_v18()

        if not danh_sach:
            print("📭 Khong lay duoc du lieu.")
        else:
            print(f"🎉 Tim thay {len(danh_sach)} van ban!")
            try:
                da_co = sheet.col_values(1)
            except Exception as e:
                print(f"❌ Loi doc Sheets: {e}")
                da_co = []

            moi = 0
            for vb in reversed(danh_sach):
                if vb[0] not in da_co:
                    try:
                        sheet.insert_row(vb, 2)
                        msg = (
                            f"🔔 *VĂN BẢN MỚI!*\n"
                            f"📌 Số: `{vb[0]}`\n"
                            f"📅 Ngày: {vb[1]}\n"
                            f"📝 ND: {vb[2]}"
                        )
                        bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
                        print(f"✅ Da bao: {vb[0]}")
                        moi += 1
                        time.sleep(1)
                    except Exception as e:
                        print(f"❌ Loi luu/gui: {e}")

            if moi == 0:
                print("☕ Khong co van ban moi.")
            else:
                print(f"📬 Da gui {moi} thong bao.")
    else:
        print("❌ Khong ket noi duoc Sheets.")

    print("=" * 50)
    print(f"🏁 Ket thuc: {time.strftime('%H:%M:%S')}")
