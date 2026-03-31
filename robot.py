import os
import json
import gspread
import telebot
import requests
import urllib3
import time
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- THÔNG TIN TỪ GITHUB ---
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
        return client.open(SHEET_NAME).get_worksheet(0)
    except Exception as e:
        print(f"❌ Lỗi Sheets: {e}")
        return None

def quet_hscv_lotus_notes():
    # Đường dẫn đăng nhập và đường dẫn trực tiếp đến bảng "Văn bản chờ xử lý"
    url_login = "https://hscvkhcn.dienbien.gov.vn/login"
    # Link này em lấy từ ảnh image_1f3362.jpg của anh
    url_target = "https://hscvkhcn.dienbien.gov.vn/qlvb/vbden.nsf/Default?OpenForm"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        print(f"🔑 Đăng nhập hệ thống Lotus Notes cho anh Hoàn...")
        payload = {'username': USER_NAME, 'password': PASS_WORD, 'submit': 'Đăng nhập'}
        session.post(url_login, data=payload, headers=headers, verify=False, timeout=30)
        
        # Nhảy thẳng vào trang danh sách văn bản
        response = session.get(url_target, headers=headers, verify=False, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            ds_van_ban = []
            
            # Lotus Notes thường để dữ liệu trong các thẻ <tr> có class hoặc cấu trúc lặp lại
            rows = soup.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                # Dựa vào ảnh image_1f3362.jpg, dữ liệu bắt đầu từ các cột có số hiệu
                if len(cols) >= 5:
                    txt = [c.get_text(strip=True) for c in cols]
                    # Lọc lấy dòng có ngày tháng (vd: 30/03/2026) và số hiệu
                    if "/" in txt[2] and len(txt[2]) == 10: 
                        ngay = txt[2]
                        so_hieu = txt[3]
                        trich_yeu = txt[5] if len(txt) > 5 else "Không có trích yếu"
                        ds_van_ban.append([so_hieu, ngay, trich_yeu])
            
            return ds_van_ban
    except Exception as e:
        print(f"❌ Lỗi quét Lotus: {e}")
    return []

if __name__ == "__main__":
    print(f"🚀 Robot bắt đầu quét chuyên sâu: {time.strftime('%H:%M:%S')}")
    sheet = ket_noi_sheets()
    
    if sheet:
        danh_sach = quet_hscv_lotus_notes()
        if not danh_sach:
            print("📭 Không tìm thấy bảng. Có thể hệ thống dùng iFrame chặn Robot.")
        else:
            try:
                da_co = sheet.col_values(1)
            except:
                da_co = []

            moi = 0
            for vb in reversed(danh_sach):
                if vb[0] not in da_co:
                    sheet.insert_row(vb, 2)
                    msg = f"🔔 **VĂN BẢN MỚI (HSCV)!**\n📌 Số: `{vb[0]}`\n📅 Ngày: {vb[1]}\n📝 ND: {vb[2]}"
                    bot.send_message(CHAT_ID, msg)
                    print(f"✅ Đã báo cáo: {vb[0]}")
                    moi += 1
            
            if moi == 0:
                print("☕ Không có văn bản mới nào.")
    print("🏁 Robot nghỉ ngơi.")
