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

# Tat canh bao SSL cho he thong HSCV
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
        print(f"!!! LOI KET NOI SHEETS: {e}")
        return None

def lay_van_ban():
    base_url = "https://hscvkhcn.dienbien.gov.vn"
    url_login = f"{base_url}/qlvb/index.nsf/default?openform"
    url_post = f"{base_url}/names.nsf?Login"
    url_target = f"{base_url}/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    try:
        print("--- Dang dang nhap he thong So KHCN ---")
        session.get(url_login, headers=headers, verify=False, timeout=15)
        payload = {
            'Username': USER_NAME, 
            'Password': PASS_WORD,
            'RedirectTo': '/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm'
        }
        res = session.post(url_post, data=payload, headers=headers, verify=False)
        
        if 'Username' in res.text:
            print("!!! Dang nhap THAT BAI. Kiem tra lai SKHCN_USER/PASS")
            return []

        print("--- Dang quet danh sach van ban ---")
        response = session.get(url_target, headers=headers, verify=False, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        ket_qua = []
        for row in soup.find_all('tr'):
            tds = row.find_all('td')
            if len(tds) < 5: continue
            cols = [td.get_text().strip() for td in tds]
            # Tim dong co chua ngay thang
            for i, c in enumerate(cols):
                if re.match(r'^\d{2}/\d{2}/\d{4}$', c):
                    so_hieu = cols[i+1] if i+1 < len(cols) else "N/A"
                    ngay = c
                    trich_yeu = cols[i+3] if i+3 < len(cols) else ""
                    ket_qua.append([so_hieu, ngay, trich_yeu])
                    break
        return ket_qua
    except Exception as e:
        print(f"!!! LOI QUET VAN BAN: {e}")
        return []

@app.route(f"/{TOKEN}", methods=['POST'])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return '', 403

@app.route('/')
def home():
    return "Robot SKHCN is LIVE!", 200

@bot.message_handler(func=lambda m: True)
def phan_hoi(message):
    print(f"-> Nhan tin: '{message.text}' tu ID: {message.chat.id}")
    cmd = message.text.lower()

    if any(x in cmd for x in ['bao nhieu', 'tổng số', 'thống kê']):
        bot.send_message(message.chat.id, "⏳ Dang dem trong Google Sheets...")
        sheet = ket_noi_sheets()
        if sheet:
            count = len(sheet.col_values(1)) - 1
            bot.reply_to(message, f"📊 Tổng văn bản hiện có: *{count}*", parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Loi ket noi Google Sheets!")

    elif any(x in cmd for x in ['mới nhất', 'danh sách', 'van ban']):
        bot.send_message(message.chat.id, "⏳ Dang quet HSCV cua So...")
        ds = lay_van_ban()
        if ds:
            msg = "📋 *VĂN BẢN MỚI NHẤT:*\n\n"
            for i, v in enumerate(ds[:5], 1):
                msg += f"{i}. `{v[0]}` - {v[1]}\n📝 {v[2][:100]}...\n\n"
            bot.reply_to(message, msg, parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Khong tim thay van ban nao hoac loi dang nhap!")
    
    else:
        bot.reply_to(message, "Chào anh Hoàn! Em đã sẵn sàng. Anh hãy nhắn 'tổng số' hoặc 'văn bản' để em báo cáo nhé!")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
