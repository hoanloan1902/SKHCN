import re
import json
from datetime import datetime, timedelta

# File dữ liệu
DATA_FILE = "da_guijson"

# Khung giờ
KHUNG_GIO = {
    "sáng": (0, 11),
    "trưa": (11, 13),
    "chiều": (13, 17),
    "tối": (17, 24),
}

def doc_du_lieu():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"danh_sach_vb": []}

def loc_theo_ngay(danh_sach, ngay_target):
    return [vb for vb in danh_sach if vb.get("ngay_den") == ngay_target]

def loc_theo_khung_gio(danh_sach, khung):
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

def loc_theo_tuan(danh_sach):
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

def loc_theo_thang(danh_sach):
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

def xu_ly_cau_hoi(cau_hoi):
    du_lieu = doc_du_lieu()
    danh_sach_vb = du_lieu.get("danh_sach_vb", [])
    cau_hoi = cau_hoi.lower().strip()
    
    # Thống kê
    if cau_hoi == "thống kê" or cau_hoi == "/thongke":
        return bao_cao_ngay(danh_sach_vb)
    
    # Danh sách
    if "danh sách" in cau_hoi:
        return hien_thi_danh_sach(danh_sach_vb, cau_hoi)
    
    # Hỏi số lượng
    if "bao nhiêu" in cau_hoi or "mấy" in cau_hoi:
        return dem_van_ban(danh_sach_vb, cau_hoi)
    
    # Hỏi ngắn gọn: "sáng nay", "hôm nay",...
    if cau_hoi == "sáng nay":
        return dem_van_ban(danh_sach_vb, "sáng nay có bao nhiêu")
    if cau_hoi == "trưa nay":
        return dem_van_ban(danh_sach_vb, "trưa nay có bao nhiêu")
    if cau_hoi == "chiều nay":
        return dem_van_ban(danh_sach_vb, "chiều nay có bao nhiêu")
    if cau_hoi == "tối nay":
        return dem_van_ban(danh_sach_vb, "tối nay có bao nhiêu")
    if cau_hoi == "hôm nay":
        return dem_van_ban(danh_sach_vb, "hôm nay có bao nhiêu")
    if cau_hoi == "hôm qua":
        return dem_van_ban(danh_sach_vb, "hôm qua có bao nhiêu")
    if cau_hoi == "tuần này":
        return dem_van_ban(danh_sach_vb, "tuần này có bao nhiêu")
    if cau_hoi == "tháng này":
        return dem_van_ban(danh_sach_vb, "tháng này có bao nhiêu")
    
    return "❓ Tôi chưa hiểu. Bạn có thể hỏi:\n- thống kê\n- sáng nay\n- hôm nay\n- danh sách hôm nay"

def hien_thi_danh_sach(danh_sach, cau_hoi):
    if "sáng nay" in cau_hoi:
        ds_loc = loc_theo_khung_gio(danh_sach, "sáng")
        tieu_de = "☀️ DANH SÁCH VĂN BẢN SÁNG NAY"
    elif "trưa nay" in cau_hoi:
        ds_loc = loc_theo_khung_gio(danh_sach, "trưa")
        tieu_de = "☀️ DANH SÁCH VĂN BẢN TRƯA NAY"
    elif "chiều nay" in cau_hoi:
        ds_loc = loc_theo_khung_gio(danh_sach, "chiều")
        tieu_de = "🌤️ DANH SÁCH VĂN BẢN CHIỀU NAY"
    elif "tối nay" in cau_hoi:
        ds_loc = loc_theo_khung_gio(danh_sach, "tối")
        tieu_de = "🌙 DANH SÁCH VĂN BẢN TỐI NAY"
    elif "hôm nay" in cau_hoi:
        ngay_hom_nay = datetime.now().strftime("%d/%m/%Y")
        ds_loc = loc_theo_ngay(danh_sach, ngay_hom_nay)
        tieu_de = f"📋 DANH SÁCH VĂN BẢN HÔM NAY ({ngay_hom_nay})"
    elif "hôm qua" in cau_hoi:
        ngay_hom_qua = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
        ds_loc = loc_theo_ngay(danh_sach, ngay_hom_qua)
        tieu_de = f"📋 DANH SÁCH VĂN BẢN HÔM QUA ({ngay_hom_qua})"
    elif "tuần này" in cau_hoi:
        ds_loc = loc_theo_tuan(danh_sach)
        tieu_de = "📋 DANH SÁCH VĂN BẢN TUẦN NÀY"
    elif "tháng này" in cau_hoi:
        ds_loc = loc_theo_thang(danh_sach)
        tieu_de = "📋 DANH SÁCH VĂN BẢN THÁNG NÀY"
    else:
        return "❓ Hãy nói rõ: 'danh sách sáng nay', 'danh sách hôm nay'"
    
    if not ds_loc:
        return f"{tieu_de}\n📭 Không có văn bản nào."
    
    ket_qua = f"{tieu_de} (Tổng: {len(ds_loc)}):\n"
    for i, vb in enumerate(ds_loc, 1):
        gio = vb.get("gio_den", "??:??")
        so_hieu = vb.get("so_hieu", "Không số")
        trich_yeu = vb.get("trich_yeu", "")[:50]
        ket_qua += f"{i}. [{gio}] {so_hieu} - {trich_yeu}\n"
    return ket_qua

def dem_van_ban(danh_sach, cau_hoi):
    if "sáng nay" in cau_hoi:
        so_luong = len(loc_theo_khung_gio(danh_sach, "sáng"))
        return f"☀️ Sáng nay có {so_luong} văn bản đến."
    if "trưa nay" in cau_hoi:
        so_luong = len(loc_theo_khung_gio(danh_sach, "trưa"))
        return f"☀️ Trưa nay có {so_luong} văn bản đến."
    if "chiều nay" in cau_hoi:
        so_luong = len(loc_theo_khung_gio(danh_sach, "chiều"))
        return f"🌤️ Chiều nay có {so_luong} văn bản đến."
    if "tối nay" in cau_hoi:
        so_luong = len(loc_theo_khung_gio(danh_sach, "tối"))
        return f"🌙 Tối nay có {so_luong} văn bản đến."
    if "hôm nay" in cau_hoi:
        ngay_hom_nay = datetime.now().strftime("%d/%m/%Y")
        so_luong = len(loc_theo_ngay(danh_sach, ngay_hom_nay))
        return f"📅 Hôm nay ({ngay_hom_nay}) có {so_luong} văn bản đến."
    if "hôm qua" in cau_hoi:
        ngay_hom_qua = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
        so_luong = len(loc_theo_ngay(danh_sach, ngay_hom_qua))
        return f"📅 Hôm qua ({ngay_hom_qua}) có {so_luong} văn bản đến."
    if "tuần này" in cau_hoi:
        so_luong = len(loc_theo_tuan(danh_sach))
        return f"📅 Tuần này có {so_luong} văn bản đến."
    if "tháng này" in cau_hoi:
        so_luong = len(loc_theo_thang(danh_sach))
        return f"📅 Tháng này có {so_luong} văn bản đến."
    return None

def bao_cao_ngay(danh_sach):
    ngay_hom_nay = datetime.now().strftime("%d/%m/%Y")
    ds_hom_nay = loc_theo_ngay(danh_sach, ngay_hom_nay)
    
    sang = len(loc_theo_khung_gio(ds_hom_nay, "sáng"))
    trua = len(loc_theo_khung_gio(ds_hom_nay, "trưa"))
    chieu = len(loc_theo_khung_gio(ds_hom_nay, "chiều"))
    toi = len(loc_theo_khung_gio(ds_hom_nay, "tối"))
    
    bc = f"📊 BÁO CÁO NGÀY {ngay_hom_nay}\n"
    bc += "─────────────────\n"
    bc += f"☀️ Sáng: {sang} văn bản\n"
    bc += f"☀️ Trưa: {trua} văn bản\n"
    bc += f"🌤️ Chiều: {chieu} văn bản\n"
    bc += f"🌙 Tối: {toi} văn bản\n"
    bc += "─────────────────\n"
    bc += f"📌 Tổng: {len(ds_hom_nay)} văn bản"
    return bc

# Hàm chính để bot gọi
def tra_loi_tin_nhan(noi_dung):
    return xu_ly_cau_hoi(noi_dung)
