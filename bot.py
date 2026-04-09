import os
import re
import json
import requests
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import PyPDF2
from io import BytesIO

# ============ CẤU HÌNH ============
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Google Sheets - Tên file là "VanBan"
SHEET_NAME = "VanBan"
SERVICE_ACCOUNT = json.loads(os.getenv("GSPREAD_SERVICE_ACCOUNT"))

# ============ KẾT NỐI GOOGLE SHEETS ============
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT, scope)
client = gspread.authorize(creds)

# Mở sheet "VanBan" và lấy 2 worksheet
spreadsheet = client.open(SHEET_NAME)
sheet_den = spreadsheet.worksheet("VB_Den")
sheet_di = spreadsheet.worksheet("VB_Di")

# ============ HÀM GỬI TIN NHẮN TELEGRAM ============
def gui_telegram(noi_dung):
    """Gửi tin nhắn qua Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": noi_dung,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Lỗi gửi Telegram: {e}")

# ============ ĐỌC NỘI DUNG PDF ============
def doc_noi_dung_pdf(url_pdf):
    """Đọc nội dung từ file PDF qua URL"""
    try:
        response = requests.get(url_pdf, timeout=30)
        pdf_file = BytesIO(response.content)
        reader = PyPDF2.PdfReader(pdf_file)
        noi_dung = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                noi_dung += text
        return noi_dung
    except Exception as e:
        print(f"Lỗi đọc PDF: {e}")
        return ""

# ============ TRÍCH XUẤT THÔNG TIN ============
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
        r'(?:Nội dung|Công văn về)[:\s]+([^\n]{10,200})'
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
                if len(match_han.groups()) == 3 and match_han.group(2):
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

# ============ TÍNH NGÀY CÒN LẠI ============
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
def them_van_ban_den(noi_dung_pdf, file_url=""):
    """Thêm văn bản đến vào Google Sheet"""
    
    # Trích xuất thông tin
    info = trich_xuat_thong_tin(noi_dung_pdf, "den")
    
    if not info["so_hieu"]:
        return "❌ Không tìm thấy số hiệu trong văn bản"
    
    # Kiểm tra trùng lặp
    try:
        existing = sheet_den.col_values(2)  # Cột B (Số hiệu)
        if info["so_hieu"] in existing:
            return f"⚠️ Văn bản {info['so_hieu']} đã tồn tại trong sheet VB_Den"
    except:
        pass
    
    # Tính số ngày còn lại
    con_lai = tinh_ngay_con_lai(info["han_xu_ly"])
    
    # Lấy ID mới
    try:
        all_rows = sheet_den.get_all_values()
        new_id = len(all_rows) if len(all_rows) > 1 else 1
    except:
        new_id = 1
    
    # Thêm dòng mới
    dong_moi = [
        new_id,                                    # ID
        info["so_hieu"],                          # Số hiệu
        datetime.now().strftime('%d/%m/%Y'),      # Ngày đến
        info["trich_yeu"],                        # Trích yếu
        info["han_xu_ly"] or "Không có hạn",      # Hạn xử lý
        str(con_lai) if con_lai != "" else "",    # Còn lại (ngày)
        file_url,                                 # File PDF
        "",                                       # File kèm
        datetime.now().strftime('%d/%m/%Y %H:%M') # Ngày nhập
    ]
    
    sheet_den.append_row(dong_moi)
    
    # Tạo thông báo
    tb = f"✅ Đã thêm văn bản ĐẾN: {info['so_hieu']}\n"
    tb += f"📝 {info['trich_yeu'][:100]}\n"
    if info["han_xu_ly"]:
        tb += f"⏰ Hạn xử lý: {info['han_xu_ly']} (còn {con_lai} ngày)"
    else:
        tb += f"📅 Không có hạn xử lý"
    return tb

def them_van_ban_di(noi_dung_pdf, file_url=""):
    """Thêm văn bản đi vào Google Sheet"""
    
    # Trích xuất thông tin
    info = trich_xuat_thong_tin(noi_dung_pdf, "di")
    
    if not info["so_hieu"]:
        return "❌ Không tìm thấy số hiệu trong văn bản"
    
    # Kiểm tra trùng lặp
    try:
        existing = sheet_di.col_values(2)  # Cột B (Số hiệu)
        if info["so_hieu"] in existing:
            return f"⚠️ Văn bản {info['so_hieu']} đã tồn tại trong sheet VB_Di"
    except:
        pass
    
    # Lấy ID mới
    try:
        all_rows = sheet_di.get_all_values()
        new_id = len(all_rows) if len(all_rows) > 1 else 1
    except:
        new_id = 1
    
    # Thêm dòng mới
    dong_moi = [
        new_id,                                    # ID
        info["so_hieu"],                          # Số hiệu
        datetime.now().strftime('%d/%m/%Y'),      # Ngày đi
        info["trich_yeu"],                        # Trích yếu
        info["noi_nhan"],                         # Nơi nhận
        file_url,                                 # File PDF
        "",                                       # File kèm
        datetime.now().strftime('%d/%m/%Y %H:%M') # Ngày nhập
    ]
    
    sheet_di.append_row(dong_moi)
    
    # Tạo thông báo
    tb = f"✅ Đã thêm văn bản ĐI: {info['so_hieu']}\n"
    tb += f"📝 {info['trich_yeu'][:100]}\n"
    if info["noi_nhan"]:
        tb += f"📬 Nơi nhận: {info['noi_nhan']}"
    return tb

# ============ TRUY VẤN ============
def tra_cuu(cau_hoi):
    """Xử lý câu hỏi từ người dùng"""
    cau_hoi = cau_hoi.lower().strip()
    
    # Lấy tất cả dữ liệu từ sheet VB_Den
    try:
        data_den = sheet_den.get_all_values()
        if len(data_den) > 1:
            data_den = data_den[1:]  # Bỏ header
        else:
            data_den = []
    except:
        data_den = []
    
    # 1. Tổng số văn bản đến
    if "bao nhiêu" in cau_hoi and ("vb đến" in cau_hoi or "văn bản đến" in cau_hoi):
        return f"📊 Tổng số văn bản đến: {len(data_den)}"
    
    # 2. Hôm nay có bao nhiêu
    if "hôm nay" in cau_hoi:
        hom_nay = datetime.now().strftime('%d/%m/%Y')
        count = sum(1 for row in data_den if len(row) > 2 and row[2] == hom_nay)
        return f"📅 Hôm nay ({hom_nay}) có {count} văn bản đến"
    
    # 3. Văn bản có hạn
    if "có hạn" in cau_hoi and "không" not in cau_hoi:
        vb_han = [row for row in data_den if len(row) > 4 and row[4] != "Không có hạn"]
        if not vb_han:
            return "📭 Không có văn bản nào có hạn xử lý"
        
        ket_qua = f"📋 Có {len(vb_han)} văn bản có hạn:\n\n"
        for row in vb_han[:10]:
            ket_qua += f"📄 {row[1]} - Hạn: {row[4]}\n"
            ket_qua += f"   {row[3][:60]}\n\n"
        return ket_qua
    
    # 4. Văn bản sắp hết hạn (còn <= 5 ngày)
    if "sắp hết hạn" in cau_hoi or "gần hết hạn" in cau_hoi:
        vb_sap_het = []
        for row in data_den:
            if len(row) > 5 and row[5] and str(row[5]).replace('-', '').isdigit():
                try:
                    con_lai = int(row[5])
                    if con_lai <= 5 and con_lai >= 0:
                        vb_sap_het.append(row)
                except:
                    pass
        
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
        ket_qua_den = []
        for row in data_den:
            if len(row) > 1 and (tu_khoa in row[1].lower() or tu_khoa in row[3].lower()):
                ket_qua_den.append(row)
        
        if ket_qua_den:
            ket_qua = f"🔍 Tìm thấy {len(ket_qua_den)} văn bản:\n\n"
            for row in ket_qua_den[:5]:
                ket_qua += f"📄 {row[1]} - {row[2]}\n"
                ket_qua += f"   {row[3][:60]}\n\n"
            return ket_qua
        else:
            return f"🔍 Không tìm thấy văn bản nào về '{tu_khoa}'"
    
    # 6. Thống kê theo tháng
    if "tháng" in cau_hoi:
        match_thang = re.search(r'tháng\s+(\d+)', cau_hoi)
        if match_thang:
            thang = match_thang.group(1).zfill(2)
            nam = datetime.now().year
            count = 0
            for row in data_den:
                if len(row) > 2 and f"/{thang}/{nam}" in row[2]:
                    count += 1
            return f"📊 Tháng {thang}/{nam} có {count} văn bản đến"
    
    # 7. Danh sách văn bản đi (nếu hỏi)
    if "văn bản đi" in cau_hoi and "bao nhiêu" in cau_hoi:
        try:
            data_di = sheet_di.get_all_values()
            count = len(data_di) - 1 if len(data_di) > 1 else 0
            return f"📊 Tổng số văn bản đi: {count}"
        except:
            return "📊 Tổng số văn bản đi: 0"
    
    return """❓ Hãy thử hỏi:
- Có bao nhiêu văn bản đến?
- Hôm nay có mấy văn bản?
- Văn bản nào có hạn?
- Văn bản nào sắp hết hạn?
- Tìm 123/QĐ
- Thống kê tháng 3"""

# ============ MAIN ============
def main():
    """Xử lý webhook từ Telegram"""
    update = json.loads(os.getenv("TELEGRAM_UPDATE", "{}"))
    
    if not update:
        print("Không có dữ liệu webhook")
        return
    
    message = update.get("message", {})
    if not message:
        print("Không có tin nhắn")
        return
    
    text = message.get("text", "")
    
    # Xử lý file PDF nếu có
    document = message.get("document")
    file_url = None
    
    if document:
        file_id = document.get("file_id")
        file_name = document.get("file_name", "")
        
        # Chỉ xử lý file PDF
        if file_name.lower().endswith('.pdf'):
            url_get_file = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
            resp = requests.get(url_get_file).json()
            
            if resp.get("ok"):
                file_path = resp["result"]["file_path"]
                file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
    
    # Xử lý nội dung
    if text and file_url:
        # Có file PDF kèm theo
        noi_dung_pdf = doc_noi_dung_pdf(file_url)
        
        if "thêm đến" in text.lower() or "them den" in text.lower():
            ket_qua = them_van_ban_den(noi_dung_pdf, file_url)
        elif "thêm đi" in text.lower() or "them di" in text.lower():
            ket_qua = them_van_ban_di(noi_dung_pdf, file_url)
        else:
            ket_qua = "❌ Vui lòng gõ 'thêm đến' hoặc 'thêm đi' kèm file PDF"
    
    elif text:
        # Câu hỏi bình thường
        ket_qua = tra_cuu(text)
    
    else:
        ket_qua = "📌 Gửi file PDF kèm lệnh 'thêm đến' hoặc 'thêm đi'\nHoặc hỏi: 'có bao nhiêu văn bản đến?'"
    
    # Gửi kết quả về Telegram
    gui_telegram(ket_qua)
    print(f"Đã gửi phản hồi: {ket_qua[:100]}...")

# ============ CHẠY ============
if __name__ == "__main__":
    main()
