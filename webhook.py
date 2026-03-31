import os
import json
import requests
import urllib3
import re
import time
from flask import Flask, request
import telebot
import gspread
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- LAY BIEN MOI TRUONG ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_JSON = os.environ.get("GSPREAD_SERVICE_ACCOUNT")
CHAT_ID = os.environ.get("CHAT_ID")
USER_NAME = os.environ.get("SKHCN_USER")
PASS_WORD = os.environ.get("SKHCN_PASS")
SHEET_NAME = "DANH_SACH_VAN_BAN"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def ket_noi_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_JSON), scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).sheet1
    except Exception as e:
        print(f"Loi Sheets: {e}")
        return None

def lay_van_ban():
    base_url = "https://hscvkhcn.dienbien.gov.vn"
    url_login = f"{base_url}/qlvb/index.nsf/default?openform"
    url_post = f"{base_url}/names.nsf?Login"
    url_target = f"{base_url}/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm"
    session = requests.Session()
    headers_get = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    headers_post = {**headers_get, 'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': base_url, 'Referer': url_login}

    def parse_trang(html):
        soup = BeautifulSoup(html, 'html.parser')
        ket_qua = []
        for row in soup.find_all('tr'):
            tds = row.find_all('td')
            if len(tds) < 5: continue
            cols = [re.sub(r'\s+', ' ', td.get_text()).strip() for td in tds]
            so_den = ngay_den = so_hieu = co_quan = trich_yeu = ""
            for i, c in enumerate(cols):
                if re.match(r'^\d{2}/\d{2}/\d{4}$', c):
                    ngay_den = c
                    so_den = cols[i-1] if i >= 1 else ""
                    so_hieu = cols[i+1] if i+1 < len(cols) else ""
                    co_quan = cols[i+2] if i+2 < len(cols) else ""
                    trich_yeu = cols[i+3] if i+3 < len(cols) else ""
                    break
            if ngay_den and so_hieu and re.search(r'\d+', so_den):
                if so_hieu.strip() and '/' in so_hieu:
                    ket_qua.append([so_hieu.strip(), ngay_den, trich_yeu[:200], co_quan, so_den])
        return ket_qua

    try:
        session.get(url_login, headers=headers_get, verify=False, timeout=15)
        res_login = session.post(url_post, data={
            'Username': USER_NAME, 'Password': PASS_WORD,
            'RedirectTo': '/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm',
        }, headers=headers_post, verify=False, allow_redirects=True)

        if 'Username' in res_login.text and 'Password' in res_login.text:
            return []

        ds_van_ban = []
        for trang in range(1, 11):
            url_trang = url_target if trang == 1 else f"{base_url}/qlvb/vbden.nsf/Private_ChoXL_KoHan?openForm&p={trang}"
            response = session.get(url_trang, headers=headers_get, verify=False, timeout=25)
            vb_trang = parse_trang(response.text)
            if not vb_trang: break
            ds_van_ban.extend(vb_trang)

        seen = set()
        ds_unique = []
        for vb in ds_van_ban:
            if vb[0] not in seen:
                seen.add(vb[0])
                ds_unique.append(vb)
        return ds_unique
    except Exception as e:
        print(f"Loi: {e}")
        return []

@app.route(f"/{TOKEN}", methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return 'ok', 200

@app.route('/')
def index():
    return 'Bot dang chay!', 200

@bot.message_handler(func=lambda m: True)
def xu_ly_tin_nhan(message):
    text = message.text.lower().strip()
    # Thong ke
    if any(x in text for x in ['bao nhieu', 'bao nhiêu', 'tong so', 'tổng số']):
        bot.send_message(message.chat.id, "⏳ Đang đếm văn bản trong Sheets, đợi xíu nhé...")
        sheet = ket_noi_sheets()
        if sheet:
            try:
                da_co = sheet.col_values(1)
                tong = len([x for x in da_co if x]) - 1 # Tru dong tieu de
                bot.reply_to(message, f"📊 *THỐNG KÊ*\n✅ Tổng văn bản: *{tong}*\n🕐 Lúc: {time.strftime('%H:%M')}", parse_mode='Markdown')
            except Exception as e:
                bot.reply_to(message, f"❌ Lỗi Sheets: {e}")
        else:
            bot.reply_to(message, "❌ Không kết nối được Sheets!")
    # Danh sach van ban moi
    elif any(x in text for x in ['danh sach', 'danh sách', 'mới nhất']):
        bot.send_message(message.chat.id, "⏳ Đang quét hệ thống Sở, đợi anh Hoàn xíu nhé...")
        danh_sach = lay_van_ban()
        if not danh_sach:
            bot.reply_to(message, "❌ Không lấy được dữ liệu mới!")
            return
        msg = "📋 *VĂN BẢN MỚI NHẤT:*\n\n"
        for i, vb in enumerate(danh_sach[:5], 1): # Hien 5 cai thoi cho do dai
            msg += f"{i}. `{vb[0]}`\n📝 {vb[2][:100]}...\n\n"
        bot.reply_to(message, msg, parse_mode='Markdown')
    else:
        bot.reply_to(message, "👋 Chào anh Hoàn! Anh có thể hỏi 'tổng số' hoặc 'danh sách' để em báo cáo nhé.")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
