import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# ========== CẤU HÌNH ==========
DATA_FILE = "da_guijson"  # file dữ liệu JSON của bạn

# ========== ĐỊNH NGHĨA KHUNG GIỜ ==========
KHUNG_GIO = {
    "sáng": (0, 11),      # 00:00 - 11:59
    "trưa": (11, 13),     # 11:00 - 12:59
    "chiều": (13, 17),    # 13:00 - 16:59
    "tối": (17, 24),      # 17:00 - 23:59
}

# ========== HÀM ĐỌC DỮ LIỆU ==========
def doc_du_lieu() -> Dict:
    """Đọc dữ liệu văn bản từ file JSON"""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"danh_sach_vb": []}
    except json.JSONDecodeError:
        return {"danh_sach_vb": []}

# ========== HÀM LỌC THEO THỜI GIAN ==========
def loc_theo_ngay(danh_sach: List[Dict], ngay_target: str) -> List[Dict]:
    """Lọc văn bản theo ngày (định dạng DD/MM/YYYY)"""
    return [vb for vb in danh_sach if vb.get("ngay_den") == ngay_target]

def loc_theo_khung_gio(danh_sach: List[Dict], khung: str) -> List[Dict]:
    """Lọc văn bản theo khung giờ (sáng, trưa, chiều, tối)"""
    if khung not in KHUNG_GIO:
        return []
    gio_bat_dau, gio_ket_thuc = KHUNG_GIO[khung]
    ket_qua = []
    for vb in danh_sach:
        gio_den = vb.get("gio_den", "")
        if gio_den and ":" in gio_den:
            try:
                gio = int(gio_den.split(":")[0])
                if gio_bat_dau <= gio < gio_ket_thuc:
                    ket_qua.append(vb)
            except:
                pass
    return ket_qua

def loc_theo_tuan(danh_sach: List[Dict]) -> List[Dict]:
    """Lọc văn bản trong 7 ngày gần đây (tính từ hôm nay)"""
    hom_nay = datetime.now()
    tuan_truoc = hom_nay - timedelta(days=7)
    ket_qua = []
    for vb in danh_sach:
        try:
            ngay_vb = datetime.strptime(vb.get("ngay_den", ""), "%d/%m/%Y")
            if tuan_truoc <= ngay_vb <= hom_nay:
                ket_qua.append(vb)
        except:
            pass
    return ket_qua

def loc_theo_thang(danh_sach: List[Dict]) -> List[Dict]:
    """Lọc văn bản trong tháng hiện tại"""
    thang_hien_tai = datetime.now().month
    nam_hien_tai = datetime.now().year
    ket_qua = []
    for vb in danh_sach:
        try:
            ngay_vb = datetime.strptime(vb.get("ngay_den", ""), "%d/%m/%Y")
            if ngay_vb.month == thang_hien_tai and ngay_vb.year == nam_hien_tai:
                ket_qua.append(vb)
        except:
            pass
    return ket_qua

# ========== XỬ LÝ CÂU HỎI TỪ NGƯỜI DÙNG ==========
def xu_ly_cau_hoi(cau_hoi: str) -> str:
    """Xử lý câu hỏi và trả về câu trả lời cho bot"""
    du_lieu = doc_du_lieu()
    danh_sach_vb = du_lieu.get("danh_sach_vb", [])
    cau_hoi = cau_hoi.lower().strip()
    
    # 1. Hỏi danh sách
    if "danh sách" in cau_hoi:
        return hien_thi_danh_sach(danh_sach_vb, cau_hoi)
    
    # 2. Hỏi số lượng
    if "bao nhiêu" in cau_hoi or "mấy" in cau_hoi or "số lượng" in cau_hoi:
        return dem_van_ban(danh_sach_vb, cau_hoi)
    
    # 3. Hỏi tổng hợp (báo cáo ngày)
    if "báo cáo" in cau_hoi or "tổng hợp" in cau_hoi:
        return bao_cao_ngay(danh_sach_vb)
    
    return "❓ Tôi chưa hiểu câu hỏi. Bạn có thể thử:\n- 'hôm nay có bao nhiêu văn bản'\n- 'danh sách văn bản sáng nay'\n- 'báo cáo ngày hôm qua'"

def hien_thi_danh_sach(danh_sach: List[Dict], cau_hoi: str) -> str:
    """Hiển thị danh sách văn bản theo yêu cầu"""
    # Xác định thời gian cần lọc
    if "sáng nay" in cau_hoi:
        ds_loc = loc_theo_khung_gio(danh_sach, "sáng")
        tieu_de = "☀️ Danh sách văn bản SÁNG NAY"
    elif "trưa nay" in cau_hoi:
        ds_loc = loc_theo_khung_gio(danh_sach, "trưa")
        tieu_de = "☀️ Danh sách văn bản TRƯA NAY"
    elif "chiều nay" in cau_hoi:
        ds_loc = loc_theo_khung_gio(danh_sach, "chiều")
        tieu_de = "🌤️ Danh sách văn bản CHIỀU NAY"
    elif "tối nay" in cau_hoi:
        ds_loc = loc_theo_khung_gio(danh_sach, "tối")
        tieu_de = "🌙 Danh sách văn bản TỐI NAY"
    elif "hôm nay" in cau_hoi:
        ngay_hom_nay = datetime.now().strftime("%d/%m/%Y")
        ds_loc = loc_theo_ngay(danh_sach, ngay_hom_nay)
        tieu_de = f"📋 Danh sách văn bản HÔM NAY ({ngay_hom_nay})"
    elif "hôm qua" in cau_hoi:
        ngay_hom_qua = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
        ds_loc = loc_theo_ngay(danh_sach, ngay_hom_qua)
        tieu_de = f"📋 Danh sách văn bản HÔM QUA ({ngay_hom_qua})"
    elif "tuần này" in cau_hoi:
        ds_loc = loc_theo_tuan(danh_sach)
        tieu_de = "📋 Danh sách văn bản TUẦN NÀY"
    elif "tháng này" in cau_hoi:
        ds_loc = loc_theo_thang(danh_sach)
        tieu_de = "📋 Danh sách văn bản THÁNG NÀY"
    else:
        return "❓ Hãy nói rõ: 'danh sách văn bản sáng nay', 'danh sách hôm nay', v.v."
    
    if not ds_loc:
        return f"{tieu_de}\n📭 Không có văn bản nào."
    
    ket_qua = f"{tieu_de} (tổng: {len(ds_loc)}):\n"
    for i, vb in enumerate(ds_loc, 1):
        gio = vb.get("gio_den", "??:??")
        so_hieu = vb.get("so_hieu", "Không số")
        trich_yeu = vb.get("trich_yeu", "")[:60]
        ket_qua += f"{i}. [{gio}] {so_hieu} - {trich_yeu}\n"
    return ket_qua

def dem_van_ban(danh_sach: List[Dict], cau_hoi: str) -> str:
    """Đếm số lượng văn bản theo yêu cầu"""
    if "sáng nay" in cau_hoi:
        ds_loc = loc_theo_khung_gio(danh_sach, "sáng")
        return f"☀️ Sáng nay có **{len(ds_loc)}** văn bản đến."
    elif "trưa nay" in cau_hoi:
        ds_loc = loc_theo_khung_gio(danh_sach, "trưa")
        return f"☀️ Trưa nay có **{len(ds_loc)}** văn bản đến."
    elif "chiều nay" in cau_hoi:
        ds_loc = loc_theo_khung_gio(danh_sach, "chiều")
        return f"🌤️ Chiều nay có **{len(ds_loc)}** văn bản đến."
    elif "tối nay" in cau_hoi:
        ds_loc = loc_theo_khung_gio(danh_sach, "tối")
        return f"🌙 Tối nay có **{len(ds_loc)}** văn bản đến."
    elif "hôm nay" in cau_hoi:
        ngay_hom_nay = datetime.now().strftime("%d/%m/%Y")
        ds_loc = loc_theo_ngay(danh_sach, ngay_hom_nay)
        return f"📅 Hôm nay ({ngay_hom_nay}) có **{len(ds_loc)}** văn bản đến."
    elif "hôm qua" in cau_hoi:
        ngay_hom_qua = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
        ds_loc = loc_theo_ngay(danh_sach, ngay_hom_qua)
        return f"📅 Hôm qua ({ngay_hom_qua}) có **{len(ds_loc)}** văn bản đến."
    elif "tuần này" in cau_hoi:
        ds_loc = loc_theo_tuan(danh_sach)
        return f"📅 Tuần này có **{len(ds_loc)}** văn bản đến."
    elif "tháng này" in cau_hoi:
        ds_loc = loc_theo_thang(danh_sach)
        return f"📅 Tháng này có **{len(ds_loc)}** văn bản đến."
    else:
        return "❓ Hãy hỏi rõ: 'hôm nay có bao nhiêu văn bản', 'sáng nay có mấy văn bản', v.v."

def bao_cao_ngay(danh_sach: List[Dict]) -> str:
    """Tạo báo cáo tổng hợp trong ngày"""
    ngay_hom_nay = datetime.now().strftime("%d/%m/%Y")
    ds_hom_nay = loc_theo_ngay(danh_sach, ngay_hom_nay)
    
    sang = loc_theo_khung_gio(ds_hom_nay, "sáng")
    trua = loc_theo_khung_gio(ds_hom_nay, "trưa")
    chieu = loc_theo_khung_gio(ds_hom_nay, "chiều")
    toi = loc_theo_khung_gio(ds_hom_nay, "tối")
    
    bc = f"📊 **BÁO CÁO NGÀY {ngay_hom_nay}**\n"
    bc += f"─────────────────\n"
    bc += f"☀️ Sáng: {len(sang)} văn bản\n"
    bc += f"☀️ Trưa: {len(trua)} văn bản\n"
    bc += f"🌤️ Chiều: {len(chieu)} văn bản\n"
    bc += f"🌙 Tối: {len(toi)} văn bản\n"
    bc += f"─────────────────\n"
    bc += f"📌 **Tổng: {len(ds_hom_nay)} văn bản**"
    return bc

# ========== HÀM CHÍNH CHO TELEGRAM BOT ==========
def tra_loi_tin_nhan(noi_dung: str) -> str:
    """Hàm này được gọi mỗi khi bot nhận được tin nhắn từ user"""
    return xu_ly_cau_hoi(noi_dung)
