import os
import re
import json
import requests
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import PyPDF2
from io import BytesIO

# ============ CẤU HÌNH ============
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Google Sheets config
GOOGLE_SHEET_NAME = "VanBan"  # Tên file Google Sheet của bạn
SERVICE_ACCOUNT_INFO = json.loads(os.getenv("GSPREAD_SERVICE_ACCOUNT"))

# Kết nối Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, scope)
client = gspread.authorize(creds)

# Mở sheet
spreadsheet = client.open(GOOGLE_SHEET_NAME)
sheet_den = spreadsheet.worksheet("VB_Den")
sheet_di = spreadsheet.worksheet("VB_Di")

# ============ HÀM GỬI TIN NHẮN TELEGRAM ============
def gui_telegram(noi_dung):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": noi_dung, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Lỗi: {e}")

# ============ TRÍCH XUẤT THÔNG TIN ============
def doc_noi_dung_pdf(url_pdf):
    """Đọc nội dung PDF từ URL"""
    try:
        response = requests.get(url_pdf, timeout=30)
        pdf_file = BytesIO(response.content)
        reader = PyPDF2.PdfReader(pdf_file)
        noi_dung = ""
        for page in reader.pages:
            noi_dung += page.extract_text()
        return noi_dung
    except Exception as e:
        print(f"Lỗi đọc PDF: {e}")
        return ""

def trich_xuat_thong_tin(noi_dung, loai="den"):
    """Trích xuất số hiệu, trích yếu, hạn xử lý, nơi nhận"""
    ket_qua = {
        "so_hieu": "",
        "trich_yeu": "",
        "han_xu_ly": None,
        "noi_nhan": ""
    }
    
    # Tìm số hiệu (VD: 123/QĐ-UBND, 456/CV-STP)
    match_sh = re.search(r'(\d+/[A-Z0-9\-\/]+)', noi_dung)
    if match_sh:
        ket_qua["so_hieu"] = match_sh.group(1)
    
    # Tìm trích yếu
    patterns_ty = [
        r'(?:Trích yếu|V/v|Về việc)[:\s]+([^\n]{10,200})',
        r'(?:Nội dung)[:\s]+([^\n]{10,200})'
    ]
    for pattern in patterns_ty:
        match_ty = re.search(pattern, noi_dung, re.IGNORECASE)
        if match_ty:
            ket_qua["trich_yeu"] = match_ty.group(1).strip()[:150]
            break
    
    # Tìm hạn xử lý (chỉ văn bản đến)
    if loai == "den":
        han_patterns = [
            r'(?:hạn|hạn xử lý|thời hạn|deadline|chậm nhất|trước ngày)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})'
        ]
        for pattern in han_patterns:
            match_han = re.search(pattern, noi_dung, re.IGNORECASE)
            if match_han:
                if len(match_han.groups()) == 3:
                    ngay = match_han.group(1).zfill(2)
                    thang = match_han.group(2).zfill(2)
                    nam = match_han.group(3)
                    ket_qua["han_xu_ly"] = f"{ngay}/{thang}/{nam}"
                else:
                    ket_qua["han_xu_ly"] = match_han.group(1).replace('-', '/')
                break
    
    # Tìm nơi nhận (văn bản đi)
    if loai == "di":
        match_noi_nhan = re.search(r'(?:Gửi|Đến|Kính gửi)[:\s]+([^\n]+)', noi_dung, re.IGNORECASE)
        if match_noi_nhan:
            ket_qua["noi_nhan"] = match_noi_nhan.group(1).strip()
    
    return ket_qua

def tinh_ngay_con_lai(han_xu_ly):
    """Tính số ngày còn lại đến hạn"""
    if not han_xu_ly or han_xu_ly == "Không có hạn":
        return ""
    try:
        ngay_han = datetime.strptime(han_xu_ly, '%d/%m/%Y')
        con_lai = (ngay_han - datetime.now()).days
        return con_lai if con_lai >= 0 else 0
    except:
        return ""

# ============ THÊM VĂN BẢN ============
def them_van_ban(noi_dung_pdf, loai="den", file_url=""):
    """Thêm văn bản vào Google Sheet"""
    
    # Trích xuất thông tin
    thong_tin = trich_xuat_thong_tin(noi_dung_pdf, loai)
    
    if not thong_tin["so_hieu"]:
        return f"❌ Không tìm thấy số hiệu trong văn bản"
    
    # Kiểm tra trùng lặp
    if loai == "den":
        existing = sheet_den.col_values(2)  # Cột Số hiệu
        if thong_tin["so_hieu"] in existing:
            return f"⚠️ Văn bản {thong_tin['so_hieu']} đã tồn tại trong sheet VB_Den"
        
        # Tính số ngày còn lại
        con_lai = tinh_ngay_con_lai(thong_tin["han_xu_ly"])
        
        # Thêm dòng mới
        dong_moi = [
            len(sheet_den.get_all_values()),  # ID
            thong_tin["so_hieu"],              # Số hiệu
            datetime.now().strftime('%d/%m/%Y'),  # Ngày đến
            thong_tin["trich_yeu"],            # Trích yếu
            thong_tin["han_xu_ly"] or "Không có hạn",  # Hạn xử lý
            con_lai if con_lai != "" else "",  # Còn lại
            file_url,                          # File PDF
            "",                                # File kèm
            datetime.now().strftime('%d/%m/%Y %H:%M')  # Ngày nhập
        ]
        sheet_den.append_row(dong_moi)
        
        # Tạo thông báo
        tb = f"✅ Đã thêm văn bản ĐẾN: {thong_tin['so_hieu']}\n"
        tb += f"📝 {thong_tin['trich_yeu'][:100]}\n"
        if thong_tin["han_xu_ly"]:
            tb += f"⏰ Hạn: {thong_tin['han_xu_ly']} (còn {con_lai} ngày)"
        return tb
        
    else:  # Văn bản đi
        existing = sheet_di.col_values(2)  # Cột Số hiệu
        if thong_tin["so_hieu"] in existing:
            return f"⚠️ Văn bản {thong_tin['so_hieu']} đã tồn tại trong sheet VB_Di"
        
        dong_moi = [
            len(sheet_di.get_all_values()),  # ID
            thong_tin["so_hieu"],              # Số hiệu
            datetime.now().strftime('%d/%m/%Y'),  # Ngày đi
            thong_tin["trich_yeu"],            # Trích yếu
            thong_tin["noi_nhan"],             # Nơi nhận
            file_url,                          # File PDF
            "",                                # File kèm
            datetime.now().strftime('%d/%m/%Y %H:%M')  # Ngày nhập
        ]
        sheet_di.append_row(dong_moi)
        
        tb = f"✅ Đã thêm văn bản ĐI: {thong_tin['so_hieu']}\n"
        tb += f"📝 {thong_tin['trich_yeu'][:100]}\n"
        if thong_tin["noi_nhan"]:
            tb += f"📬 Gửi: {thong_tin['noi_nhan']}"
        return tb

# ============ TRUY VẤN ============
def tra_cuu(cau_hoi):
    """Xử lý câu hỏi từ người dùng"""
    cau_hoi = cau_hoi.lower().strip()
    
    # Lấy tất cả dữ liệu
    data_den = sheet_den.get_all_values()
    data_di = sheet_di.get_all_values()
    
    # Bỏ header
    if len(data_den) > 1:
        data_den = data_den[1:]
    if len(data_di) > 1:
        data_di = data_di[1:]
    
    # 1. Tổng số văn bản đến
    if "bao nhiêu" in cau_hoi and ("vb đến" in cau_hoi or "văn bản đến" in cau_hoi):
        return f"📊 Tổng số văn bản đến: {len(data_den)}"
    
    # 2. Hôm nay
    if "hôm nay" in cau_hoi:
        hom_nay = datetime.now().strftime('%d/%m/%Y')
        count = sum(1 for row in data_den if len(row) > 2 and row[2] == hom_nay)
        return f"📅 Hôm nay ({hom_nay}) có {count} văn bản đến"
    
    # 3. Văn bản có hạn
    if "có hạn" in cau_hoi:
        vb_han = [row for row in data_den if len(row) > 4 and row[4] != "Không có hạn"]
        if not vb_han:
            return "📭 Không có văn bản nào có hạn xử lý"
        
        ket_qua = f"📋 Có {len(vb_han)} văn bản có hạn:\n\n"
        for row in vb_han[:10]:
            ket_qua += f"📄 {row[1]} - Hạn: {row[4]}\n"
            ket_qua += f"   {row[3][:60]}\n\n"
        return ket_qua
    
    # 4. Sắp hết hạn (còn <= 5 ngày)
    if "sắp hết hạn" in cau_hoi or "gần hết hạn" in cau_hoi:
        vb_sap_het = []
        for row in data_den:
            if len(row) > 5 and row[5] and str(row[5]).isdigit():
                if int(row[5]) <= 5:
                    vb_sap_het.append(row)
        
        if not vb_sap_het:
            return "🎉 Không có văn bản nào sắp hết hạn trong 5 ngày tới"
        
        ket_qua = f"⚠️ {len(vb_sap_het)} văn bản sắp hết hạn:\n\n"
        for row in vb_sap_het[:10]:
            ket_qua += f"🔴 {row[1]} - Còn {row[5]} ngày\n"
            ket_qua += f"   Hạn: {row[4]}\n\n"
        return ket_qua
    
    # 5. Tìm kiếm
    if "tìm" in cau_hoi or "tra" in cau_hoi:
        tu_khoa = re.sub(r'(tìm|tra|kiếm|văn bản|công văn|số)', '', cau_hoi).strip()
        
        # Tìm trong VB_Den
        ket_qua_den = [row for row in data_den if tu_khoa in row[1] or tu_khoa in row[3]]
        
        if ket_qua_den:
            ket_qua = f"🔍 Tìm thấy {len(ket_qua_den)} văn bản:\n\n"
            for row in ket_qua_den[:5]:
                ket_qua += f"📄 {row[1]} - {row[2]}\n"
                ket_qua += f"   {row[3][:60]}\n\n"
            return ket_qua
        else:
            return f"🔍 Không tìm thấy văn bản nào về '{tu_khoa}'"
    
    # 6. Thống kê tháng
    if "tháng" in cau_hoi:
        match_thang = re.search(r'tháng\s+(\d+)', cau_hoi)
        if match_thang:
            thang = match_thang.group(1).zfill(2)
            nam = datetime.now().year
            count = sum(1 for row in data_den if len(row) > 2 and f"/{thang}/{nam}" in row[2])
            return f"📊 Tháng {thang}/{nam} có {count} văn bản đến"
    
    return "❓ Hãy thử hỏi:\n- Có bao nhiêu văn bản đến?\n- Hôm nay có mấy văn bản?\n- Văn bản nào có hạn?\n- Tìm 123/QĐ"

# ============ MAIN ============
def main():
    """Xử lý webhook"""
    update = json.loads(os.getenv("TELEGRAM_UPDATE", "{}"))
    
    if not update:
        print("Không có dữ liệu")
        return
    
    message = update.get("message", {})
    text = message.get("text", "")
    
    # Xử lý file PDF nếu có
    document = message.get("document")
    file_url = None
    if document:
        file_id = document.get("file_id")
        url_get_file = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
        resp = requests.get(url_get_file).json()
        if resp.get("ok"):
            file_path = resp["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
    
    # Xử lý nội dung
    if text and file_url:
        noi_dung_pdf = doc_noi_dung_pdf(file_url)
        if "thêm đến" in text.lower() or "them den" in text.lower():
            ket_qua = them_van_ban(noi_dung_pdf, "den", file_url)
        elif "thêm đi" in text.lower() or "them di" in text.lower():
            ket_qua = them_van_ban(noi_dung_pdf, "di", file_url)
        else:
            ket_qua = "❓ Gửi file PDF kèm 'thêm đến' hoặc 'thêm đi'"
    elif text:
        ket_qua = tra_cuu(text)
    else:
        ket_qua = "📌 Gửi file PDF kèm lệnh 'thêm đến' hoặc hỏi 'có bao nhiêu văn bản đến?'"
    
    gui_telegram(ket_qua)

if __name__ == "__main__":
    main()
