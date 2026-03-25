import time
import os
import json
import logging
import requests
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ============================================================
# 1. CẤU HÌNH — Đọc từ GitHub Secrets
# ============================================================
URL_LOGIN     = "https://hscvkhcn.dienbien.gov.vn/names.nsf?Login"
URL_DANH_SACH = "https://hscvkhcn.dienbien.gov.vn/qlvb/vbden.nsf/default?openform&frm=Private_ChoXL?openForm"

USER_NAME        = os.environ.get("SKHCN_USER", "")
PASS_WORD        = os.environ.get("SKHCN_PASS", "")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

FILE_DA_GUI = "da_gui.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def gui_telegram(msg: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=15)
        return resp.status_code == 200
    except Exception:
        return False


def la_ngay_thang(text: str) -> bool:
    clean_text = text.replace("(", "").replace(")", "").strip()
    return bool(re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', clean_text))


def chay_robot():
    log.info("--- BẮT ĐẦU QUÉT HỆ THỐNG SỞ KH&CN (GIAO DIỆN TINH GỌN) ---")
    driver = None

    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 30)

        # Đăng nhập
        driver.get(URL_LOGIN)
        wait.until(EC.presence_of_element_located((By.NAME, "Username")))
        driver.find_element(By.NAME, "Username").send_keys(USER_NAME)
        driver.find_element(By.NAME, "Password").send_keys(PASS_WORD)
        try:
            driver.find_element(By.XPATH, "//input[@type='submit']").click()
        except Exception:
            driver.execute_script("document.forms[0].submit()")
        time.sleep(15)

        # Vào danh sách
        driver.get(URL_DANH_SACH)
        time.sleep(35)

        driver.switch_to.default_content()
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "Main")))

        wait.until(EC.presence_of_element_located((By.TAG_NAME, "tr")))
        rows = driver.find_elements(By.TAG_NAME, "tr")
        ds_vb_moi = []

        for row in rows:
            tds = row.find_elements(By.TAG_NAME, "td")
            if len(tds) < 5: continue

            # Thu thập toàn bộ chữ có giá trị trong 1 dòng
            o_chu_co_chu = []
            for td in tds:
                txt = td.text.strip()
                if txt and txt.lower() != "trích yếu":
                    o_chu_co_chu.append(txt)

            if len(o_chu_co_chu) < 4: continue

            so_hieu = ""
            ngay_den = ""
            han_xl = "Không có"
            trich_yeu = ""

            # --- Thuật toán bóc tách tinh gọn ---
            for text in o_chu_co_chu:
                # 1. Lấy ngày đến (Dạng ngày đầu tiên xuất hiện đơn lẻ hoặc kèm ngoặc đơn)
                if la_ngay_thang(text) and not ngay_den:
                    ngay_den = text.replace("(", "").replace(")", "").strip()
                    continue

                # 2. Lấy số hiệu (Chứa dấu / và không phải ngày tháng thuần túy)
                if "/" in text and not la_ngay_thang(text) and not so_hieu:
                    so_hieu = text
                    continue

                # 3. Lấy trích yếu (Đoạn chữ dài nhất)
                if len(text) > len(trich_yeu) and len(text) > 25 and not la_ngay_thang(text):
                    trich_yeu = text

            # Gạn lọc hạn xử lý (thường nằm ở cuối hoặc chứa mốc thời gian hạn)
            if len(o_chu_co_chu) > 4:
                cuoi_dong = o_chu_co_chu[-1]
                if la_ngay_thang(cuoi_dong) or "ngày" in cuoi_dong.lower():
                    han_xl = cuoi_dong

            if so_hieu and trich_yeu:
                ds_vb_moi.append(
                    f"🏷️ <b>Số hiệu:</b> {so_hieu}\n"
                    f"📅 <b>Ngày đến:</b> {ngay_den}\n"
                    f"⏳ <b>Hạn xử lý:</b> {han_xl}\n"
                    f"📝 <b>Trích yếu:</b> {trich_yeu}"
                )

        if ds_vb_moi:
            noi_dung = "\n\n➖➖➖➖➖➖➖➖➖➖\n\n".join(ds_vb_moi[:3]) # Hiển thị 3 cái test cho thoáng mắt
            msg = (
                f"🚀 <b>VĂN BẢN ĐẾN SỞ KH&CN (TINH GỌN)</b>\n"
                f"⏰ Quét lúc: {datetime.now().strftime('%H:%M %d/%m/%Y')}\n\n"
                f"{noi_dung}"
            )
            gui_telegram(msg)
            log.info("🔥 Đã đẩy giao diện tinh gọn lên Telegram!")

    except Exception as e:
        log.error(f"❌ Lỗi: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    chay_robot()
