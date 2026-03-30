import time
import os
import json
import logging
import requests
import re
from datetime import datetime
import telebot # Thư viện pyTelegramBotAPI
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CẤU HÌNH ---
USER_NAME = os.environ.get("SKHCN_USER", "")
PASS_WORD = os.environ.get("SKHCN_PASS", "")
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
URL_LOGIN = "https://hscvkhcn.dienbien.gov.vn/names.nsf?Login"
URL_DANH_SACH = "https://hscvkhcn.dienbien.gov.vn/qlvb/vbden.nsf/default?openform&frm=Private_ChoXL?openForm"

bot = telebot.TeleBot(TOKEN)
FILE_DA_GUI = "da_gui.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

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

def chay_robot():
    log.info("=== QUÉT HỆ THỐNG V3.2 (FIX NHẢY CỘT) ===")
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
        try: WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "Main")))
        except: pass

        rows = driver.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            cells = [c.text.strip() for c in row.find_elements(By.TAG_NAME, "td")]
            if len(cells) < 4: continue
            
            # --- LOGIC NHẬN DIỆN CỘT THÔNG MINH ---
            so_hieu = ""
            ngay_den = ""
            trich_yeu = ""
            han_xl = "Không có hạn"

            for cell in cells:
                # Nếu ô chứa dấu / và không phải ngày tháng -> Số hiệu
                if "/" in cell and not re.search(r'\d{2}/\d{2}/\d{4}', cell):
                    so_hieu = cell
                # Nếu ô chứa ngày tháng định dạng dd/mm/yyyy -> Ngày đến
                elif re.search(r'\d{2}/\d{2}/\d{4}', cell):
                    if not ngay_den: ngay_den = cell
                    else: han_xl = cell # Ngày thứ 2 tìm thấy thường là hạn xử lý
                # Ô dài nhất thường là Trích yếu
                elif len(cell) > len(trich_yeu):
                    trich_yeu = cell

            if so_hieu and so_hieu not in du_lieu:
                msg = (
                    f"🚀 <b>CÓ VĂN BẢN MỚI</b>\n"
                    f"────────────────────\n"
                    f"📌 <b>Số CV:</b> <code>{so_hieu}</code>\n"
                    f"📅 <b>Ngày đến:</b> {ngay_den}\n"
                    f"📝 <b>Trích yếu:</b> {trich_yeu[:300]}\n"
                    f"⏳ <b>Hạn xử lý:</b> {han_xl}\n"
                    f"⏰ <i>Cập nhật: {datetime.now().strftime('%H:%M')}</i>"
                )
                bot.send_message(CHAT_ID, msg, parse_mode="HTML")
                du_lieu[so_hieu] = {"so_cv": so_hieu, "ngay_den": ngay_den, "trich_yeu": trich_yeu, "han_xu_ly": han_xl}
                co_thay_doi = True

        if co_thay_doi:
            luu_ds(du_lieu)
            os.system('git config user.email "bot@github.com"')
            os.system('git config user.name "Robot Bot"')
            os.system(f'git add {FILE_DA_GUI}')
            os.system('git commit -m "Update data [skip ci]"')
            os.system('git push')

    except Exception as e: log.error(f"Lỗi: {e}")
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    chay_robot()
