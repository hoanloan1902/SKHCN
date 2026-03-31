import os
import json
import gspread
import telebot
import requests
import urllib3
import time
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

# Tắt cảnh báo bảo mật SSL cho hệ thống nội bộ
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
        # Phân tích cú pháp JSON từ biến môi trường
        creds_dict = json.loads(GOOGLE_JSON)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        # Mở trang tính đầu tiên
        return client.open(SHEET_NAME).get_worksheet(0)
    except Exception as e:
        print(f"❌ Lỗi kết nối Google Sheets: {e}")
        return None

def quet_hscv_dang_nhap():
    url_login = "https://hscvkhcn.dienbien.gov.vn/login"
    url_main = "https://hscvkhcn.dienbien.gov.vn"
    
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    }
    
    try:
        # Kiểm tra nếu chưa lấy được tài khoản từ GitHub
        if not USER_NAME or not PASS_WORD:
            print("⚠️ LỖI: Chưa lấy được SKHCN_USER hoặc SKHCN_PASS từ GitHub Secrets!")
            return []

        print(f"🔑 Đang thử đăng nhập tài khoản: {USER_NAME}...")
        
        # Dữ liệu đóng gói để gửi lệnh Login
        payload = {
            'username': USER_NAME,
            'password': PASS_WORD,
            'submit': 'Đăng nhập'
        }
        
        # Thực hiện đăng nhập
        session.post(url_login, data=payload, headers=headers, verify=False, timeout=30)
        
        # Truy cập trang chủ sau khi login để lấy bảng văn bản
        response = session.get(url_main, headers=headers, verify=False, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            ds_van_ban = []
            
            # Tìm tất cả các bảng trên trang
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        txt = [c.get_text(strip=True) for c in cols]
                        # Kiểm tra xem dòng này có chứa số hiệu văn bản (thường có dấu /)
                        if len(txt) > 1 and "/" in txt[1]:
                            ds_van_ban.append(txt[1:4]) # Lấy Số hiệu, Ngày, Trích yếu
            return ds_van_ban
    except Exception as e:
        print(f"❌ Lỗi khi quét hệ thống HSCV: {e}")
    return []

if __name__ == "__main__":
    print(f"🚀 Robot bắt đầu làm việc lúc: {time.strftime('%H:%M:%S')}")
    sheet = ket_noi_sheets()
    
    if sheet:
        danh_sach_moi = quet_hscv_dang_nhap()
        if not danh_sach_moi:
            print("📭 Đăng nhập được nhưng không tìm thấy bảng văn bản. Anh Hoàn kiểm tra lại giao diện trang chủ nhé!")
        else:
            # Lấy danh sách số hiệu cũ trong cột A để đối chiếu
            try:
                da_co = sheet.col_values(1)
            except:
                da_co = []

            moi_them = 0
            # Duyệt danh sách từ cũ đến mới
            for vb in reversed(danh_sach_moi):
                if vb[0] not in da_co:
                    # Chèn vào Excel
                    sheet.insert_row(vb, 2)
                    # Gửi tin nhắn Telegram
                    msg = f"🔔 **VĂN BẢN HSCV MỚI!**\n\n📌 **Số hiệu:** `{vb[0]}`\n📝 **Trích yếu:** {vb[2]}"
                    bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                    print(f"✅ Đã báo cáo văn bản: {vb[0]}")
                    moi_them += 1
                    time.sleep(1) # Tránh bị Telegram chặn

            if moi_them == 0:
                print("☕ Không có văn bản nào mới trên hệ thống.")
    
    print("🏁 Robot đã hoàn thành phiên làm việc.")
