import time
import os
import json
import logging
import requests
from datetime import datetime
from telebot import telebot
from threading import Thread
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ============================================================
# CẤU HÌNH (Lấy từ Secrets của GitHub)
# ============================================================
USER_NAME       = os.environ.get("SKHCN_USER", "")
PASS_WORD       = os.environ.get("SKHCN_PASS", "")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
URL_LOGIN      = "https://hscvkhcn.dienbien.gov.vn/names.nsf?Login"
URL_DANH_SACH  = "https://hscvkhcn.dienbien.gov.vn/qlvb/vbden.nsf/default?openform&frm=Private_ChoXL?openForm"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
FILE_DA_GUI = "da_gui.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# --- HÀM TẢI/LƯU DỮ LIỆU ---
def tai_ds():
    try:
        if os.path.exists(FILE_DA_GUI):
            with open(FILE_DA_GUI, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {item['so_cv']: item for item in data if isinstance(item, dict)}
    except: pass
    return {}

def luu_ds(du_lieu):
    with open(FILE_DA_GUI, "w", encoding="utf-8") as f:
        json.dump(list(du_lieu.values()), f, ensure_ascii=False, indent=2)

# --- TRỢ LÝ ẢO (THỨC 10 PHÚT ĐỂ TRẢ LỜI ANH) ---
@bot.message_handler(func=lambda message: True)
def handle_assistant(message):
    text = message.text.lower() if message.text else ""
    if any(k in text for k in ["thống kê", "bao nhiêu", "tình hình"]):
        ds = tai_ds()
        msg = f"📊 <b>THỐNG KÊ HỆ THỐNG</b>\n────────────────\n✅ Tổng văn bản đã lưu: <b>{len(ds)}</b>\n🚀 Robot đang thức đợi lệnh anh Hoàn!"
        bot.reply_to(message, msg, parse_mode="HTML")

# --- ROBOT QUÉT CHÍNH ---
def chay_robot():
    log.info("=== BẮT ĐẦU QUÉT V3.1 (CHỐNG NHẢY CỘT) ===")
    driver = None
    du_lieu = tai_ds()
    co_thay_doi = False
    
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        driver.get(URL_LOGIN)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "Username"))).send_keys(USER_NAME)
        driver.find_element(By.NAME, "Password").send_keys(PASS_WORD)
        driver.execute_script("document.forms[0].submit()")
        time.sleep(7)

        driver.get(URL_DANH_SACH)
        time.sleep(7)
        driver.switch_to.default_content()
        try:
            WebDriverWait(driver, 20).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "Main")))
        except: pass

        rows = driver.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 5: continue # Bỏ qua hàng rác
            
            # LẤY DỮ LIỆU THÔNG MINH:
            # Thông thường: Cột 2 là Số hiệu, Cột 3 là Ngày, Cột 4 là Trích yếu
            raw_data = [c.text.strip() for c in cells]
            
            so_hieu = raw_data[2] if len(raw_data) > 2 else ""
            ngay_den = raw_data[3] if len(raw_data) > 3 else ""
            trich_yeu = raw_data[4] if len(raw_data) > 4 else ""
            han_xl = raw_data[5] if len(raw_data) > 5 else "Không có hạn"

            # Kiểm tra xem có đúng là văn bản không (phải có dấu / trong số hiệu)
            if "/" in so_hieu and so_hieu not in du_lieu:
                msg = (
                    f"🚀 <b>CÓ VĂN BẢN MỚI</b>\n"
                    f"────────────────────\n"
                    f"📌 <b>Số CV:</b> <code>{so_hieu}</code>\n"
                    f"📅 <b>Ngày đến:</b> {ngay_den}\n"
                    f"📝 <b>Trích yếu:</b> {trich_yeu[:300]}\n"
                    f"⏳ <b>Hạn xử lý:</b> {han_xl}\n"
                    f"⏰ <i>Phát hiện: {datetime.now().strftime('%H:%M')}</i>"
                )
                bot.send_message(TELEGRAM_CHAT_ID, msg, parse_mode="HTML")
                
                du_lieu[so_hieu] = {
                    "so_cv": so_hieu,
                    "ngay_den": ngay_den,
                    "trich_yeu": trich_yeu,
                    "han_xu_ly": han_xl
                }
                co_thay_doi = True

        if co_thay_doi:
            luu_ds(du_lieu)
            # Tự động commit file json lên GitHub để lần sau không bị trùng
            os.system('git config user.email "bot@github.com"')
            os.system('git config user.name "Robot Bot"')
            os.system(f'git add {FILE_DA_GUI}')
            os.system('git commit -m "Update data [skip ci]"')
            os.system('git push')

    except Exception as e:
        log.error(f"Lỗi: {e}")
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    chay_robot()
    # Thức đợi anh Hoàn 10 phút để trả lời thống kê/voice-to-text
    log.info("Robot đang đợi lệnh từ anh...")
    start = time.time()
    while time.time() - start < 600:
        try:
            bot.polling(none_stop=True, timeout=10)
        except: time.sleep(5)
