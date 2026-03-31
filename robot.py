import os
import json
import gspread
import telebot
import requests
import urllib3
import time
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- THÔNG TIN TỪ GITHUB ---
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
        print(f"❌ Lỗi Sheets: {e}")
        return None

def quet_hscv_chuan_xac():
    # Sử dụng link Private anh vừa tìm thấy
    url_login = "https://hscvkhcn.dienbien.gov.vn/login"
    url_target = "https://hscvkhcn.dienbien.gov.vn/qlvb/vbden.nsf/Private_ChoXL_KoHan?openForm"
    
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    try:
        print(f"🔑 Đang đăng nhập hệ thống HSCV...")
        payload = {'username': USER_NAME, 'password': PASS_WORD, 'submit': 'Đăng nhập'}
        session.post(url_login, data=payload, headers=headers, verify=False, timeout=30)
        
        # Truy cập trực tiếp link danh sách chờ xử lý
        print(f"🎯 Đang quét danh sách: Chờ xử lý...")
        response = session.get(url_target, headers=headers, verify=False, timeout=45)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            ds_van_ban = []
            
            # Quét tất cả các hàng trong bảng
            rows = soup.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                # Trong hệ thống Lotus, hàng dữ liệu thường có từ 5-10 cột
                if len(cols) >= 5:
                    txt = [c.get_text(strip=True) for c in cols]
                    
                    # Kiểm tra cột ngày tháng (thường là cột 2 hoặc 3)
                    # Định dạng ngày của Lotus thường là dd/mm/yyyy
                    ngay_den = ""
                    for item in txt:
                        if len(item) == 10 and item.count("/") == 2:
                            ngay_den = item
                            break
                    
                    if ngay_den:
                        # Số hiệu thường nằm sau ngày hoặc ở một vị trí cố định
                        # Em sẽ lấy Số hiệu và Trích yếu dựa trên cấu trúc quan sát được
                        so_hieu = txt[3] if len(txt) > 3 else "Chưa rõ số"
                        trich_yeu = txt[5] if len(txt) > 5 else "Không có nội dung"
                        
                        # Chỉ lấy nếu số hiệu không phải là tiêu đề
                        if "/" in so_hieu or "-" in so_hieu:
                            ds_van_ban.append([so_hieu, ngay_den, trich_yeu])
            
            return ds_van_ban
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    return []

if __name__ == "__main__":
    print(f"🚀 Robot HSCV khởi động: {time.strftime('%H:%M:%S')}")
    sheet = ket_noi_sheets()
    
    if sheet:
        danh_sach = quet_hscv_chuan_xac()
        if not danh_sach:
            print("📭 Đăng nhập thành công nhưng chưa lấy được bảng. Có thể cần thêm bước click.")
        else:
            try:
                da_co = sheet.col_values(1)
            except:
                da_co = []

            moi = 0
            # Duyệt từ văn bản cũ nhất đến mới nhất để chèn vào Sheets
            for vb in reversed(danh_sach):
                if vb[0] not in da_co:
                    sheet.insert_row(vb, 2)
                    msg = f"🔔 **VĂN BẢN CHỜ XỬ LÝ!**\n📌 Số: `{vb[0]}`\n📅 Ngày đến: {vb[1]}\n📝 ND: {vb[2]}"
                    bot.send_message(CHAT_ID, msg)
                    print(f"✅ Đã báo cáo: {vb[0]}")
                    moi += 1
            
            if moi == 0:
                print("☕ Không có văn bản nào mới.")
    print("🏁 Robot hoàn thành ca trực.")
