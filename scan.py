#!/usr/bin/env python3
"""
Bot quét văn bản đến từ HSCV - Hỗ trợ hạn xử lý và lưu đầy đủ thông tin
"""

import os
import json
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import urllib3

import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup
import telebot  # Đúng với pyTelegramBotAPI

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== CẤU HÌNH ====================
USER_NAME = os.environ.get("SKHCN_USER")
PASS_WORD = os.environ.get("SKHCN_PASS")
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_JSON = os.environ.get("GSPREAD_SERVICE_ACCOUNT")
CHAT_ID = os.environ.get("CHAT_ID")
SHEET_NAME = "DANH_SACH_VAN_BAN"
DA_GUI_FILE = "da_gui.json"

# URL hệ thống
BASE_URL = "https://hscvkhcn.dienbien.gov.vn"
DB_PATH = "/qlvb/vbden.nsf"
VIEW_NAME = "Private_ChoXL_KoHan"

# ==================== HÀM TIỆN ÍCH ====================
def tinh_ngay_con_lai(han_xu_ly: str) -> int:
    """Tính số ngày còn lại đến hạn xử lý"""
    if not han_xu_ly or han_xu_ly == "Không có hạn":
        return 999
    try:
        for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%Y-%m-%d']:
            try:
                han_date = datetime.strptime(han_xu_ly.strip(), fmt)
                today = datetime.now()
                delta = (han_date - today).days
                return max(delta, -1)
            except:
                continue
        return 999
    except:
        return 999

def tach_chu_ky(so_hieu: str) -> str:
    """Tách số và ký hiệu văn bản"""
    match = re.match(r'^(\d+)/([A-Za-z0-9\-]+)', so_hieu)
    if match:
        return f"Số {match.group(1)} - {match.group(2)}"
    return so_hieu

# ==================== ĐỌC/GHI JSON ====================
def load_da_gui() -> Set[str]:
    """Đọc danh sách văn bản đã gửi"""
    if os.path.exists(DA_GUI_FILE):
        try:
            with open(DA_GUI_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('da_gui', []))
        except:
            pass
    return set()

def load_danh_sach_chi_tiet() -> List[Dict]:
    """Đọc danh sách chi tiết văn bản"""
    if os.path.exists(DA_GUI_FILE):
        try:
            with open(DA_GUI_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('danh_sach_chi_tiet', [])
        except:
            pass
    return []

def save_full_data(da_gui: Set[str], danh_sach_chi_tiet: List[Dict]):
    """Lưu đầy đủ dữ liệu vào JSON"""
    try:
        data = {
            'da_gui': list(da_gui),
            'danh_sach_chi_tiet': danh_sach_chi_tiet,
            'last_update': datetime.now().isoformat(),
            'total_count': len(danh_sach_chi_tiet)
        }
        with open(DA_GUI_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Đã lưu {len(danh_sach_chi_tiet)} văn bản vào JSON")
    except Exception as e:
        print(f"❌ Lỗi lưu JSON: {e}")

# ==================== KẾT NỐI GOOGLE SHEETS ====================
def ket_noi_sheets():
    """Kết nối Google Sheets (backup)"""
    if not GOOGLE_JSON:
        return None
    try:
        scope = ["https://spreadsheets.google.com/feeds",
                 "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(GOOGLE_JSON), scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME)
    except Exception as e:
        print(f"⚠️ Lỗi Sheets: {e}")
        return None

# ==================== ĐĂNG NHẬP DOMINO ====================
def domino_login(session: requests.Session) -> bool:
    """Đăng nhập Domino"""
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
        if response.status_code == 200 and "Login" not in response.text:
            print("✅ Đăng nhập thành công")
            return True
        print(f"❌ Đăng nhập thất bại: {response.status_code}")
        return False
    except Exception as e:
        print(f"❌ Lỗi đăng nhập: {e}")
        return False

# ==================== QUÉT HTML (CHÍNH) ====================
def quet_van_ban_tu_html(session: requests.Session) -> List[Dict]:
    """Quét danh sách văn bản từ HTML"""
    url_target = f"{BASE_URL}{DB_PATH}/{VIEW_NAME}?OpenForm"
    
    try:
        response = session.get(url_target, verify=False, timeout=30)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        ket_qua = []
        
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                tds = row.find_all('td')
                if len(tds) < 5:
                    continue
                
                cols = [re.sub(r'\s+', ' ', td.get_text()).strip() for td in tds]
                
                for i, c in enumerate(cols):
                    if re.match(r'^\d{2}[/-]\d{2}[/-]\d{4}$', c):
                        ngay = c
                        so_hieu = cols[i+1] if i+1 < len(cols) else ""
                        co_quan = cols[i+2] if i+2 < len(cols) else ""
                        trich_yeu = cols[i+3] if i+3 < len(cols) else ""
                        han_xu_ly = cols[i+4] if i+4 < len(cols) else "Không có hạn"
                        
                        so_hieu = so_hieu.replace('✅', '').replace('❌', '').strip()
                        trich_yeu = re.sub(r'[✅❌]', '', trich_yeu).strip()
                        
                        if so_hieu and ("/" in so_hieu or "-" in so_hieu):
                            ngay_con_lai = tinh_ngay_con_lai(han_xu_ly)
                            
                            ket_qua.append({
                                'so_hieu': so_hieu,
                                'so_hieu_dep': tach_chu_ky(so_hieu),
                                'ngay': ngay,
                                'han_xu_ly': han_xu_ly,
                                'ngay_con_lai': ngay_con_lai,
                                'trich_yeu': trich_yeu[:250],
                                'co_quan': co_quan,
                                'trang_thai': 'Đang chờ xử lý'
                            })
                        break
        
        # Loại bỏ trùng lặp
        unique = {}
        for vb in ket_qua:
            if vb['so_hieu'] not in unique:
                unique[vb['so_hieu']] = vb
        
        danh_sach = list(unique.values())
        print(f"📊 Quét HTML: {len(danh_sach)} văn bản")
        return danh_sach
        
    except Exception as e:
        print(f"❌ Lỗi quét HTML: {e}")
        return []

# ==================== GỬI THÔNG BÁO ====================
def gui_thong_bao_telegram(van_ban_moi: List[Dict], bot_instance):
    """Gửi thông báo Telegram chi tiết"""
    if not van_ban_moi:
        return
    
    sap_het_han = [vb for vb in van_ban_moi if vb.get('ngay_con_lai', 999) <= 3]
    
    msg = f"🔔 *CÓ {len(van_ban_moi)} VĂN BẢN ĐẾN MỚI*\n\n"
    
    if sap_het_han:
        msg += f"⚠️ *Cảnh báo:* {len(sap_het_han)} văn bản có hạn xử lý trong 3 ngày tới\n\n"
    
    for i, vb in enumerate(van_ban_moi[:10], 1):
        if vb.get('ngay_con_lai', 999) <= 1:
            emoji = "🔴"
            warn = f" *HẾT HẠN HÔM NAY!*"
        elif vb.get('ngay_con_lai', 999) <= 3:
            emoji = "🟡"
            warn = f" *Còn {vb['ngay_con_lai']} ngày*"
        else:
            emoji = "📄"
            warn = ""
        
        msg += f"{emoji} *{vb['so_hieu']}*\n"
        msg += f"   📅 Ngày: {vb['ngay']}"
        if vb.get('han_xu_ly') and vb['han_xu_ly'] != "Không có hạn":
            msg += f" | ⏰ Hạn: {vb['han_xu_ly']}{warn}\n"
        else:
            msg += f"\n"
        msg += f"   🏢 {vb['co_quan']}\n"
        msg += f"   📝 {vb['trich_yeu'][:100]}...\n\n"
    
    if len(van_ban_moi) > 10:
        msg += f"... và {len(van_ban_moi) - 10} văn bản khác\n"
        msg += f"📌 Gửi /list_all để xem toàn bộ"
    
    try:
        bot_instance.send_message(CHAT_ID, msg, parse_mode='Markdown')
        print(f"✅ Đã gửi Telegram: {len(van_ban_moi)} văn bản")
    except Exception as e:
        print(f"❌ Lỗi gửi Telegram: {e}")

def gui_bao_cao_hang_ngay(bot_instance, danh_sach: List[Dict]):
    """Gửi báo cáo tổng hợp mỗi ngày lúc 8h sáng"""
    hom_nay = datetime.now().strftime('%d/%m/%Y')
    
    qua_han = [vb for vb in danh_sach if vb.get('ngay_con_lai', 999) < 0]
    hom_nay_het_han = [vb for vb in danh_sach if vb.get('ngay_con_lai', 999) == 0]
    sap_het_han = [vb for vb in danh_sach if 0 < vb.get('ngay_con_lai', 999) <= 3]
    
    msg = f"📊 *BÁO CÁO HÀNG NGÀY - {hom_nay}*\n\n"
    msg += f"📋 Tổng số văn bản đang chờ: {len(danh_sach)}\n\n"
    
    if qua_han:
        msg += f"🔴 *QUÁ HẠN:* {len(qua_han)} văn bản\n"
        for vb in qua_han[:5]:
            msg += f"   - {vb['so_hieu']} (quá hạn {abs(vb['ngay_con_lai'])} ngày)\n"
        msg += "\n"
    
    if hom_nay_het_han:
        msg += f"⚠️ *HẾT HẠN HÔM NAY:* {len(hom_nay_het_han)} văn bản\n"
        for vb in hom_nay_het_han[:5]:
            msg += f"   - {vb['so_hieu']}\n"
        msg += "\n"
    
    if sap_het_han:
        msg += f"🟡 *SẮP HẾT HẠN (3 ngày tới):* {len(sap_het_han)} văn bản\n"
        for vb in sap_het_han[:5]:
            msg += f"   - {vb['so_hieu']} (còn {vb['ngay_con_lai']} ngày)\n"
    
    try:
        bot_instance.send_message(CHAT_ID, msg, parse_mode='Markdown')
    except Exception as e:
        print(f"❌ Lỗi gửi báo cáo: {e}")

# ==================== MAIN ====================
def main():
    print(f"🚀 Bắt đầu quét: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    if not USER_NAME or not PASS_WORD:
        print("❌ Thiếu tài khoản đăng nhập")
        return
    
    session = requests.Session()
    if not domino_login(session):
        print("❌ Đăng nhập thất bại")
        return
    
    danh_sach_moi_nhat = quet_van_ban_tu_html(session)
    if not danh_sach_moi_nhat:
        print("📭 Không lấy được dữ liệu")
        return
    
    print(f"📊 Tổng số văn bản trong hệ thống: {len(danh_sach_moi_nhat)}")
    
    da_gui = load_da_gui()
    danh_sach_cu = load_danh_sach_chi_tiet()
    
    so_hieu_cu = {vb['so_hieu'] for vb in danh_sach_cu}
    van_ban_moi = [vb for vb in danh_sach_moi_nhat if vb['so_hieu'] not in so_hieu_cu]
    
    for vb in van_ban_moi:
        da_gui.add(vb['so_hieu'])
    
    save_full_data(da_gui, danh_sach_moi_nhat)
    
    if van_ban_moi and TOKEN and CHAT_ID:
        bot_instance = telebot.TeleBot(TOKEN)
        gui_thong_bao_telegram(van_ban_moi, bot_instance)
        
        sheet = ket_noi_sheets()
        if sheet:
            try:
                sheet_main = sheet.sheet1
                for vb in reversed(van_ban_moi):
                    row = [vb['so_hieu'], vb['ngay'], vb['trich_yeu'], 
                           vb['co_quan'], vb.get('han_xu_ly', '')]
                    sheet_main.insert_row(row, 2)
                    time.sleep(0.5)
                print(f"✅ Đã lưu {len(van_ban_moi)} văn bản vào Sheets")
            except Exception as e:
                print(f"⚠️ Lỗi lưu Sheets: {e}")
    
    now = datetime.now()
    if now.hour == 8 and now.minute < 30 and TOKEN and CHAT_ID:
        bot_instance = telebot.TeleBot(TOKEN)
        gui_bao_cao_hang_ngay(bot_instance, danh_sach_moi_nhat)
    
    print(f"✅ Hoàn thành! Thêm {len(van_ban_moi)} văn bản mới")

if __name__ == "__main__":
    main()
