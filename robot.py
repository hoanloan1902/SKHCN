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

# --- CẤU HÌNH ---
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
USER_NAME = os.environ.get("SKHCN_USER", "")
PASS_WORD = os.environ.get("SKHCN_PASS", "")

URL_LOGIN = "https://hscvkhcn.dienbien.gov.vn/names.nsf?Login"
URL_DANH_SACH = "https://hscvkhcn.dienbien.gov.vn/qlvb/vbden.nsf/default?openform&frm=Private_ChoXL?openForm"

bot = telebot.TeleBot(TOKEN)
FILE_DA_GUI = "da_gui.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# --- HÀM CƠ SỞ DỮ LIỆU ---
def tai_ds():
    try:
        with open(FILE_DA_GUI, "r", encoding="utf-8") as f: return set(json.load(f))
    except: return set()

def luu_ds(ds):
    with open(FILE_DA_GUI, "w", encoding="utf-8") as f: json.dump(list(ds), f, ensure_ascii=False)

# --- XỬ LÝ KHI ANH NHẮN TIN (TRỢ LÝ ẢO) ---
@bot.message_handler(func=lambda message: True)
def tra_loi_anh_hoan(message):
    text = message.text.lower() if message.text else ""
    
    # Nếu anh hỏi thống kê (bằng chữ hoặc bằng giọng nói qua bàn phím)
    if any(keyword in text for keyword in ["thống kê", "bao nhiêu", "tình hình"]):
        ds = tai_ds()
        msg = f"📊 <b>BÁO CÁO NHANH</b>\n────────────────\n✅ Đã quét tổng cộng: <b>{len(ds)}</b> văn bản.\n🤖 Trạng thái: <i>Đang trực chiến trên hệ thống Sở!</i>"
        bot.reply_to(message, msg, parse_mode="HTML")
    
    elif "chào" in text:
        bot.reply_to(message, "Chào anh Hoàn! Em đã sẵn sàng. Anh cứ hỏi 'thống kê' nhé!")

# --- LUỒNG ROBOT QUÉT WEB (SELENIUM) ---
def chay_robot_quet():
    while True:
        log.info("--- BẮT ĐẦU QUÉT HỆ THỐNG ---")
        driver = None
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            
            # Đăng nhập
            driver.get(URL_LOGIN)
            driver.find_element(By.NAME, "Username").send_keys(USER_NAME)
            driver.find_element(By.NAME, "Password").send_keys(PASS_WORD)
            driver.execute_script("document.forms[0].submit()")
            time.sleep(10)
            
            # Vào danh sách
            driver.get(URL_DANH_SACH)
            time.sleep(10)
            driver.switch_to.default_content()
            WebDriverWait(driver, 20).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "Main")))
            
            rows = driver.find_elements(By.TAG_NAME, "tr")
            ds_da_gui = tai_ds()
            moi = 0

            for row in rows:
                t = row.text.strip()
                if "/" in t and len(t) > 10:
                    so_hieu = t.split()[0] # Lấy số hiệu làm ID
                    if so_hieu not in ds_da_gui:
                        bot.send_message(CHAT_ID, f"🚀 <b>VĂN BẢN MỚI</b>\n📄 Số: <code>{so_hieu}</code>\n📝 {t[:150]}...", parse_mode="HTML")
                        ds_da_gui.add(so_hieu)
                        moi += 1
            
            if moi > 0: luu_ds(ds_da_gui)
            
        except Exception as e:
            log.error(f"Lỗi quét: {e}")
        finally:
            if driver: driver.quit()
        
        log.info("Nghỉ 15 phút...")
        time.sleep(900)

# --- CHẠY SONG SONG ---
if __name__ == "__main__":
    # Luồng 1: Chạy Robot quét web ngầm
    t_robot = Thread(target=chay_robot_quet)
    t_robot.daemon = True
    t_robot.start()
    
    # Luồng 2: Chạy Bot lắng nghe tin nhắn từ anh
    log.info("Bot bắt đầu lắng nghe tin nhắn...")
    bot.polling(none_stop=True)
