import os
import json
import gspread
import telebot
import requests
import urllib3
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

# Tắt cảnh báo bảo mật SSL khi quét web Sở
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH BIẾN MÔI TRƯỜNG ---
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
        # Mở Sheet1 của file DANH_SACH_VAN_BAN
        return client.open(SHEET_NAME).worksheet("Sheet1")
    except Exception as e:
        print(f"❌ Lỗi kết nối Google Sheets: {e}")
        return None

def quet_web_so_khcn():
    url = "https://sokhcn.dienbien.gov.vn/van-ban"
    print(f"🌍 Đang quét website Sở KH&CN: {url}")
    ds_van_ban = []
    try:
        # Gửi yêu cầu lấy dữ liệu từ web
        response = requests.get(url, timeout=30, verify=False)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Tìm bảng danh sách văn bản (Dựa trên cấu trúc web NukeViet của Sở)
        table = soup.find('table') 
        if not table: return []

        rows = table.find_all('tr')[1:] # Bỏ hàng tiêu đề
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 4:
                so_hieu = cols[1].text.strip()    # Cột 2: Số hiệu
                ngay_ban = cols[2].text.strip()   # Cột 3: Ngày ban hành
                trich_yeu = cols[3].text.strip()  # Cột 4: Trích yếu nội dung
                ds_van_ban.append([so_hieu, ngay_ban, trich_yeu])
        
        return ds_van_ban
    except Exception as e:
        print(f"❌ Lỗi khi đọc dữ liệu web: {e}")
        return []

if __name__ == "__main__":
    print("🚀 Robot bắt đầu chu kỳ làm việc...")
    sheet = ket_noi_sheets()
    
    if sheet:
        danh_sach_moi = quet_web_so_khcn()
        if not danh_sach_moi:
            print("📭 Không tìm thấy văn bản nào mới trên web.")
        else:
            # Lấy danh sách số hiệu đã có trong file Excel để đối chiếu
            so_hieu_da_co = sheet.col_values(1)
            
            # Duyệt qua các văn bản mới quét được
            for vb in reversed(danh_sach_moi): # Đảo ngược để lưu cái cũ trước, cái mới sau
                if vb[0] not in so_hieu_da_co:
                    # Ghi vào file Excel
                    sheet.append_row(vb)
                    
                    # Gửi tin nhắn về Telegram cho anh Hoàn
                    thong_bao = (
                        f"🔔 **CÓ VĂN BẢN MỚI TỪ SỞ KH&CN!**\n\n"
                        f"📌 **Số hiệu:** `{vb[0]}`\n"
                        f"📅 **Ngày ban hành:** {vb[1]}\n"
                        f"📝 **Nội dung:** {vb[2]}\n\n"
                        f"🔗 Xem tại: https://sokhcn.dienbien.gov.vn/van-ban"
                    )
                    bot.send_message(CHAT_ID, thong_bao, parse_mode="Markdown")
                    print(f"✅ Đã báo cáo văn bản: {vb[0]}")

    print("🏁 Robot đã hoàn thành công việc và đang ở trạng thái chờ.")
