import json
import re
from datetime import datetime

DATA_FILE = "da_guijson"

def doc_du_lieu():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"danh_sach_vb": []}

def ghi_du_lieu(du_lieu):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(du_lieu, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def trich_xuat_van_ban(van_ban_tho):
    ket_qua = {
        "so_hieu": "",
        "ngay_den": datetime.now().strftime("%d/%m/%Y"),
        "gio_den": datetime.now().strftime("%H:%M"),
        "trich_yeu": ""
    }
    
    # Tìm số hiệu
    match = re.search(r'(\d+[\-/][A-Z0-9\-/]+)', van_ban_tho)
    if match:
        ket_qua["so_hieu"] = match.group(1)
    
    # Tìm ngày đến
    match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', van_ban_tho)
    if match:
        ket_qua["ngay_den"] = match.group(1)
    
    # Tìm trích yếu
    match = re.search(r'Trích yếu:\s*(.+?)(?:\n|$)', van_ban_tho, re.IGNORECASE)
    if not match:
        match = re.search(r'V/v\s*(.+?)(?:\n|$)', van_ban_tho, re.IGNORECASE)
    if match:
        ket_qua["trich_yeu"] = match.group(1).strip()[:100]
    
    return ket_qua

def them_van_ban(van_ban_tho):
    du_lieu = doc_du_lieu()
    danh_sach = du_lieu.get("danh_sach_vb", [])
    
    vb_moi = trich_xuat_van_ban(van_ban_tho)
    
    if not vb_moi["so_hieu"]:
        return "❌ Không tìm thấy số hiệu văn bản"
    
    # Kiểm tra trùng
    for vb in danh_sach:
        if vb.get("so_hieu") == vb_moi["so_hieu"]:
            return f"⚠️ Văn bản {vb_moi['so_hieu']} đã tồn tại"
    
    danh_sach.append(vb_moi)
    du_lieu["danh_sach_vb"] = danh_sach
    
    if ghi_du_lieu(du_lieu):
        return f"✅ Đã thêm: {vb_moi['so_hieu']} - {vb_moi['ngay_den']} lúc {vb_moi['gio_den']}"
    return "❌ Lỗi lưu file"

def quet_van_ban(ocr_text):
    return them_van_ban(ocr_text)
