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

# --- CẤU HÌNH ---
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

def quet_web_so_khcn():
    url = "https://sokhcn.dienbien.gov.vn/van-ban"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    print(f"🌍 Đang kết nối tới: {url}")
    
    # Thử lại tối đa 3 lần nếu lỗi mạng
    for i in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                ds_van_ban = []
                
                # Tìm tất cả các dòng trong bảng
                rows = soup.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        so_hieu = cols[1].get_text(strip=True)
                        ngay_ban = cols[2].get_text(strip=True)
                        noi_dung = cols[3].get_text(strip=True)
                        
                        # Chỉ lấy nếu dòng đó có số hiệu (loại bỏ tiêu đề)
                        if so_hieu and so_hieu != "Số hiệu":
                            ds_van_ban.append([so_hieu, ngay_ban, noi_dung])
                return ds_van_ban
        except Exception as e:
            print(f"⚠️ Lần thử {i+1} thất bại, đang thử lại... ({e})")
            time.sleep(5)
    return []

if __name__ == "__main__":
    print("🚀 Robot bắt đầu chu kỳ làm việc...")
    sheet = ket_noi_sheets()
    
    if sheet:
        danh_sach_moi = quet_web_so_khcn()
        if not danh_sach_moi:
            print("📭 Không lấy được dữ liệu. Có thể web Sở đang bảo trì.")
        else:
            # Lấy 20 số hiệu gần nhất trong Sheets để so sánh
            so_hieu_da_co = sheet.col_values(1)[:20]
            
            moi_them = 0
            for vb in reversed(danh_sach_moi):
                if vb[0] not in so_hieu_da_co:
                    sheet.insert_row(vb, 2) # Chèn vào dòng thứ 2 (dưới tiêu đề)
                    
                    msg = (f"🔔 **CÓ VĂN BẢN MỚI!**\n\n"
                           f"📌 **Số:** `{vb[0]}`\n"
                           f"📅 **Ngày:** {vb[1]}\n"
                           f"📝 **ND:** {vb[2]}")
                    
                    try:
                        bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                        print(f"✅ Đã báo cáo: {vb[0]}")
                        moi_them += 1
                        time.sleep(1) # Tránh bị Telegram chặn do gửi nhanh
                    except Exception as e:
                        print(f"❌ Lỗi gửi Telegram: {e}")

            if moi_them == 0:
                print("☕ Không có văn bản nào mới hơn.")
    
    print("🏁 Robot đã hoàn thành công việc.")
