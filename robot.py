import time
import os
import json
import logging
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ============================================================
# CẤU HÌNH
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


# ============================================================
# TELEGRAM — gửi tin nhắn đơn giản qua requests, không cần thư viện
# ============================================================
def gui_telegram(msg: str):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
        r.raise_for_status()
        log.info("Đã gửi Telegram thành công.")
    except Exception as e:
        log.error(f"Lỗi gửi Telegram: {e}")


# ============================================================
# QUẢN LÝ TRẠNG THÁI (file JSON)
# ============================================================
def tai_ds_da_gui() -> set:
    try:
        if os.path.exists(FILE_DA_GUI):
            with open(FILE_DA_GUI, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
    except Exception as e:
        log.warning(f"Không đọc được {FILE_DA_GUI}: {e}")
    return set()


def luu_ds_da_gui(ds: set):
    try:
        with open(FILE_DA_GUI, "w", encoding="utf-8") as f:
            json.dump(sorted(list(ds)), f, ensure_ascii=False, indent=2)
        log.info(f"Đã lưu {len(ds)} mục vào {FILE_DA_GUI}")
    except Exception as e:
        log.error(f"Lỗi lưu {FILE_DA_GUI}: {e}")


# ============================================================
# COMMIT TRẠNG THÁI VỀ REPO
# ============================================================
def commit_trang_thai():
    log.info("Đang commit da_gui.json lên repo...")
    os.system('git config user.email "github-actions[bot]@users.noreply.github.com"')
    os.system('git config user.name "github-actions[bot]"')
    os.system(f'git add {FILE_DA_GUI}')
    # Nếu không có thay đổi thì lệnh commit sẽ exit code != 0 nhưng không sao
    ret = os.system('git commit -m "cap nhat trang thai van ban [skip ci]"')
    if ret == 0:
        os.system("git push")
        log.info("Commit và push thành công.")
    else:
        log.info("Không có thay đổi cần commit.")


# ============================================================
# ROBOT SELENIUM
# ============================================================
def chay_robot():
    log.info("====== BẮT ĐẦU QUÉT HỆ THỐNG SỞ KH&CN ======")
    driver = None
    ds_da_gui = tai_ds_da_gui()
    co_thay_doi = False

    try:
        # --- Khởi động Chrome headless ---
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,800")

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        wait = WebDriverWait(driver, 30)

        # --- Bước 1: Đăng nhập ---
        log.info("Đang đăng nhập...")
        driver.get(URL_LOGIN)
        wait.until(EC.presence_of_element_located((By.NAME, "Username"))).send_keys(USER_NAME)
        driver.find_element(By.NAME, "Password").send_keys(PASS_WORD)
        driver.execute_script("document.forms[0].submit()")

        # Chờ trang sau đăng nhập load xong (tìm phần tử quen thuộc thay vì sleep cứng)
        time.sleep(5)  # buffer nhỏ cho redirect
        wait.until(lambda d: d.current_url != URL_LOGIN)
        log.info(f"Đăng nhập xong. URL hiện tại: {driver.current_url}")

        # --- Bước 2: Vào trang danh sách ---
        log.info("Đang vào trang danh sách văn bản đến...")
        driver.get(URL_DANH_SACH)
        time.sleep(5)

        # Chuyển vào frame Main (nếu trang dùng frameset)
        driver.switch_to.default_content()
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "Main")))
            log.info("Đã switch vào frame Main.")
        except Exception:
            log.info("Không tìm thấy frame Main, tiếp tục với trang chính.")

        # Chờ bảng hiển thị
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))

        # --- Bước 3: Đọc danh sách văn bản ---
        rows = driver.find_elements(By.TAG_NAME, "tr")
        log.info(f"Tìm thấy {len(rows)} hàng trong bảng.")

        # --- DEBUG: In cấu trúc bảng để xác định đúng cột ---
        DEBUG_COT = True
        tat_ca_rows = driver.find_elements(By.TAG_NAME, "tr")
        log.info(f"Tổng số hàng tìm được: {len(tat_ca_rows)}")

        rows_hop_le = []
        for i, row in enumerate(tat_ca_rows):
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 4:
                noi_dung = [c.text.strip() for c in cells]
                # Lọc bỏ hàng phân trang và hàng rác
                full_text = " ".join(noi_dung)
                if any(k in full_text for k in ["Trang 1", "Có tổng số", "tổng số"]):
                    continue
                # Bỏ hàng toàn rỗng
                if not any(noi_dung):
                    continue
                rows_hop_le.append((i, cells, noi_dung))
                if DEBUG_COT and i < 8:
                    log.info(f"[DEBUG hàng {i}] " + " | ".join(
                        f"[{j}]{v[:25]}" for j, v in enumerate(noi_dung)
                    ))

        log.info(f"Số hàng hợp lệ (sau lọc): {len(rows_hop_le)}")

        # ----------------------------------------------------------------
        # CHỈ SỐ CỘT — xem log DEBUG để xác nhận, điều chỉnh nếu cần
        # Dự đoán ban đầu dựa trên hệ thống Lotus Notes điển hình:
        #   [0] STT
        #   [1] Số công văn
        #   [2] Ngày đến
        #   [3] Trích yếu
        #   [4] Hạn xử lý
        # ----------------------------------------------------------------
        COT_SO_CV  = 1
        COT_NGAY   = 2
        COT_TRICH  = 3
        COT_HAN    = 4

        so_moi = 0
        for (i, cells, noi_dung) in rows_hop_le:
            if len(noi_dung) <= COT_HAN:
                continue

            so_cv     = noi_dung[COT_SO_CV]
            ngay_den  = noi_dung[COT_NGAY]
            trich_yeu = noi_dung[COT_TRICH]
            han_xu_ly = noi_dung[COT_HAN]

            # Bỏ tiêu đề cột
            if not so_cv or so_cv.lower() in ("số công văn", "số cv", "số hiệu", "stt", ""):
                continue
            # Bỏ hàng không có dấu hiệu số công văn thực
            if len(so_cv) < 3:
                continue

            if so_cv not in ds_da_gui:
                log.info(f"Văn bản mới: [{so_cv}] | Ngày: {ngay_den} | Hạn: {han_xu_ly}")
                tin = (
                    f"📄 <b>VĂN BẢN MỚI - SỞ KH&amp;CN ĐIỆN BIÊN</b>\n"
                    f"────────────────────\n"
                    f"📌 <b>Số công văn:</b> <code>{so_cv}</code>\n"
                    f"📝 <b>Trích yếu:</b> {trich_yeu[:300]}\n"
                    f"📅 <b>Ngày đến:</b> {ngay_den}\n"
                    f"⏳ <b>Hạn xử lý:</b> {han_xu_ly}\n"
                    f"⏰ Phát hiện: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                )
                gui_telegram(tin)
                ds_da_gui.add(so_cv)
                co_thay_doi = True
                so_moi += 1

        log.info(f"Quét xong. Văn bản mới: {so_moi}")

        if so_moi == 0:
            log.info("Không có văn bản mới.")

    except Exception as e:
        log.error(f"Lỗi trong quá trình chạy robot: {e}", exc_info=True)
        gui_telegram(f"⚠️ <b>Robot gặp lỗi</b>\n{str(e)[:300]}")
    finally:
        if driver:
            driver.quit()

    # --- Lưu và commit nếu có thay đổi ---
    if co_thay_doi:
        luu_ds_da_gui(ds_da_gui)
        commit_trang_thai()
    else:
        log.info("Không có thay đổi, bỏ qua commit.")


# ============================================================
# CHƯƠNG TRÌNH CHÍNH
# ============================================================
if __name__ == "__main__":
    chay_robot()
