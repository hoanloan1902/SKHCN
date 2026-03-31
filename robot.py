import os
import json
import gspread
import telebot
import requests
import urllib3
import time
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

# Tắt cảnh báo bảo mật SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_JSON = os.environ.get("GSPREAD_SERVICE_ACCOUNT")
CHAT_ID = os.environ.get("CHAT_ID")
SHEET_NAME = "DAN_SACH_VAN_BAN" # Anh kiểm tra tên file Sheets phải khớp nhé

bot = telebot.TeleBot(TOKEN)

def ket_noi_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(GOOGLE_JSON)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).sheet1
    except Exception as e:
        print(f"❌ Lỗi kết nối Sheets: {e}")
        return None

def quet_web_hscv():
    # Cập nhật địa chỉ mới của anh Hoàn
    url = "https://hscvkhcn.dienbien.gov.vn" 
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    }
    print(f"🌍 Đang kết nối tới hệ thống HSCV: {url}")
    
    for i in range(3):
        try:
            # Hệ thống HSCV thường yêu cầu thời gian chờ lâu hơn một chút
            response = requests.get(url, headers=headers, timeout=45, verify=False)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                ds_van_ban = []
                
                # Quét các dòng trong bảng văn bản
                rows = soup.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        so_hieu = cols[1].get_text(strip=True)
                        ngay_ban = cols[2].get_text(strip=True)
                        noi_dung = cols[3].get_text(strip=True)
                        
                        if so_hieu and "Số hiệu" not in so_hieu:
                            ds_van_ban.append([so_hieu, ngay_ban, noi_dung])
                return ds_van_ban
            else:
                print(f"⚠️ Hệ thống phản hồi lỗi: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Lần thử {i+1} thất bại... Đang thử lại. ({e})")
            time.sleep(10)
    return []

if __name__ == "__main__":
    print(f"🚀 Robot bắt đầu quét hệ thống lúc: {time.strftime('%H:%M:%S')}")
    sheet = ket_noi_sheets()
    
    if sheet:
        danh_sach_moi = quet_web_hscv()
        if not danh_sach_moi:
            print("📭 Chưa lấy được dữ liệu. Anh Hoàn kiểm tra xem trang web có yêu cầu đăng nhập không nhé.")
        else:
            # Lấy 30 số hiệu cũ để đối chiếu
            try:
                so_hieu_da_co = sheet.col_values(1)[:30]
            except:
                so_hieu_da_co = []

            moi_them = 0
            for vb in reversed(danh_sach_moi):
                if vb[0] not in so_hieu_da_co:
                    # Ghi văn bản mới vào dòng thứ 2 (ngay dưới tiêu đề)
                    sheet.insert_row(vb, 2)
                    
                    # Gửi tin nhắn Telegram cho anh
                    msg = (f"🔔 **VĂN BẢN MỚI TỪ HSCV!**\n\n"
                           f"📌 **Số:** `{vb[0]}`\n"
                           f"📅 **Ngày:** {vb[1]}\n"
                           f"📝 **ND:** {vb[2]}")
                    
                    try:
                        bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                        print(f"✅ Đã báo cáo văn bản: {vb[0]}")
                        moi_them += 1
                        time.sleep(1)
                    except Exception as e:
                        print(f"❌ Lỗi gửi tin nhắn: {e}")

            if moi_them == 0:
                print("☕ Không có văn bản mới nào trên hệ thống HSCV.")
    
    print("🏁 Phiên làm việc kết thúc.")
