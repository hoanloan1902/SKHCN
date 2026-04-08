import json
import re
from datetime import datetime
from typing import List, Dict

DATA_FILE = "da_guijson"

def doc_danh_sach_hien_tai() -> Dict:
    """Đọc danh sách văn bản hiện tại từ file JSON"""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"danh_sach_vb": []}

def ghi_danh_sach(du_lieu: Dict) -> bool:
    """Ghi danh sách văn bản vào file JSON"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(du_lieu, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Lỗi khi ghi file: {e}")
        return False

def trich_xuat_thong_tin(van_ban_tho: str) -> Dict:
    """
    Trích xuất thông tin từ văn bản thô (OCR hoặc copy-paste)
    Trả về dict: {"so_hieu": ..., "ngay_den": ..., "gio_den": ..., "trich_yeu": ...}
    """
    ket_qua = {
        "so_hieu": "",
        "ngay_den": datetime.now().strftime("%d/%m/%Y"),
        "gio_den": datetime.now().strftime("%H:%M"),
        "trich_yeu": ""
    }
    
    # Tìm số hiệu (VD: 533/UBND-VHXH, 726/QĐ-UBND, 2309/UBND-PVHCC)
    match_so_hieu = re.search(r'(\d+[\-/][A-Z0-9\-/]+)', van_ban_tho)
    if match_so_hieu:
        ket_qua["so_hieu"] = match_so_hieu.group(1)
    
    # Tìm ngày đến (VD: 07/04/2026, 30/03/2026)
    match_ngay = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', van_ban_tho)
    if match_ngay:
        ket_qua["ngay_den"] = match_ngay.group(1)
    
    # Tìm trích yếu (dòng sau "Trích yếu:" hoặc "V/v")
    match_trich_yeu = re.search(r'Trích yếu:\s*(.+?)(?:\n|$)', van_ban_tho, re.IGNORECASE)
    if not match_trich_yeu:
        match_trich_yeu = re.search(r'V/v\s*(.+?)(?:\n|$)', van_ban_tho, re.IGNORECASE)
    if match_trich_yeu:
        ket_qua["trich_yeu"] = match_trich_yeu.group(1).strip()[:100]
    
    return ket_qua

def kiem_tra_trung(van_ban_moi: Dict, danh_sach_cu: List[Dict]) -> bool:
    """Kiểm tra văn bản đã tồn tại chưa (dựa trên số hiệu + ngày đến)"""
    for vb in danh_sach_cu:
        if vb.get("so_hieu") == van_ban_moi.get("so_hieu") and \
           vb.get("ngay_den") == van_ban_moi.get("ngay_den"):
            return True
    return False

def them_van_ban_moi(van_ban_tho: str) -> str:
    """Thêm một văn bản mới vào hệ thống"""
    du_lieu = doc_danh_sach_hien_tai()
    danh_sach = du_lieu.get("danh_sach_vb", [])
    
    van_ban_moi = trich_xuat_thong_tin(van_ban_tho)
    
    if not van_ban_moi.get("so_hieu"):
        return "❌ Không tìm thấy số hiệu văn bản. Vui lòng kiểm tra lại."
    
    if kiem_tra_trung(van_ban_moi, danh_sach):
        return f"⚠️ Văn bản {van_ban_moi['so_hieu']} đã tồn tại trong hệ thống."
    
    danh_sach.append(van_ban_moi)
    du_lieu["danh_sach_vb"] = danh_sach
    
    if ghi_danh_sach(du_lieu):
        return f"✅ Đã thêm văn bản:\n📄 {van_ban_moi['so_hieu']}\n📅 {van_ban_moi['ngay_den']} lúc {van_ban_moi['gio_den']}\n📝 {van_ban_moi['trich_yeu']}"
    else:
        return "❌ Lỗi khi lưu văn bản."

def quet_van_ban_tu_anh(ocr_text: str) -> str:
    """Quét văn bản từ ảnh (đã qua OCR) và thêm vào hệ thống"""
    return them_van_ban_moi(ocr_text)

# Ví dụ chạy thử
if __name__ == "__main__":
    # Test với mẫu
    mau_van_ban = """
    Số hiệu: 533/UBND-VHXH
    Ngày đến: 07/04/2026
    Cơ quan gửi: UBND Xã Mường Nhé
    Trích yếu: V/v Đề nghị cho ý kiến thẩm định đối với dự thảo Đề án phân loại đơn vị hành chính xã Mường Nhé.
    """
    print(them_van_ban_moi(mau_van_ban))
