import time
import os
import json
import logging
import requests
import re
import telebot
from datetime import datetime, timedelta
from threading import Thread
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ============================================================
# CẤU HÌNH HỆ THỐNG (Lấy từ Environment Variables trên Render)
# ============================================================
URL_LOGIN      = "https://hscvkhcn.dienbien.gov.vn/names.nsf?Login"
URL_DANH_SACH  = "https://hscvkhcn.dienbien.gov.vn/qlvb/vbden.nsf/default?openform&frm=Private_ChoXL?openForm"

USER_NAME       = os.environ.get("SKHCN_USER", "")
PASS_WORD       = os.environ.get("SKHCN_PASS", "")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Khởi tạo Bot Telegram
bot = telebot.TeleBot(TELEGRAM_TOKEN)
FILE_DA_GUI = "da_gui.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# --- HÀM QUẢN LÝ DỮ LIỆU ---
def tai_ds_da_gui():
    try:
        if os.path.exists(FILE_DA_GUI):
            with open(FILE_DA_GUI, "r", encoding="utf-8") as f:
                return set(json.load(f))
    except: pass
    return set()

def luu_ds_da_gui(ds):
    with open(FILE_DA_GUI, "w", encoding="utf-8") as f:
        json.dump(list(ds), f, ensure_ascii=False, indent=2)

def gui_telegram(msg):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, msg, parse_mode="HTML")
        return True
    except: return False

# --- HÀM THỐNG KÊ (DÀNH CHO TRỢ LÝ ẢO) ---
def thong_ke_nhanh():
    ds = tai_ds_da_gui()
    tong = len(ds)
    msg = (
        f"📊 <b>BÁO CÁO THỐNG KÊ</b>\n"
        f"────────────────\n"
        f"✅ Tổng văn bản đã quét: <b>{tong}</b>\n"
        f"⏰ Cập nhật lúc: {datetime.now().strftime('%H:%M:%S')}\n"
        f"🤖 Trạng thái: <i>Đang trực chiến...</i>"
    )
    return msg

# --- XỬ LÝ LỆNH TỪ ANH HOÀN (VOICE-TO-TEXT HOẶC CHỮ) ---
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    input_text = message.text.lower() if message.text else ""
    
    # Logic phản hồi thông minh
    if any(word in input_text for word in ["thống kê", "bao nhiêu", "tình hình"]):
        bot.reply_to(message, thong_ke_nhanh(), parse_mode="HTML")
    elif "chào" in input_text or "start" in input_text:
        bot.reply_to(message, "Chào anh Hoàn! Em là Trợ lý V3.0. Anh có thể hỏi 'thống kê' để em báo cáo nhé!")

# --- HÀM QUÉT ROBOT (SELENIUM) ---
def chay_robot():
    log.info("--- BẮT ĐẦU QUÉT HỆ THỐNG V3.0 ---")
    driver = None
    ds_da_gui = tai_ds_da_gui()
    
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 20)

        # Đăng nhập
        driver.get(URL_LOGIN)
        wait.until(EC.presence_of_element_located((By.NAME, "Username"))).send_keys(USER_NAME)
        driver.find_element(By.NAME, "Password").send_keys(PASS_WORD)
        driver.execute_script("document.forms[0].submit()")
        time.sleep(10)

        # Vào danh sách văn bản đến
        driver.get(URL_DANH_SACH)
        time.sleep(10)
        driver.switch_to.default_content()
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "Main")))

        rows = driver.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            txt = row.text.strip()
            if not txt or "/" not in txt: continue
            
            # Logic tách số hiệu đơn giản
            parts = txt.split()
            so_hieu = next((p for p in parts if "/" in p and len(p) > 5), None)
            
            if so_hieu and so_hieu not in ds_da_gui:
                msg = f"🚀 <b>CÓ VĂN BẢN MỚI</b>\n📄 Số hiệu: <code>{so_hieu}</code>\n📝 Nội dung: {txt[:100]}..."
                if gui_telegram(msg):
                    ds_da_gui.add(so_hieu)
                    luu_ds_da_gui(ds_da_gui)
                    
    except Exception as e:
        log.error(f"Lỗi Robot: {e}")
    finally:
        if driver: driver.quit()

# --- CHẠY SONG SONG 2 LUỒNG ---
def robot_loop():
    while True:
        chay_robot()
        time.sleep(900) # Quét mỗi 15 phút

if __name__ == "__main__":
    # Luồng 1: Robot quét tự động
    t1 = Thread(target=robot_loop)
    t1.daemon = True
    t1.start()
    
    # Luồng 2: Bot Telegram lắng nghe tin nhắn
    log.info("Bot đang lắng nghe...")
    bot.polling(none_stop=True)
