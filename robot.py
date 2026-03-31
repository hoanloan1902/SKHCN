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

# --- BIẾN MÔI TRƯỜNG ---
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

def quet_du_lieu_lotus():
    url_login = "https://hscvkhcn.dienbien.gov.vn/login"
    # Link này là "ruột" của danh sách văn bản chờ xử lý
    url_target = "https://hscvkhcn.dienbien.gov.vn/qlvb/vbden.nsf/Private_ChoXL_KoHan?openForm"
    
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Referer': url_login
    }
    
    try:
        print(f"🔑 Đăng nhập hệ thống (User: {USER_NAME})...")
        payload = {'Username': USER_NAME, 'Password': PASS_WORD, 'submit': 'Đăng nhập'}
        session.post(url_login, data=payload, headers=headers, verify=False, timeout=30)
        
        # Đợi 2 giây để hệ thống thiết lập Session
        time.sleep(2)
        
        print("🎯 Đang truy cập hang ổ dữ liệu...")
        response = session.get(url_target, headers=headers, verify=False, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            ds_van_ban = []
            
            # CHIẾN THUẬT MỚI: Quét tất cả các thẻ <td> có chứa định dạng ngày dd/mm/yyyy
            all_tds = soup.find_all('td')
            temp_row = []
            
            for td in all_tds:
                text = td.get_text(strip=True)
                # Kiểm tra nếu là ngày tháng
                if re.match(r'\d{2}/\d{2}/\d{4}', text):
                    if temp_row: # Nếu đã có hàng trước đó thì lưu lại
                        ds_van_ban.append(temp_row)
                    temp_row = [text] # Bắt đầu hàng mới với cột Ngày
                elif temp_row and len(temp_row) < 3:
                    if text: # Thêm Số hiệu và Trích yếu vào hàng
                        temp_row.append(text)
            
            # Thêm hàng cuối cùng nếu có
            if temp_row and len(temp_row) >= 2:
                ds_van_ban.append(temp_row)
                
            return ds_van_ban
    except Exception as e:
        print(f"❌ Lỗi hệ thống: {e}")
    return []

if __name__ == "__main__":
    print(f"🚀 Robot khởi động: {time.strftime('%H:%M:%S')}")
    sheet = ket_noi_sheets()
    
    if sheet:
        danh_sach = quet_du_lieu_lotus()
        if not danh_sach:
            print("📭 Vẫn chưa thấy bảng. Có thể cần cấu hình iFrame.")
        else:
            print(f"✅ Đã tìm thấy {len(danh_sach)} văn bản!")
            try:
                da_co = sheet.col_values(1)
            except:
                da_co = []

            moi = 0
            for vb in reversed(danh_sach):
                # Chuẩn hóa hàng dữ liệu (đảm bảo có 3 cột: Số hiệu, Ngày, ND)
                # Vì cấu hình quét mới, mình đảo lại vị trí cho đúng Sheets: [Số hiệu, Ngày, ND]
                if len(vb) >= 2:
                    ngay = vb[0]
                    so_hieu = vb[1]
                    nd = vb[2] if len(vb) > 2 else "Không có nội dung"
                    
                    row_data = [so_hieu, ngay, nd]
                    
                    if so_hieu not in da_co:
                        sheet.insert_row(row_data, 2)
                        msg = f"🔔 **VĂN BẢN HSCV MỚI!**\n📌 Số: `{so_hieu}`\n📅 Ngày: {ngay}\n📝 ND: {nd}"
                        bot.send_message(CHAT_ID, msg)
                        print(f"✅ Đã báo cáo: {so_hieu}")
                        moi += 1
                        time.sleep(1)
            
            if moi == 0:
                print("☕ Không có gì mới.")
    print("🏁 Kết thúc.")
