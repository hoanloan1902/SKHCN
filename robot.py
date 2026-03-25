import time
import os
import json
import logging
import requests
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ============================================================
# CẤU HÌNH HỆ THỐNG
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


def tai_ds_da_gui() -> set:
    try:
        with open(FILE_DA_GUI, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def luu_ds_da_gui(ds: set):
    with open(FILE_DA_GUI, "w", encoding="utf-8") as f:
        json.dump(list(ds), f, ensure_ascii=False, indent=2)


def gui_telegram(msg: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=15)
        return resp.status_code == 200
    except Exception:
        return False


def la_ngay_thang(txt: str) -> bool:
    t = txt.replace("(", "").replace(")", "").strip()
    return bool(re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', t))


def chuyen_chuoi_thanh_ngay(txt_ngay: str):
    try:
        clean_txt = txt_ngay.replace("(", "").replace(")", "").strip()
        return datetime.strptime(clean_txt, "%d/%m/%Y")
    except ValueError:
        return None


def chay_robot():
    log.info("--- BẮT ĐẦU QUÉT HỆ THỐNG SỞ KH&CN V2.5 (BẤM CHI TIẾT + F5 TẢI LẠI TRANG) ---")
    driver = None
    ds_da_gui = tai_ds_da_gui()
    ngay_hom_nay = datetime.now() + timedelta(hours=7)

    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 30)

        # 🚀 Bước 1: Đăng nhập
        driver.get(URL_LOGIN)
        wait.until(EC.presence_of_element_located((By.NAME, "Username")))
        driver.find_element(By.NAME, "Username").send_keys(USER_NAME)
        driver.find_element(By.NAME, "Password").send_keys(PASS_WORD)
        try:
            driver.find_element(By.XPATH, "//input[@type='submit']").click()
        except Exception:
            driver.execute_script("document.forms[0].submit()")
        time.sleep(15)

        # CHỈ LẤY TỐI ĐA 2 VĂN BẢN MỚI NHẤT MỖI LẦN CHẠY ĐỂ TRÁNH QUÁ 5 PHÚT TIMEOUT
        for lan_quet in range(2): 
            # 🚀 Bước 2: Vào lại danh sách chính (Mỗi vòng lặp tải lại trang cho sạch Iframe)
            driver.get(URL_DANH_SACH)
            time.sleep(20)

            driver.switch_to.default_content()
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "Main")))

            wait.until(EC.presence_of_element_located((By.TAG_NAME, "tr")))
            rows = driver.find_elements(By.TAG_NAME, "tr")

            tim_thay_vb_moi = False
            
            for row in rows:
                txt_row = row.text.strip()
                if not txt_row or "số ký hiệu" in txt_row.lower() or "/" not in txt_row:
                    continue

                parts = txt_row.split()
                if len(parts) < 4: continue

                so_hieu = ""
                ngay_den = ""
                trich_yeu = ""

                if len(parts) > 1 and la_ngay_thang(parts[1]):
                    ngay_den = parts[1]

                for i, p in enumerate(parts):
                    if "/" in p and not la_ngay_thang(p) and not so_hieu:
                        so_hieu = p
                        if (i + 2) < len(parts):
                            trich_yeu = " ".join(parts[i+2:])
                        break

                # 🛑 Chống bắn trùng
                if so_hieu in ds_da_gui:
                    continue

                tds = row.find_elements(By.TAG_NAME, "td")
                if tds:
                    tim_thay_vb_moi = True
                    o_bam = tds[min(len(tds)-1, 3)] # Lấy ô Trích yếu để bấm
                    
                    # 👉 Bấm mở xem chi tiết văn bản
                    o_bam.click()
                    time.sleep(15)

                    # Bới chữ lấy hạn xử lý
                    page_text = driver.find_element(By.TAG_NAME, "body").text
                    han_xl_tim_thay = "Không rõ"
                    khoang_cach_ngay = 999

                    tat_ca_ngay = re.findall(r'\b\d{1,2}/\d{1,2}/\d{4}\b', page_text)
                    for ngay_mau in tat_ca_ngay:
                        doi_tuong_ngay = chuyen_chuoi_thanh_ngay(ngay_mau)
                        if doi_tuong_ngay:
                            date_mau = doi_tuong_ngay.date()
                            date_nay = ngay_hom_nay.date()
                            
                            if date_mau >= date_nay:
                                kc = (date_mau - date_nay).days
                                if kc < khoang_cach_ngay:
                                    khoang_cach_ngay = kc
                                    han_xl_tim_thay = ngay_mau

                    # Soạn tin đẩy lên Telegram
                    khung_chu_telegram = (
                        f"🏷️ <b>Số hiệu:</b> {so_hieu}\n"
                        f"📅 <b>Ngày đến:</b> {ngay_den}\n"
                        f"📝 <b>Trích yếu:</b> {trich_yeu[:200]}...\n"
                        f"⏳ <b>Hạn xử lý:</b> {han_xl_tim_thay}"
                    )

                    thong_bao_chot = f"🚀 <b>QUÉT VĂN BẢN ĐẾN SỞ KH&CN (CHI TIẾT)</b>\n⏰ {ngay_hom_nay.strftime('%H:%M %d/%m/%Y')}\n\n"

                    if 0 <= khoang_cach_ngay <= 2:
                        thong_bao_chot += f"🚨 <b>DANH SÁCH VĂN BẢN KHẨN (HẠN ≤ 2 NGÀY)</b> 🚨\n\n🔴 <b>[GẤP HẠN CÒN {khoang_cach_ngay} NGÀY]</b>\n{khung_chu_telegram}"
                    else:
                        thong_bao_chot += f"📋 <b>DANH SÁCH VĂN BẢN THƯỜNG</b>\n\n🔹 <b>[Bình thường]</b>\n{khung_chu_telegram}"

                    gui_telegram(thong_bao_chot)
                    ds_da_gui.add(so_hieu)
                    luu_ds_da_gui(ds_da_gui)
                    break # Văng ra ngoài vòng lặp hàng để F5 tải lại trang danh sách mới

            if not tim_thay_vb_moi:
                log.info("✅ Không tìm thấy văn bản mới ở vòng quét này.")
                break # Không còn văn bản mới thì dừng luôn không quét vòng thứ 2 nữa

    except Exception as e:
        log.error(f"❌ Lỗi: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    chay_robot()
