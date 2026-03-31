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

# --- THÔNG TIN CẤU HÌNH ---
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

def quet_du_lieu_lotus_v2():
    url_login = "https://hscvkhcn.dienbien.gov.vn/login"
    url_target = "https://hscvkhcn.dienbien.gov.vn/qlvb/vbden.nsf/Private_ChoXL_KoHan?openForm"
    
    # Dùng Session để giữ kết nối xuyên suốt
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        print(f"🔑 Đang thực hiện đăng nhập cho tài khoản: {USER_NAME}...")
        
        # Bước 1: Lấy trang login để nhận Cookie ban đầu
        session.get(url_login, headers=headers, verify=False, timeout=20)
        
        # Bước 2: Gửi dữ liệu đăng nhập
        payload = {
            'Username': USER_NAME,
            'Password': PASS_WORD,
            'RedirectTo': '/qlvb/vbden.nsf/Private_ChoXL_KoHan?openForm', # Yêu cầu chuyển hướng thẳng sau khi login
            '__Click': '0'
        }
        
        login_res = session.post(url_login, data=payload, headers=headers, verify=False, timeout=30)
        
        # Bước 3: Truy cập link mục tiêu (thử lại 2 lần)
        for attempt in range(2):
            print(f"🎯 Đang truy quét dữ liệu (Lần {attempt+1})...")
            response = session.get(url_target, headers=headers, verify=False, timeout=30)
            
            # Nếu hệ thống trả về mã nguồn, mình sẽ phân tích mạnh hơn
            content = response.text
            if "Ngày đến" in content or "Số hiệu" in content or "tr" in content.lower():
                soup = BeautifulSoup(content, 'html.parser')
                ds_van_ban = []
                
                # Tìm tất cả hàng bảng <tr>
                rows = soup.find_all('tr')
                for row in rows:
                    cols = row.find_all(['td', 'font']) # Lotus hay dùng thẻ font để hiện chữ
                    txt = [c.get_text(strip=True) for c in cols if c.get_text(strip=True)]
                    
                    # Tìm cột có định dạng ngày dd/mm/yyyy
                    found_date = None
                    for t in txt:
                        if re.search(r'\d{2}/\d{2}/\d{4}', t):
                            found_date = t
                            break
                    
                    if found_date and len(txt) >= 3:
                        # Thử bóc tách thông tin dựa trên vị trí phổ biến của Lotus
                        # Thường là: [STT, Ngày, Số hiệu, Cơ quan, Nội dung]
                        so_hieu = ""
                        noi_dung = ""
                        for item in txt:
                            if "/" in item and item != found_date: so_hieu = item
                            if len(item) > 20: noi_dung = item # Nội dung thường là chuỗi dài nhất
                        
                        if so_hieu:
                            ds_van_ban.append([so_hieu, found_date, noi_dung])
                
                if ds_van_ban: return ds_van_ban
            
            time.sleep(3) # Đợi một chút nếu lần 1 chưa ra
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    return []

if __name__ == "__main__":
    print(f"🚀 Robot HSCV khởi động: {time.strftime('%H:%M:%S')}")
    sheet = ket_noi_sheets()
    
    if sheet:
        danh_sach = quet_du_lieu_lotus_v2()
        if not danh_sach:
            print("📭 Vẫn chưa bóc tách được bảng. Hệ thống này khóa dữ liệu rất kỹ.")
        else:
            print(f"✅ Tìm thấy {len(danh_sach)} văn bản thực tế!")
            try:
                da_co = sheet.col_values(1)
            except:
                da_co = []

            moi = 0
            for vb in reversed(danh_sach):
                if vb[0] not in da_co:
                    sheet.insert_row(vb, 2)
                    msg = f"🔔 **VĂN BẢN HSCV MỚI!**\n📌 Số: `{vb[0]}`\n📅 Ngày: {vb[1]}\n📝 ND: {vb[2]}"
                    bot.send_message(CHAT_ID, msg)
                    print(f"✅ Báo cáo thành công: {vb[0]}")
                    moi += 1
            
            if moi == 0:
                print("☕ Không có văn bản mới nào.")
    print("🏁 Kết thúc ca trực.")
