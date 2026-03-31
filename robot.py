import os
import json
import gspread
import telebot
import requests
import urllib3
import time
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

# Tắt cảnh báo bảo mật
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- THÔNG TIN TỪ GITHUB SECRETS ---
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

def quet_hscv_phien_ban_chot():
    url_login = "https://hscvkhcn.dienbien.gov.vn/login"
    # Link hang ổ chứa dữ liệu anh tìm được
    url_target = "https://hscvkhcn.dienbien.gov.vn/qlvb/vbden.nsf/Private_ChoXL_KoHan?openForm"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        print(f"🔑 Đang đăng nhập tài khoản: {USER_NAME}...")
        # SỬA QUAN TRỌNG: 'Username' viết hoa theo đúng mã nguồn anh gửi
        payload = {
            'Username': USER_NAME, 
            'Password': PASS_WORD, 
            'submit': 'Đăng nhập'
        }
        session.post(url_login, data=payload, headers=headers, verify=False, timeout=30)
        
        # Truy cập link dữ liệu
        print("🎯 Đang lấy danh sách văn bản chờ xử lý...")
        response = session.get(url_target, headers=headers, verify=False, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            ds_van_ban = []
            
            rows = soup.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                # Dựa trên ảnh thực tế bảng Lotus Notes của anh
                if len(cols) >= 6:
                    txt = [c.get_text(strip=True) for c in cols]
                    
                    # Lọc lấy dòng có ngày tháng ở cột index 2 (cột thứ 3)
                    ngay = txt[2]
                    if "/" in ngay and len(ngay) == 10:
                        so_hieu = txt[3] # Cột 4
                        trich_yeu = txt[5] # Cột 6
                        ds_van_ban.append([so_hieu, ngay, trich_yeu])
            
            return ds_van_ban
    except Exception as e:
        print(f"❌ Lỗi quét dữ liệu: {e}")
    return []

if __name__ == "__main__":
    print(f"🚀 Robot HSCV bắt đầu phiên làm việc: {time.strftime('%H:%M:%S')}")
    sheet = ket_noi_sheets()
    
    if sheet:
        danh_sach = quet_hscv_phien_ban_chot()
        if not danh_sach:
            print("📭 Không tìm thấy văn bản nào. Anh kiểm tra lại link hoặc quyền truy cập nhé.")
        else:
            try:
                da_co = sheet.col_values(1) # Lấy danh sách số hiệu đã lưu
            except:
                da_co = []

            moi = 0
            for vb in reversed(danh_sach):
                if vb[0] not in da_co:
                    sheet.insert_row(vb, 2) # Lưu vào dòng 2 của Google Sheets
                    # Gửi tin nhắn báo cho anh Hoàn
                    msg = f"🔔 **CÓ VĂN BẢN MỚI!**\n\n📌 **Số:** `{vb[0]}`\n📅 **Ngày:** {vb[1]}\n📝 **Nội dung:** {vb[2]}"
                    bot.send_message(CHAT_ID, msg)
                    print(f"✅ Đã báo cáo: {vb[0]}")
                    moi += 1
            
            if moi == 0:
                print("☕ Hệ thống chưa có gì mới, anh cứ thong thả nghỉ ngơi.")
    print("🏁 Robot hoàn thành ca trực.")
