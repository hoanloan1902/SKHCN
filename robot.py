import os
import json
import gspread
import telebot
import requests
import urllib3
import time
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- KHỚP LỆNH VỚI GITHUB SECRETS CỦA ANH HOÀN ---
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
        print(f"❌ Lỗi kết nối Sheets: {e}")
        return None

def quet_hscv_dang_nhap_that():
    url_login = "https://hscvkhcn.dienbien.gov.vn/login"
    url_main = "https://hscvkhcn.dienbien.gov.vn"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        print(f"🔑 Đang đăng nhập tài khoản: {USER_NAME}...")
        # Gửi dữ liệu đăng nhập
        payload = {
            'username': USER_NAME,
            'password': PASS_WORD,
            'submit': 'Đăng nhập' # Thường các web VN có thêm nút này
        }
        
        # Thử đăng nhập
        login_res = session.post(url_login, data=payload, headers=headers, verify=False, timeout=30)
        
        # Sau khi đăng nhập, lấy nội dung trang chủ
        response = session.get(url_main, headers=headers, verify=False, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            ds_van_ban = []
            
            # Tìm bảng văn bản
            rows = soup.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4:
                    txt = [c.get_text(strip=True) for c in cols]
                    # Lọc lấy dòng có số hiệu văn bản thực sự
                    if "/" in txt[1] and len(txt[1]) > 3:
                        ds_van_ban.append(txt[1:4])
            return ds_van_ban
    except Exception as e:
        print(f"❌ Lỗi truy cập HSCV: {e}")
    return []

if __name__ == "__main__":
    print(f"🚀 Robot HSCV bắt đầu làm việc: {time.strftime('%H:%M:%S')}")
    sheet = ket_noi_sheets()
    
    if sheet:
        danh_sach_moi = quet_hscv_dang_nhap_that()
        if not danh_sach_moi:
            print("📭 Đã vào được web nhưng bảng văn bản đang trống hoặc sai thông tin đăng nhập.")
        else:
            try:
                da_co = sheet.col_values(1)
            except:
                da_co = []

            them_moi = 0
            for vb in reversed(danh_sach_moi):
                if vb[0] not in da_co:
                    sheet.insert_row(vb, 2)
                    msg = f"🔔 **VĂN BẢN HSCV MỚI!**\n\n📌 **Số:** `{vb[0]}`\n📝 **Nội dung:** {vb[2]}"
                    bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                    print(f"✅ Đã báo cáo: {vb[0]}")
                    them_moi += 1
            
            if them_moi == 0:
                print("☕ Không có văn bản nào mới.")
    print("🏁 Kết thúc.")
