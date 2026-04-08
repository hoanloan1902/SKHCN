#!/usr/bin/env python3
"""
Bot quét văn bản đến từ HSCV - Dùng API Domino ReadViewEntries
"""

import os
import json
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import urllib3

import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import telebot

# ==================== CẤU HÌNH ====================
# Đọc từ environment variables
USER_NAME = os.environ.get("SKHCN_USER")
PASS_WORD = os.environ.get("SKHCN_PASS")
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_JSON = os.environ.get("GSPREAD_SERVICE_ACCOUNT")
CHAT_ID = os.environ.get("CHAT_ID")
SHEET_NAME = "DANH_SACH_VAN_BAN"
DA_GUI_FILE = "da_gui.json"

# URL hệ thống (có thể cần chỉnh theo thực tế)
BASE_URL = "https://hscvkhcn.dienbien.gov.vn"
DB_PATH = "/qlvb/vbden.nsf"
VIEW_NAME = "Private_ChoXL_KoHan"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== ĐỌC/GHI JSON ====================
def load_da_gui() -> set:
    """Đọc danh sách văn bản đã gửi từ file JSON"""
    if os.path.exists(DA_GUI_FILE):
        try:
            with open(DA_GUI_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('da_gui', []))
        except Exception as e:
            print(f"⚠️ Lỗi đọc da_gui.json: {e}")
    return set()

def save_da_gui(da_gui: set):
    """Lưu danh sách văn bản đã gửi vào file JSON"""
    try:
        with open(DA_GUI_FILE, 'w', encoding='utf-8') as f:
            json.dump({'da_gui': list(da_gui), 'last_update': datetime.now().isoformat()}, 
                     f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Lỗi ghi da_gui.json: {e}")

# ==================== KẾT NỐI GOOGLE SHEETS ====================
def ket_noi_sheets():
    """Kết nối Google Sheets (dùng làm backup lưu trữ)"""
    if not GOOGLE_JSON:
        print("⚠️ Không có GOOGLE_JSON, bỏ qua Sheets")
        return None
    try:
        scope = ["https://spreadsheets.google.com/feeds",
                 "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(GOOGLE_JSON), scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME)
    except Exception as e:
        print(f"❌ Lỗi kết nối Sheets: {e}")
        return None

# ==================== ĐĂNG NHẬP DOMINO ====================
def domino_login(session: requests.Session) -> bool:
    """Đăng nhập vào hệ thống Domino"""
    login_url = f"{BASE_URL}/names.nsf?Login"
    
    payload = {
        'Username': USER_NAME,
        'Password': PASS_WORD,
        'RedirectTo': f'{DB_PATH}/{VIEW_NAME}?OpenForm'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        response = session.post(login_url, data=payload, 
                                headers=headers, verify=False, timeout=30)
        
        # Kiểm tra đăng nhập thành công
        if response.status_code == 200 and "Login" not in response.text:
            print("✅ Đăng nhập Domino thành công")
            return True
        else:
            print(f"❌ Đăng nhập thất bại: status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi đăng nhập: {e}")
        return False

# ==================== QUA HTML (FALLBACK KHI API LỖI) ====================
def parse_html_table(html_content: str) -> List[Dict]:
    """Parse HTML table để lấy danh sách văn bản (fallback)"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    ket_qua = []
    for row in soup.find_all('tr'):
        tds = row.find_all('td')
        if len(tds) < 5:
            continue
        
        cols = [re.sub(r'\s+', ' ', td.get_text()).strip() for td in tds]
        
        for i, c in enumerate(cols):
            if re.match(r'^\d{2}/\d{2}/\d{4}$', c):
                so_hieu = cols[i+1] if i+1 < len(cols) else ""
                co_quan = cols[i+2] if i+2 < len(cols) else ""
                trich_yeu = cols[i+3] if i+3 < len(cols) else ""
                
                if so_hieu and ("/" in so_hieu or "-" in so_hieu):
                    ket_qua.append({
                        'so_hieu': so_hieu,
                        'ngay': c,
                        'trich_yeu': trich_yeu[:200],
                        'co_quan': co_quan
                    })
                break
    
    return ket_qua

def quet_qua_html(session: requests.Session) -> List[Dict]:
    """Quét qua HTML (fallback khi API không hoạt động)"""
    url_target = f"{BASE_URL}{DB_PATH}/{VIEW_NAME}?OpenForm"
    
    try:
        response = session.get(url_target, verify=False, timeout=30)
        response.encoding = response.apparent_encoding
        return parse_html_table(response.text)
    except Exception as e:
        print(f"❌ Lỗi quét HTML: {e}")
        return []

# ==================== QUA API READVIEWENTRIES ====================
def lay_danh_sach_qua_api(session: requests.Session, 
                           tu_ngay: str = None, 
                           den_ngay: str = None) -> List[Dict]:
    """
    Lấy danh sách qua API ReadViewEntries
    tu_ngay, den_ngay format: YYYYMMDD
    """
    api_url = f"{BASE_URL}{DB_PATH}/{VIEW_NAME}?ReadViewEntries"
    
    params = {
        'Count': '100',  # Giới hạn số lượng
    }
    
    # Thêm filter theo ngày nếu có
    if tu_ngay and den_ngay:
        params['StartKey'] = f"{tu_ngay}T000000Z"
        params['UntilKey'] = f"{den_ngay}T235959Z"
        params['KeyType'] = 'time'
    
    try:
        response = session.get(api_url, params=params, verify=False, timeout=30)
        
        if response.status_code != 200:
            print(f"⚠️ API trả về status {response.status_code}, fallback sang HTML")
            return None
        
        # Thử parse XML
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(response.content)
            danh_sach = []
            
            for entry in root.findall('.//viewentry'):
                so_hieu = ""
                ngay = ""
                co_quan = ""
                trich_yeu = ""
                
                for i, entrydata in enumerate(entry.findall('.//entrydata')):
                    value = entrydata.text or ""
                    if i == 0:
                        so_hieu = value.strip()
                    elif i == 1:
                        ngay = value.strip()
                    elif i == 2:
                        co_quan = value.strip()
                    elif i == 3:
                        trich_yeu = value.strip()[:200]
                
                if so_hieu:
                    danh_sach.append({
                        'so_hieu': so_hieu,
                        'ngay': ngay,
                        'trich_yeu': trich_yeu,
                        'co_quan': co_quan
                    })
            
            print(f"📊 API trả về {len(danh_sach)} văn bản")
            return danh_sach
            
        except ET.ParseError:
            print("⚠️ Không parse được XML API, fallback sang HTML")
            return None
            
    except Exception as e:
        print(f"⚠️ Lỗi API: {e}, fallback sang HTML")
        return None

# ==================== LẤY DANH SÁCH CHÍNH ====================
def lay_danh_sach_van_ban(session: requests.Session) -> List[Dict]:
    """Lấy danh sách văn bản (ưu tiên API, fallback HTML)"""
    hom_nay = datetime.now()
    tu_ngay = (hom_nay - timedelta(days=7)).strftime("%Y%m%d")
    den_ngay = hom_nay.strftime("%Y%m%d")
    
    # Thử API trước
    danh_sach = lay_danh_sach_qua_api(session, tu_ngay, den_ngay)
    
    # Fallback sang HTML nếu API lỗi
    if danh_sach is None:
        print("🔄 Chuyển sang chế độ quét HTML...")
        danh_sach = quet_qua_html(session)
    
    return danh_sach or []

# ==================== GỬI THÔNG BÁO ====================
def gui_thong_bao(van_ban_moi: List[Dict]):
    """Gửi thông báo Telegram"""
    if not van_ban_moi:
        return
    
    bot = telebot.TeleBot(TOKEN)
    
    # Nhóm tin nhắn để tránh spam
    if len(van_ban_moi) == 1:
        vb = van_ban_moi[0]
        msg = (f"🔔 *VĂN BẢN ĐẾN MỚI*\n\n"
               f"📌 *Số hiệu:* `{vb['so_hieu']}`\n"
               f"📅 *Ngày:* {vb['ngay']}\n"
               f"🏢 *Cơ quan gửi:* {vb['co_quan']}\n"
               f"📝 *Trích yếu:* {vb['trich_yeu'][:150]}...")
    else:
        msg = f"🔔 *CÓ {len(van_ban_moi)} VĂN BẢN ĐẾN MỚI*\n\n"
        for i, vb in enumerate(van_ban_moi[:5], 1):
            msg += f"{i}. `{vb['so_hieu']}` - {vb['co_quan']}\n"
            msg += f"   📝 {vb['trich_yeu'][:80]}...\n\n"
        if len(van_ban_moi) > 5:
            msg += f"... và {len(van_ban_moi) - 5} văn bản khác"
    
    try:
        bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
        print(f"✅ Đã gửi {len(van_ban_moi)} thông báo")
    except Exception as e:
        print(f"❌ Lỗi gửi Telegram: {e}")

# ==================== LUU VAO GOOGLE SHEETS ====================
def luu_vao_sheets(sheet, van_ban_moi: List[Dict]):
    """Lưu văn bản mới vào Google Sheets"""
    if not sheet:
        return
    
    for vb in van_ban_moi:
        try:
            row = [vb['so_hieu'], vb['ngay'], vb['trich_yeu'], vb['co_quan']]
            sheet.insert_row(row, 2)
            time.sleep(0.5)
        except Exception as e:
            print(f"⚠️ Không lưu được {vb['so_hieu']} vào Sheets: {e}")

# ==================== MAIN ====================
def main():
    print(f"🚀 Bắt đầu quét: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Kiểm tra biến môi trường
    if not USER_NAME or not PASS_WORD:
        print("❌ Thiếu SKHCN_USER hoặc SKHCN_PASS")
        return
    if not TOKEN or not CHAT_ID:
        print("❌ Thiếu TELEGRAM_TOKEN hoặc CHAT_ID")
        return
    
    # Đọc danh sách đã gửi
    da_gui = load_da_gui()
    print(f"📁 Đã gửi trước đó: {len(da_gui)} văn bản")
    
    # Đăng nhập
    session = requests.Session()
    if not domino_login(session):
        print("❌ Đăng nhập thất bại")
        return
    
    # Lấy danh sách văn bản
    danh_sach = lay_danh_sach_van_ban(session)
    if not danh_sach:
        print("📭 Không lấy được dữ liệu")
        return
    
    print(f"📊 Tổng số văn bản trong view: {len(danh_sach)}")
    
    # Tìm văn bản mới (chưa gửi)
    so_hieu_da_co = {vb['so_hieu'] for vb in danh_sach if vb['so_hieu'] in da_gui}
    van_ban_moi = [vb for vb in danh_sach if vb['so_hieu'] not in da_gui]
    
    if not van_ban_moi:
        print("✅ Không có văn bản mới")
        # Vẫn cập nhật thời gian chạy cuối
        save_da_gui(da_gui)
        return
    
    print(f"🆕 Phát hiện {len(van_ban_moi)} văn bản mới")
    
    # Cập nhật danh sách đã gửi
    for vb in van_ban_moi:
        da_gui.add(vb['so_hieu'])
    
    # Lưu vào JSON
    save_da_gui(da_gui)
    
    # Lưu vào Google Sheets (nếu có)
    sheet = ket_noi_sheets()
    luu_vao_sheets(sheet, van_ban_moi)
    
    # Gửi thông báo Telegram
    gui_thong_bao(van_ban_moi)
    
    print(f"✅ Hoàn thành! Đã thêm {len(van_ban_moi)} văn bản mới")

if __name__ == "__main__":
    main()
