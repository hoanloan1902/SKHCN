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

# Tắt cảnh báo bảo mật
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- LẤY BIẾN MÔI TRƯỜNG ---
USER_NAME = os.environ.get("SKHCN_USER")
PASS_WORD = os.environ.get("SKHCN_PASS")
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_JSON = os.environ.get("GSPREAD_SERVICE_ACCOUNT")
CHAT_ID = os.environ.get("CHAT_ID")
SHEET_NAME = "DANH_SACH_VAN_BAN"

bot = telebot.TeleBot(TOKEN)

# Biến tạm để lưu thống kê trong phiên chạy
stats = {"tong_so": 0, "moi": 0, "last_run": ""}

def ket_noi_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_JSON), scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).sheet1
    except Exception as e:
        print(f"❌ Lỗi Sheets: {e}")
        return None

def quet_he_thong_hscv():
    base_url = "https://hscvkhcn.dienbien.gov.vn"
    url_post = f"{base_url}/names.nsf?Login"
    url_target = f"{base_url}/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        # Đăng nhập
        session.post(url_post, data={
            'Username': USER_NAME,
            'Password': PASS_WORD,
            'RedirectTo': '/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm',
        }, headers=headers, verify=False)
        
        # Quét dữ liệu
        response = session.get(url_target, headers=headers, verify=False, timeout=30)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        ket_qua = []
        for row in soup.find_all('tr'):
            tds = row.find_all('td')
            if len(tds) < 5: continue
            cols = [re.sub(r'\s+', ' ', td.get_text()).strip() for td in tds]
            
            for i, c in enumerate(cols):
                if re.match(r'^\d{2}/\d{2}/\d{4}$', c):
                    ngay = c
                    so_hieu = cols[i+1] if i+1 < len(cols) else ""
                    co_quan = cols[i+2] if i+2 < len(cols) else ""
                    trich_yeu = cols[i+3] if i+3 < len(cols) else ""
                    if "/" in so_hieu:
                        ket_qua.append([so_hieu, ngay, trich_yeu, co_quan])
                    break
        return ket_qua
    except Exception as e:
        print(f"❌ Lỗi quét: {e}")
        return []

# --- XỬ LÝ LỆNH TELEGRAM ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Chào anh Hoàn! Em là Robot HSCV. Anh có thể dùng lệnh /thongke để xem tình hình văn bản nhé.")

@bot.message_handler(commands=['thongke'])
def send_stats(message):
    msg = (
        f"📊 **THỐNG KÊ HỆ THỐNG**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📩 Tổng văn bản chờ xử lý: `{stats['tong_so']}`\n"
                f"🆕 Văn bản mới vừa quét: `{stats['moi']}`\n"
        f"⏰ Cập nhật lúc: {stats['last_run']}\n"
        f"📂 Dữ liệu đã lưu tại Google Sheets."
    )
    bot.reply_to(message, msg, parse_mode='Markdown')

def thuc_thi_nhiem_vu():
    print(f"=== Bắt đầu quét: {time.strftime('%H:%M:%S')} ===")
    sheet = ket_noi_sheets()
    if not sheet: return

    danh_sach = quet_he_thong_hscv()
    stats['tong_so'] = len(danh_sach)
    stats['last_run'] = time.strftime('%H:%M:%S')
    
    if danh_sach:
        try:
            da_co = sheet.col_values(1)
        except:
            da_co = []

        moi_count = 0
        for vb in reversed(danh_sach):
            if vb[0] not in da_co:
                sheet.insert_row(vb, 2)
                thong_bao = (
                    f"🔔 **VĂN BẢN MỚI!**\n"
                    f"📌 Số: `{vb[0]}`\n"
                    f"📅 Ngày: {vb[1]}\n"
                    f"🏢 Nơi gửi: {vb[3]}\n"
                    f"📝 ND: {vb[2][:150]}..."
                )
                bot.send_message(CHAT_ID, thong_bao, parse_mode='Markdown')
                moi_count += 1
                time.sleep(1)
        
        stats['moi'] = moi_count
        # Gửi báo cáo tổng kết tự động
        report = f"✅ Đã quét xong! Tìm thấy `{moi_count}` văn bản mới. Tổng chờ xử lý: `{len(danh_sach)}`."
        bot.send_message(CHAT_ID, report, parse_mode='Markdown')

if __name__ == "__main__":
    # 1. Thực hiện quét dữ liệu trước
    thuc_thi_nhiem_vu()
    
    # 2. Bật chế độ lắng nghe tin nhắn trong 5 phút (để anh Hoàn có thể hỏi thống kê)
    print("🤖 Robot đang lắng nghe lệnh (trong 5 phút)...")
    # Lưu ý: Vì chạy trên GitHub Actions nên không thể để Robot thức mãi mãi (sẽ bị lỗi timeout)
    # Em để 5 phút để anh kịp kiểm tra và hỏi lệnh.
    bot.polling(none_stop=True, interval=0, timeout=20)
