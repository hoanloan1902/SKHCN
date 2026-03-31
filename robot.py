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

USER_NAME = os.environ.get("SKHCN_USER")
PASS_WORD = os.environ.get("SKHCN_PASS")
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_JSON = os.environ.get("GSPREAD_SERVICE_ACCOUNT")
CHAT_ID = os.environ.get("CHAT_ID")
SHEET_NAME = "DANH_SACH_VAN_BAN"

print(f"USER={'OK' if USER_NAME else 'MISSING'} PASS={'OK' if PASS_WORD else 'MISSING'} TOKEN={'OK' if TOKEN else 'MISSING'} CHAT={'OK' if CHAT_ID else 'MISSING'} GOOGLE={'OK' if GOOGLE_JSON else 'MISSING'}")

if not TOKEN:
    print("Thieu TELEGRAM_TOKEN!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

def ket_noi_sheets():
    if not GOOGLE_JSON:
        print("Thieu GSPREAD!")
        return None
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_JSON), scope)
        client = gspread.authorize(creds)
        print("Sheets OK!")
        return client.open(SHEET_NAME).sheet1
    except Exception as e:
        print(f"Loi Sheets: {e}")
        return None

def quet_lotus_v18():
    base_url   = "https://hscvkhcn.dienbien.gov.vn"
    url_login  = f"{base_url}/qlvb/index.nsf/default?openform"
    url_post   = f"{base_url}/names.nsf?Login"
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

    def parse_trang(html):
        soup = BeautifulSoup(html, 'html.parser')
        ket_qua = []
        for row in soup.find_all('tr'):
            tds = row.find_all('td')
            if len(tds) < 5:
                continue
            cols = [re.sub(r'\s+', ' ', td.get_text()).strip() for td in tds]
            so_den = ngay_den = so_hieu = co_quan = trich_yeu = ""
            for i, c in enumerate(cols):
                if re.match(r'^\d{2}/\d{2}/\d{4}$', c):
                    ngay_den  = c
                    so_den    = cols[i-1] if i >= 1 else ""
                    so_hieu   = cols[i+1] if i+1 < len(cols) else ""
                    co_quan   = cols[i+2] if i+2 < len(cols) else ""
                    trich_yeu = cols[i+3] if i+3 < len(cols) else ""
                    break
            if ngay_den and so_hieu and re.search(r'\d+', so_den):
                if so_hieu.strip() and '/' in so_hieu:
                    ket_qua.append([so_hieu.strip(), ngay_den, trich_yeu[:200], co_quan, so_den])
        return ket_qua

    try:
        # Buoc 1: Lay cookie
        print("[B1] Lay cookie...")
        session.get(url_login, headers=headers_get, verify=False, timeout=15)

        # Buoc 2: Dang nhap
        print("[B2] Dang nhap...")
        res_login = session.post(url_post, data={
            'Username': USER_NAME,
            'Password': PASS_WORD,
            'RedirectTo': '/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm',
        }, headers=headers_post, verify=False, allow_redirects=True)
        print(f"   Status: {res_login.status_code} | URL: {res_login.url}")

        if 'Username' in res_login.text and 'Password' in res_login.text:
            print("Dang nhap that bai!")
            return []
        print("Dang nhap OK!")

        # Buoc 3: Lay tung trang
        ds_van_ban = []
        trang = 1

        while True:
            if trang == 1:
                url_trang = url_target
            else:
                url_trang = f"{base_url}/qlvb/vbden.nsf/Private_ChoXL_KoHan?openForm&p={trang}"

            print(f"[B3] Lay trang {trang}...")
            response = session.get(url_trang, headers=headers_get, verify=False, timeout=25)
            vb_trang = parse_trang(response.text)
            print(f"   Trang {trang}: {len(vb_trang)} van ban")

            if not vb_trang:
                print(f"   Trang {trang} rong, dung lai.")
                break

            ds_van_ban.extend(vb_trang)

            if trang >= 10:
                break

            trang += 1

        # Loai bo trung lap theo so hieu
        seen = set()
        ds_unique = []
        for vb in ds_van_ban:
            if vb[0] not in seen:
                seen.add(vb[0])
                ds_unique.append(vb)

        print(f"Tong: {len(ds_unique)} van ban (da loai trung)")
        return ds_unique

    except requests.exceptions.ConnectionError as e:
        print(f"Loi ket noi: {e}")
    except requests.exceptions.Timeout:
        print("Timeout")
    except Exception as e:
        print(f"Loi: {e}")
    return []

if __name__ == "__main__":
    print(f"=== Robot bat dau: {time.strftime('%H:%M:%S')} ===")
    sheet = ket_noi_sheets()

    if sheet:
        danh_sach = quet_lotus_v18()
        if not danh_sach:
            print("Khong lay duoc du lieu.")
        else:
            print(f"Tim thay {len(danh_sach)} van ban!")
            try:
                da_co = sheet.col_values(1)
            except Exception as e:
                print(f"Loi doc Sheets: {e}")
                da_co = []

            moi = 0
            for vb in reversed(danh_sach):
                if vb[0] not in da_co:
                    try:
                        sheet.insert_row(vb, 2)
                        msg = (
                            f"*VAN BAN MOI!*\n"
                            f"So hieu: `{vb[0]}`\n"
                            f"Ngay: {vb[1]}\n"
                            f"Co quan: {vb[3]}\n"
                            f"Trich yeu: {vb[2]}"
                        )
                        bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
                        print(f"Da bao: {vb[0]}")
                        moi += 1
                        time.sleep(1)
                    except Exception as e:
                        print(f"Loi luu/gui: {e}")

            if moi == 0:
                print("Khong co van ban moi.")
            else:
                print(f"Da gui {moi} thong bao.")
    else:
        print("Khong ket noi Sheets.")

    print(f"=== Ket thuc: {time.strftime('%H:%M:%S')} ===")
