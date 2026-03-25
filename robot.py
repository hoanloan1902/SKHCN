import time
import os
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

# Kiểm tra ngày tháng năm dd/mm/yyyy
def la_ngay_thang(txt: str) -> bool:
    t = txt.replace("(", "").replace(")", "").strip()
    return bool(re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', t))


def chay_robot():
    log.info("--- BẮT ĐẦU QUÉT HỆ THỐNG SỞ KH&CN (PHÂN TÁCH CHUỖI CHUẨN) ---")
    driver = None

    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 30)

        driver.get(URL_LOGIN)
        wait.until(EC.presence_of_element_located((By.NAME, "Username")))
        driver.find_element(By.NAME, "Username").send_keys(USER_NAME)
        driver.find_element(By.NAME, "Password").send_keys(PASS_WORD)
        try:
            driver.find_element(By.XPATH, "//input[@type='submit']").click()
        except Exception:
            driver.execute_script("document.forms[0].submit()")
        time.sleep(15)

        driver.get(URL_DANH_SACH)
        time.sleep(35)

        driver.switch_to.default_content()
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "Main")))

        wait.until(EC.presence_of_element_located((By.TAG_NAME, "tr")))
        rows = driver.find_elements(By.TAG_NAME, "tr")
        ds_vb_moi = []

        for row in rows:
            txt_row = row.text.strip()
            if not txt_row or "số ký hiệu" in txt_row.lower() or "/" not in txt_row:
                continue

            # Cắt nhỏ dòng chữ thành các từ riêng biệt
            parts = txt_row.split()
            if len(parts) < 6: continue

            so_hieu = ""
            ngay_den = ""
            trich_yeu = ""
            han_xl = "Không có"

            # 🔍 Thuật toán bóc tách theo vị trí dòng của Lotus:
            # - Phần tử 0: Số đến nội bộ
            # - Phần tử 1: Ngày đến (dd/mm/yyyy)
            # - Phần tử 2: (Ngày chuyển) -> Bỏ qua

            if len(parts) > 1 and la_ngay_thang(parts[1]):
                ngay_den = parts[1]

            # Quét tìm Số hiệu và Trích yếu thực sự
            for i in range(len(parts)):
                p = parts[i]
                # Nếu từ có chứa '/' và ko phải ngày tháng đơn thuần -> đích thị là Số ký hiệu văn bản!
                if "/" in p and not la_ngay_thang(p) and not so_hieu:
                    so_hieu = p
                    
                    # 💥 TRÍCH YẾU sẽ bắt đầu ngay sau Cơ quan ban hành (Cơ quan ban hành nằm sau Số hiệu)
                    # Chúng ta gom tất cả các từ từ vị trí Số hiệu + 3 từ trở đi (bỏ qua cơ quan ban hành ngắn như UBND tỉnh...)
                    start_trich_yeu = i + 3 if "ubnd" in parts[i+1].lower() or "sở" in parts[i+1].lower() else i + 2
                    
                    if start_trich_yeu < len(parts):
                        doan_duoi = " ".join(parts[start_trich_yeu:])
                        
                        # Tách lấy hạn xử lý nếu có mốc ngày ở cuối dòng
                        if la_ngay_thang(parts[-1]):
                            han_xl = parts[-1]
                            trich_yeu = " ".join(parts[start_trich_yeu:-1])
                        else:
                            trich_yeu = doan_duoi
                    break

            if so_hieu and trich_yeu:
                ds_vb_moi.append(
                    f"🏷️ <b>Số hiệu:</b> {so_hieu}\n"
                    f"📅 <b>Ngày đến:</b> {ngay_den}\n"
                    f"⏳ <b>Hạn xử lý:</b> {han_xl}\n"
                    f"📝 <b>Trích yếu:</b> {trich_yeu}"
                )

        if ds_vb_moi:
            # Gửi 3 cái test cho thoáng mắt anh Hoàn nhé!
            noi_dung = "\n\n➖➖➖➖➖➖➖➖➖➖\n\n".join(ds_vb_moi[:3])
            msg = (
                f"🚀 <b>VĂN BẢN ĐẾN SỞ KH&CN (CẮT CHUỖI CHUẨN)</b>\n"
                f"⏰ Quét lúc: {datetime.now().strftime('%H:%M %d/%m/%Y')}\n\n"
                f"{noi_dung}"
            )
            gui_telegram(msg)
            log.info("🔥 Đã bốc tách cắt chuỗi thành công!")

    except Exception as e:
        log.error(f"❌ Lỗi: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    chay_robot()
