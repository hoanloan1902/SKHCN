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

bot = telebot.TeleBot(TOKEN)

def ket_noi_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(GOOGLE_JSON)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).sheet1
    except Exception as e:
        print(f"❌ Loi Sheets: {e}")
        return None

def quet_lotus_v18():
    url_login = "https://hscvkhcn.dienbien.gov.vn/login"
    # Thu dung link rut gon nay xem he thong co tu mo frame cho minh ko
    url_target = "https://hscvkhcn.dienbien.gov.vn/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm"
    
    session = requests.Session()
    # Gia lap trinh duyet that de tranh bi chan
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://hscvkhcn.dienbien.gov.vn',
        'Referer': url_login
    }
    
    try:
        print(f"🔑 Dang mo cong dang nhap cho anh Hoan...")
        # Buoc 1: Lay cookie khoi tao
        session.get(url_login, verify=False, timeout=15)
        
        # Buoc 2: Gui thong tin dang nhap
        login_data = {
            'Username': USER_NAME,
            'Password': PASS_WORD,
            'RedirectTo': '/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm',
            '__Click': '0'
        }
        
        res_login = session.post(url_login, data=login_data, headers=headers, verify=False, allow_redirects=True)
        print("✅ Da gui lenh dang nhap. Dang kiem tra phan hoi...")
        
        # Buoc 3: Truy cap trang du lieu (thu lay ca nhung trang phu)
        response = session.get(url_target, headers=headers, verify=False, timeout=25)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # In thu mot doan ma nguon de minh kiem tra (chi hien trong log GitHub)
        # print(response.text[:500]) 

        ds_van_ban = []
        # Tim tat ca cac hang (tr)
        rows = soup.find_all('tr')
        
        for row in rows:
            cols = row.find_all(['td', 'font'])
            txt = [re.sub(r'\s+', ' ', c.get_text().strip()) for c in cols if c.get_text().strip()]
            
            # Kiem tra dong co ngay thang dd/mm/yyyy
            found_date = None
            for t in txt:
                if re.search(r'\d{2}/\d{2}/\d{4}', t):
                    found_date = t
                    break
            
            if found_date:
                # Theo anh chup: Ngay thuong la cot index 2, So hieu index 3, ND index 5
                # Nhung Robot se quet thong minh hon
                so_hieu = ""
                noi_dung = ""
                for t in txt:
                    if "/" in t and t != found_date: so_hieu = t
                    if len(t) > 25: noi_dung = t
                
                if so_hieu:
                    ds_van_ban.append([so_hieu, found_date, noi_dung])
        
        return ds_van_ban

    except Exception as e:
        print(f"❌ Loi: {e}")
    return []

if __name__ == "__main__":
    print(f"🚀 Robot HSCV V18 bat dau: {time.strftime('%H:%M:%S')}")
    sheet = ket_noi_sheets()
    
    if sheet:
        danh_sach = quet_lotus_v18()
        if not danh_sach:
            print("📭 Van chua thong duoc du lieu. Co the he thong chan IP tu nuoc ngoai.")
        else:
            print(f"🎉 Thanh cong! Tim thay {len(danh_sach)} van ban.")
            try:
                da_co = sheet.col_values(1)
            except:
                da_co = []

            moi = 0
            for vb in reversed(danh_sach):
                if vb[0] not in da_co:
                    sheet.insert_row(vb, 2)
                    msg = f"🔔 **VĂN BẢN MỚI!**\n📌 Số: `{vb[0]}`\n📅 Ngày: {vb[1]}\n📝 ND: {vb[2]}"
                    bot.send_message(CHAT_ID, msg)
                    print(f"✅ Da bao: {vb[0]}")
                    moi += 1
            if moi == 0: print("☕ Khong co gi moi.")
    print("🏁 Ket thuc.")
