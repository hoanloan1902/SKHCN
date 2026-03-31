import time
import os
import json
import re
import gspread
from datetime import datetime
import telebot
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CẤU HÌNH HỆ THỐNG ---
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
USER_NAME = os.environ.get("SKHCN_USER", "")
PASS_WORD = os.environ.get("SKHCN_PASS", "")
GOOGLE_JSON = os.environ.get("GSPREAD_SERVICE_ACCOUNT", "")

bot = telebot.TeleBot(TOKEN)

def ket_noi_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_JSON), scope)
        return gspread.authorize(creds).open("DANH_SACH_VAN_BAN").sheet1
    except Exception as e:
        print(f"Lỗi Sheets: {e}")
        return None

# --- BỘ NÃO XỬ LÝ KỊCH BẢN (TRẢ LỜI ANH HOÀN) ---
@bot.message_handler(func=lambda message: True)
def handle_assistant(message):
    txt = message.text.lower().strip()
    sheet = ket_noi_sheets()
    if not sheet: return
    
    all_data = sheet.get_all_values()[1:] # Bỏ tiêu đề
    today_str = datetime.now().strftime("%d/%m/%Y")
    
    # 1. Kịch bản: "Danh sách X văn bản" (Lấy đúng số lượng anh yêu cầu)
    match_list = re.search(r'danh sách (\d+) văn bản', txt)
    if match_list:
        n = int(match_list.group(1))
        all_data.reverse() # Cái mới nhất lên đầu
        results = all_data[:n]
        msg = f"📋 **DANH SÁCH {len(results)} VĂN BẢN GẦN NHẤT**\n"
        for r in results:
            msg += f"📌 `{r[0]}` | {r[1]}\n📝 {r[2][:120]}...\n\n"
        bot.reply_to(message, msg, parse_mode="Markdown")
        return

    # 2. Kịch bản: "Sáng nay/Hôm nay có gì?"
    if any(k in txt for k in ["hôm nay", "sáng nay", "mới về"]):
        results = [r for r in all_data if today_str in r[1]]
        if not results:
            bot.reply_to(message, f"📅 Dạ anh Hoàn, hôm nay ({today_str}) chưa ghi nhận văn bản mới nào về hệ thống ạ.")
        else:
            msg = f"📅 **VĂN BẢN ĐẾN HÔM NAY ({len(results)} cái):**\n"
            for r in results:
                msg += f"✅ `{r[0]}`: {r[2][:100]}...\n"
            bot.reply_to(message, msg, parse_mode="Markdown")
        return

    # 3. Kịch bản: "Cái nào gấp/khẩn không?"
    if any(k in txt for k in ["gấp", "khẩn", "hỏa tốc", "hạn"]):
        keywords = ["khẩn", "hỏa tốc", "gấp", "hạn", "trước ngày"]
        results = [r for r in all_data if any(k in r[2].lower() for k in keywords)]
        if not results:
            bot.reply_to(message, "✅ Em kiểm tra thì hiện không có văn bản nào đánh dấu Gấp/Khẩn trong danh sách ạ.")
        else:
            msg = f"🚨 **VĂN BẢN CẦN XỬ LÝ GẤP ({len(results)} cái):**\n"
            for r in results:
                msg += f"⚠️ `{r[0]}`: {r[2][:150]}\n\n"
            bot.reply_to(message, msg, parse_mode="Markdown")
        return

    # 4. Kịch bản: Thống kê tổng quát
    if any(k in txt for k in ["thống kê", "bao nhiêu"]):
        bot.reply_to(message, f"📊 **THỐNG KÊ TỔNG QUÁT**\nChào anh Hoàn, hiện Sheets đang lưu trữ **{len(all_data)}** văn bản đến.")
        return

    bot.reply_to(message, "🤖 Em nghe rõ rồi sếp Hoàn! Anh có thể hỏi: 'Danh sách 24 văn bản', 'Sáng nay có gì mới' hoặc 'Có cái nào gấp không' nhé!")

# --- ROBOT QUÉT DỮ LIỆU ---
def quet_he_thong():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        driver.get("https://hscvkhcn.dienbien.gov.vn/names.nsf?Login")
        driver.find_element(By.NAME, "Username").send_keys(USER_NAME)
        driver.find_element(By.NAME, "Password").send_keys(PASS_WORD)
        driver.execute_script("document.forms[0].submit()")
        time.sleep(5)

        driver.get("https://hscvkhcn.dienbien.gov.vn/qlvb/vbden.nsf/default?openform&frm=Private_ChoXL?openForm")
        time.sleep(5)
        driver.switch_to.default_content()
        WebDriverWait(driver, 20).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "Main")))

        sheet = ket_noi_sheets()
        rows = driver.find_elements(By.TAG_NAME, "tr")
        ids_da_co = sheet.col_values(1) if sheet else []

        count_new = 0
        for row in rows:
            txt = row.text.strip()
            if "/" in txt and len(txt) > 10:
                so_hieu = txt.split()[0]
                if so_hieu not in ids_da_co:
                    bot.send_message(CHAT_ID, f"🚀 **CÓ VĂN BẢN MỚI**\n📄 Số: `{so_hieu}`\n📝 {txt[:150]}...", parse_mode="Markdown")
                    if sheet:
                        sheet.append_row([so_hieu, datetime.now().strftime("%d/%m/%Y %H:%M"), txt])
                    ids_da_co.append(so_hieu)
                    count_new += 1
        print(f"Đã quét xong. Tìm thấy {count_new} văn bản mới.")
    finally:
        driver.quit()

if __name__ == "__main__":
    # 1. Quét web trước để cập nhật Sheets
    quet_he_thong()
    # 2. Thức 10 phút để anh Hoàn ra lệnh thông minh
    print("Robot đang trực tuyến, đợi lệnh sếp Hoàn...")
    start = time.time()
    while time.time() - start < 600:
        try: bot.polling(none_stop=True, timeout=10)
        except: time.sleep(5)
