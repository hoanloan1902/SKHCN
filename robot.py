import os
import json
import gspread
import telebot
import requests
import urllib3
import time
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

# Tắt cảnh báo bảo mật cho các hệ thống nội bộ
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- LẤY BIẾN TỪ GITHUB SECRETS ---
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
        print(f"❌ Lỗi Sheets: {e}")
        return None

def quet_hscv_lotus_notes():
    # Link đăng nhập và Link danh sách văn bản chờ xử lý của anh
    url_login = "https://hscvkhcn.dienbien.gov.vn/login"
    url_target = "https://hscvkhcn.dienbien.gov.vn/qlvb/vbden.nsf/Private_ChoXL_KoHan?openForm"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        print(f"🔑 Đang đăng nhập hệ thống cho anh Hoàn (User: {USER_NAME})...")
        # Sửa đúng 'Username' và 'Password' viết hoa chữ cái đầu theo mã nguồn anh gửi
        payload = {
            'Username': USER_NAME, 
            'Password': PASS_WORD, 
            'submit': 'Đăng nhập'
        }
        session.post(url_login, data=payload, headers=headers, verify=False, timeout=30)
        
        # Truy cập trực tiếp link bảng văn bản
        print("🎯 Đang lấy dữ liệu từ danh sách Chờ xử lý...")
        response = session.get(url_target, headers=headers, verify=False, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            ds_van_ban = []
            
            # Quét các hàng trong bảng Lotus Notes
            rows = soup.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 6:
                    txt = [c.get_text(strip=True) for c in cols]
                    # Cột 3 là ngày, Cột 4 là số hiệu, Cột 6 là trích yếu
                    ngay = txt[2]
                    if "/" in ngay and len(ngay) == 10:
                        so_hieu = txt[3]
                        trich_yeu = txt[5]
                        ds_van_ban.append([so_hieu, ngay, trich_yeu])
            return ds_van_ban
    except Exception as e:
        print(f"❌ Lỗi hệ thống HSCV: {e}")
    return []

if __name__ == "__main__":
    print("🚀 Robot bắt đầu chu kỳ làm việc thực tế...")
    sheet = ket_noi_sheets()
    
    if sheet:
        danh_sach_that = quet_hscv_lotus_notes()
        if not danh_sach_that:
            print("📭 Đăng nhập được nhưng không tìm thấy văn bản nào mới.")
        else:
            # Lấy 20 số hiệu cũ để đối chiếu
            try:
                da_co = sheet.col_values(1)[:20]
            except:
                da_co = []

            moi = 0
            for vb in reversed(danh_sach_that):
                if vb[0] not in da_co:
                    # Ghi vào Sheets
                    sheet.insert_row(vb, 2)
                    # Gửi tin nhắn Telegram
                    msg = f"🔔 **VĂN BẢN MỚI (HSCV)!**\n📌 Số: `{vb[0]}`\n📅 Ngày: {vb[1]}\n📝 ND: {vb[2]}"
                    bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                    print(f"✅ Đã báo cáo thành công: {vb[0]}")
                    moi += 1
            
            if moi == 0:
                print("☕ Không có văn bản nào mới trên hệ thống.")
    print("🏁 Robot đã hoàn thành nhiệm vụ.")
