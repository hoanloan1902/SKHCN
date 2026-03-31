import os
import json
import gspread
import telebot
import requests
import urllib3
import time
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

# Tắt cảnh báo SSL cho hệ thống nội bộ
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- LẤY BIẾN TỪ GITHUB SECRETS (Khớp hoàn toàn với file .yml của anh) ---
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
        # Mở Sheet1 (mặc định)
        return client.open(SHEET_NAME).sheet1
    except Exception as e:
        print(f"❌ Lỗi Sheets: {e}")
        return None

def quet_du_lieu_that():
    url_login = "https://hscvkhcn.dienbien.gov.vn/login"
    # Link "hang ổ" chứa văn bản chờ xử lý của anh
    url_target = "https://hscvkhcn.dienbien.gov.vn/qlvb/vbden.nsf/Private_ChoXL_KoHan?openForm"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        print(f"🔑 Đăng nhập tài khoản: {USER_NAME}...")
        # Sử dụng 'Username' và 'Password' viết hoa đúng mã nguồn anh chụp
        payload = {
            'Username': USER_NAME, 
            'Password': PASS_WORD, 
            'submit': 'Đăng nhập'
        }
        session.post(url_login, data=payload, headers=headers, verify=False, timeout=30)
        
        print("🎯 Đang quét văn bản chờ xử lý thực tế...")
        response = session.get(url_target, headers=headers, verify=False, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            ds_van_ban = []
            
            rows = soup.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                # Dựa vào ảnh image_1f3362.jpg: Ngày cột 3, Số hiệu cột 4, Trích yếu cột 6
                if len(cols) >= 6:
                    txt = [c.get_text(strip=True) for c in cols]
                    ngay = txt[2]
                    if "/" in ngay and len(ngay) == 10:
                        so_hieu = txt[3]
                        trich_yeu = txt[5]
                        ds_van_ban.append([so_hieu, ngay, trich_yeu])
            return ds_van_ban
    except Exception as e:
        print(f"❌ Lỗi quét web: {e}")
    return []

if __name__ == "__main__":
    print(f"🚀 Robot HSCV bắt đầu lúc: {time.strftime('%H:%M:%S')}")
    sheet = ket_noi_sheets()
    
    if sheet:
        danh_sach_moi = quet_du_lieu_that()
        
        if not danh_sach_moi:
            print("📭 Đã đăng nhập nhưng không tìm thấy văn bản nào thực tế.")
        else:
            # Lấy danh sách số hiệu cũ trong cột A để đối chiếu (tránh trùng)
            try:
                da_co = sheet.col_values(1)
            except:
                da_co = []

            moi = 0
            for vb in reversed(danh_sach_moi):
                if vb[0] not in da_co:
                    # Ghi vào Sheets (chèn vào dòng 2 để văn bản mới nhất luôn ở trên)
                    sheet.insert_row(vb, 2)
                    
                    # Gửi tin nhắn Telegram
                    msg = f"🔔 **CÓ VĂN BẢN MỚI!**\n\n📌 **Số:** `{vb[0]}`\n📅 **Ngày:** {vb[1]}\n📝 **ND:** {vb[2]}"
                    bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                    
                    print(f"✅ Đã báo cáo: {vb[0]}")
                    moi += 1
            
            if moi == 0:
                print("☕ Không có văn bản nào mới so với danh sách đã lưu.")
                
    print("🏁 Robot đã hoàn thành công việc.")
