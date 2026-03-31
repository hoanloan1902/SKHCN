import os
import json
import gspread
import telebot
import requests
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

# --- LAY BIEN MOI TRUONG ---
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
        print(f"Loi Sheets: {e}")
        return None

def quet_web_so_khcn():
    # Day la vi du quet trang van ban (Anh co the thay link cua So vao day)
    url = "https://sokhcn.dienbien.gov.vn/van-ban" 
    print(f"Dang quet: {url}")
    # Gia su tra ve mot danh sach van ban mau de anh test
    return [["123/QD-SKHCN", "31/03/2026", "Quyet dinh ve viec phe duyet de tai..."]]

if __name__ == "__main__":
    print("🚀 Robot bat dau lam viec...")
    sheet = ket_noi_sheets()
    
    if sheet:
        # Lay du lieu moi tu web
        danh_sach_moi = quet_web_so_khcn()
        so_hieu_da_co = sheet.col_values(1)

        for vb in danh_sach_moi:
            if vb[0] not in so_hieu_da_co:
                sheet.append_row(vb)
                # Gui thong bao ve Telegram cho anh Hoan
                thong_bao = f"🔔 **CO VAN BAN MOI!**\n📌 So: {vb[0]}\n📅 Ngay: {vb[1]}\n📝 ND: {vb[2]}"
                bot.send_message(CHAT_ID, thong_bao, parse_mode="Markdown")
                print(f"✅ Da luu va thong bao van ban: {vb[0]}")
    
    print("🏁 Robot da hoan thanh cong viec va dang nghi ngoi.")
