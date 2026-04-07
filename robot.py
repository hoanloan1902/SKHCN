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

# Tắt cảnh báo bảo mật cho trang .gov.vn
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- BIẾN MÔI TRƯỜNG (Cấu hình trên GitHub Secrets) ---
USER_NAME = os.environ.get("SKHCN_USER")
PASS_WORD = os.environ.get("SKHCN_PASS")
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_JSON = os.environ.get("GSPREAD_SERVICE_ACCOUNT")
CHAT_ID = os.environ.get("CHAT_ID")
SHEET_NAME = "DANH_SACH_VAN_BAN"

def ket_noi_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_JSON), scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME)
    except Exception as e:
        print(f"❌ Lỗi kết nối Google Sheets: {e}")
        return None

def quet_he_thong_hscv():
    base_url = "https://hscvkhcn.dienbien.gov.vn"
    url_post = f"{base_url}/names.nsf?Login"
    url_target = f"{base_url}/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        # 1. Đăng nhập hệ thống
        session.post(url_post, data={
            'Username': USER_NAME,
            'Password': PASS_WORD,
            'RedirectTo': '/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm',
        }, headers=headers, verify=False)
        
        # 2. Lấy dữ liệu trang mục tiêu
        response = session.get(url_target, headers=headers, verify=False, timeout=30)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        ket_qua = []
        for row in soup.find_all('tr'):
            tds = row.find_all('td')
            if len(tds) < 5: continue
            cols = [re.sub(r'\s+', ' ', td.get_text()).strip() for td in tds]
            
            # Khớp định dạng ngày dd/mm/yyyy như trong ảnh của anh
            for i, c in enumerate(cols):
                if re.match(r'^\d{2}/\d{2}/\d{4}$', c):
                    ngay = c
                    so_hieu = cols[i+1] if i+1 < len(cols) else ""
                    co_quan = cols[i+2] if i+2 < len(cols) else ""
                    trich_yeu = cols[i+3] if i+3 < len(cols) else ""                                        if "/" in so_hieu or "-" in so_hieu:
                        # Thứ tự: Số hiệu, Ngày, Trích yếu, Nơi gửi (Khớp cột A, B, C, D)
                        ket_qua.append([so_hieu, ngay, trich_yeu, co_quan])
                    break
        return ket_qua
    except Exception as e:
        print(f"❌ Lỗi khi quét web: {e}")
        return []

def cap_nhat_he_thong():
    print(f"🚀 Bắt đầu phiên quét: {time.strftime('%d/%m/%Y %H:%M:%S')}")
    workbook = ket_noi_sheets()
    if not workbook: return
    
    sheet_main = workbook.sheet1
    try:
        sheet_status = workbook.worksheet("STATUS")
    except:
        print("⚠️ CẢNH BÁO: Anh chưa tạo tab 'STATUS'. Vui lòng tạo để Bot 24/7 hoạt động.")
        return
    
    danh_sach = quet_he_thong_hscv()
    if not danh_sach:
        print("📭 Không tìm thấy dữ liệu mới hoặc lỗi login.")
        return

    # Lấy danh sách số hiệu cũ để tránh ghi trùng
    try:
        da_co = sheet_main.col_values(1)
    except:
        da_co = []

    moi_count = 0
    bot = telebot.TeleBot(TOKEN)

    # Ghi văn bản mới lên đầu (Dưới dòng tiêu đề)
    for vb in reversed(danh_sach):
        if vb[0] not in da_co:
            sheet_main.insert_row(vb, 2)
            # Bắn thông báo Telegram cho anh Hoàn
            msg = (f"🔔 *CÓ VĂN BẢN MỚI*\n"
                   f"📌 *Số:* `{vb[0]}`\n"
                   f"🏢 *Gửi từ:* {vb[3]}\n"
                   f"📝 *Nội dung:* {vb[2][:150]}...")
            bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
            moi_count += 1
            time.sleep(1) # Tránh bị Telegram chặn do gửi nhanh

    # Cập nhật bảng STATUS để Bot phản hồi 24/7 lấy dữ liệu trả lời anh
    status_update = [
        ["THÔNG SỐ", "GIÁ TRỊ"],
        ["tong_so", len(danh_sach)],
        ["moi_phien_nay", moi_count],
        ["cap_nhat_cuoi", time.strftime('%H:%M:%S %d/%m/%Y')]
    ]
    sheet_status.update("A1:B4", status_update)
    print(f"✅ Xong! Thêm mới {moi_count} văn bản. Tổng chờ xử lý: {len(danh_sach)}")

if __name__ == "__main__":
    cap_nhat_he_thong()
