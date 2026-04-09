import os
import re
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import PyPDF2
from io import BytesIO

# ============ CẤU HÌNH ============
EXCEL_FILE = "van_ban.xlsx"
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def gui_telegram(noi_dung):
    """Gửi tin nhắn qua Telegram"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": noi_dung,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Lỗi gửi Telegram: {e}")

def doc_noi_dung_pdf(url_pdf):
    """Đọc PDF từ URL (file gửi qua Telegram)"""
    try:
        response = requests.get(url_pdf, timeout=30)
        pdf_file = BytesIO(response.content)
        reader = PyPDF2.PdfReader(pdf_file)
        noi_dung = ""
        for page in reader.pages:
            noi_dung += page.extract_text()
        return noi_dung
    except Exception as e:
        return f""

def trich_xuat_van_ban(noi_dung, loai="den"):
    """Trích xuất thông tin từ nội dung"""
    ket_qua = {"so_hieu": "", "trich_yeu": "", "han_xu_ly": None, "noi_nhan": ""}
    
    # Tìm số hiệu
    match = re.search(r'(\d+/[A-Z0-9\-\/]+)', noi_dung)
    if match:
        ket_qua["so_hieu"] = match.group(1)
    
    # Tìm trích yếu
    match = re.search(r'(?:Trích yếu|V/v|Về việc)[:\s]+([^\n]{10,200})', noi_dung, re.IGNORECASE)
    if match:
        ket_qua["trich_yeu"] = match.group(1).strip()
    
    # Tìm hạn (cho văn bản đến)
    if loai == "den":
        patterns = [
            r'(?:hạn|hạn xử lý|thời hạn|deadline|chậm nhất|trước ngày)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})'
        ]
        for pattern in patterns:
            match = re.search(pattern, noi_dung, re.IGNORECASE)
            if match:
                if len(match.groups()) == 3:
                    ngay = match.group(1).zfill(2)
                    thang = match.group(2).zfill(2)
                    nam = match.group(3)
                    ket_qua["han_xu_ly"] = f"{ngay}/{thang}/{nam}"
                else:
                    ket_qua["han_xu_ly"] = match.group(1).replace('-', '/')
                break
    
    # Tìm nơi nhận (cho văn bản đi)
    if loai == "di":
        match = re.search(r'(?:Gửi|Đến|Kính gửi)[:\s]+([^\n]+)', noi_dung, re.IGNORECASE)
        if match:
            ket_qua["noi_nhan"] = match.group(1).strip()
    
    return ket_qua

def them_van_ban(noi_dung_pdf, loai="den"):
    """Thêm văn bản vào Excel"""
    # Đọc file Excel hiện tại
    if not os.path.exists(EXCEL_FILE):
        khoi_tao_excel()
    
    df_den = pd.read_excel(EXCEL_FILE, sheet_name='VB_Den')
    df_di = pd.read_excel(EXCEL_FILE, sheet_name='VB_Di')
    
    # Trích xuất thông tin
    thong_tin = trich_xuat_van_ban(noi_dung_pdf, loai)
    
    if not thong_tin["so_hieu"]:
        return f"❌ Không tìm thấy số hiệu trong văn bản {loai}"
    
    # Kiểm tra trùng
    if loai == "den":
        if thong_tin["so_hieu"] in df_den['So_hieu'].values:
            return f"⚠️ Văn bản {thong_tin['so_hieu']} đã tồn tại"
        
        # Tính số ngày còn lại
        con_lai = ""
        if thong_tin["han_xu_ly"]:
            try:
                ngay_han = datetime.strptime(thong_tin["han_xu_ly"], '%d/%m/%Y')
                con_lai = (ngay_han - datetime.now()).days
            except:
                con_lai = ""
        
        # Thêm mới
        dong_moi = {
            'ID': len(df_den) + 1,
            'So_hieu': thong_tin["so_hieu"],
            'Ngay_den': datetime.now().strftime('%d/%m/%Y'),
            'Trich_yeu': thong_tin["trich_yeu"][:150],
            'Han_xu_ly': thong_tin["han_xu_ly"] or "Không có hạn",
            'Con_lai_ngay': con_lai if con_lai != "" else "",
            'File_PDF': "",
            'File_kem': "",
            'Ngay_nhap': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        df_den = pd.concat([df_den, pd.DataFrame([dong_moi])], ignore_index=True)
        
        # Ghi lại Excel
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl') as writer:
            df_den.to_excel(writer, sheet_name='VB_Den', index=False)
            df_di.to_excel(writer, sheet_name='VB_Di', index=False)
        
        # Tạo thông báo
        tb = f"✅ Đã thêm văn bản ĐẾN: {thong_tin['so_hieu']}\n"
        tb += f"📝 {thong_tin['trich_yeu'][:100]}\n"
        if thong_tin["han_xu_ly"]:
            tb += f"⏰ Hạn xử lý: {thong_tin['han_xu_ly']} (còn {con_lai} ngày)"
        else:
            tb += f"📅 Không có hạn xử lý"
        return tb
    
    else:  # Văn bản đi
        if thong_tin["so_hieu"] in df_di['So_hieu'].values:
            return f"⚠️ Văn bản {thong_tin['so_hieu']} đã tồn tại"
        
        dong_moi = {
            'ID': len(df_di) + 1,
            'So_hieu': thong_tin["so_hieu"],
            'Ngay_di': datetime.now().strftime('%d/%m/%Y'),
            'Trich_yeu': thong_tin["trich_yeu"][:150],
            'Noi_nhan': thong_tin["noi_nhan"],
            'File_PDF': "",
            'File_kem': "",
            'Ngay_nhap': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        df_di = pd.concat([df_di, pd.DataFrame([dong_moi])], ignore_index=True)
        
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl') as writer:
            df_den.to_excel(writer, sheet_name='VB_Den', index=False)
            df_di.to_excel(writer, sheet_name='VB_Di', index=False)
        
        tb = f"✅ Đã thêm văn bản ĐI: {thong_tin['so_hieu']}\n"
        tb += f"📝 {thong_tin['trich_yeu'][:100]}\n"
        if thong_tin["noi_nhan"]:
            tb += f"📬 Gửi: {thong_tin['noi_nhan']}"
        return tb

def tra_cuu(cau_hoi):
    """Xử lý câu hỏi tự nhiên"""
    cau_hoi = cau_hoi.lower()
    df_den = pd.read_excel(EXCEL_FILE, sheet_name='VB_Den')
    df_di = pd.read_excel(EXCEL_FILE, sheet_name='VB_Di')
    
    # Tổng số văn bản đến
    if "bao nhiêu" in cau_hoi and ("vb đến" in cau_hoi or "văn bản đến" in cau_hoi):
        return f"📊 Tổng số văn bản đến: {len(df_den)}"
    
    # Hôm nay
    if "hôm nay" in cau_hoi:
        hom_nay = datetime.now().strftime('%d/%m/%Y')
        sl = len(df_den[df_den['Ngay_den'] == hom_nay])
        return f"📅 Hôm nay ({hom_nay}) có {sl} văn bản đến"
    
    # Văn bản có hạn
    if "có hạn" in cau_hoi:
        vb_han = df_den[df_den['Han_xu_ly'] != "Không có hạn"]
        if len(vb_han) == 0:
            return "📭 Không có văn bản nào có hạn xử lý"
        
        ket_qua = f"📋 Có {len(vb_han)} văn bản có hạn:\n\n"
        for _, row in vb_han.head(10).iterrows():
            ket_qua += f"📄 {row['So_hieu']} - Hạn: {row['Han_xu_ly']}\n"
            ket_qua += f"   {row['Trich_yeu'][:60]}\n\n"
        return ket_qua
    
    # Sắp hết hạn
    if "sắp hết hạn" in cau_hoi or "gần hết hạn" in cau_hoi:
        vb_han = df_den[df_den['Han_xu_ly'] != "Không có hạn"].copy()
        vb_han['Con_lai_ngay'] = pd.to_numeric(vb_han['Con_lai_ngay'], errors='coerce')
        vb_sap_het = vb_han[vb_han['Con_lai_ngay'] <= 5].sort_values('Con_lai_ngay')
        
        if len(vb_sap_het) == 0:
            return "🎉 Không có văn bản nào sắp hết hạn trong 5 ngày tới"
        
        ket_qua = f"⚠️ {len(vb_sap_het)} văn bản sắp hết hạn:\n\n"
        for _, row in vb_sap_het.iterrows():
            ket_qua += f"🔴 {row['So_hieu']} - Còn {int(row['Con_lai_ngay'])} ngày\n"
            ket_qua += f"   Hạn: {row['Han_xu_ly']}\n\n"
        return ket_qua
    
    # Tìm kiếm
    if "tìm" in cau_hoi or "tra" in cau_hoi:
        tu_khoa = re.sub(r'(tìm|tra|kiếm|văn bản|công văn|số)', '', cau_hoi).strip()
        
        ket_qua_den = df_den[df_den['So_hieu'].str.contains(tu_khoa, case=False, na=False) | 
                             df_den['Trich_yeu'].str.contains(tu_khoa, case=False, na=False)]
        
        if len(ket_qua_den) == 0:
            return f"🔍 Không tìm thấy văn bản nào về '{tu_khoa}'"
        
        ket_qua = f"🔍 Tìm thấy {len(ket_qua_den)} văn bản:\n\n"
        for _, row in ket_qua_den.head(5).iterrows():
            ket_qua += f"📄 {row['So_hieu']} - {row['Ngay_den']}\n"
            ket_qua += f"   {row['Trich_yeu'][:60]}\n\n"
        return ket_qua
    
    return "❓ Hãy hỏi: 'có bao nhiêu vb đến?', 'hôm nay?', 'văn bản có hạn?', 'tìm 123'"

def khoi_tao_excel():
    """Tạo file Excel mới"""
    with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl') as writer:
        df_den = pd.DataFrame(columns=[
            'ID', 'So_hieu', 'Ngay_den', 'Trich_yeu', 
            'Han_xu_ly', 'Con_lai_ngay', 'File_PDF', 'File_kem', 'Ngay_nhap'
        ])
        df_di = pd.DataFrame(columns=[
            'ID', 'So_hieu', 'Ngay_di', 'Trich_yeu', 
            'Noi_nhan', 'File_PDF', 'File_kem', 'Ngay_nhap'
        ])
        df_den.to_excel(writer, sheet_name='VB_Den', index=False)
        df_di.to_excel(writer, sheet_name='VB_Di', index=False)

# ============ MAIN ============
def main():
    """Xử lý webhook từ Telegram"""
    # Lấy dữ liệu từ webhook (đọc từ stdin hoặc biến môi trường)
    update = json.loads(os.getenv("TELEGRAM_UPDATE", "{}"))
    
    if not update:
        print("Không có dữ liệu")
        return
    
    # Lấy tin nhắn
    message = update.get("message", {})
    text = message.get("text", "")
    chat_id = message.get("chat", {}).get("id")
    
    # Lấy file nếu có
    document = message.get("document")
    file_url = None
    if document:
        file_id = document.get("file_id")
        # Lấy file từ Telegram
        url_get_file = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
        resp = requests.get(url_get_file).json()
        if resp.get("ok"):
            file_path = resp["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    
    # Xử lý
    if text and file_url:
        # Có file PDF đính kèm
        noi_dung_pdf = doc_noi_dung_pdf(file_url)
        if "thêm đến" in text.lower() or "them den" in text.lower():
            ket_qua = them_van_ban(noi_dung_pdf, "den")
        elif "thêm đi" in text.lower() or "them di" in text.lower():
            ket_qua = them_van_ban(noi_dung_pdf, "di")
        else:
            ket_qua = "❓ Vui lòng gõ 'thêm đến' hoặc 'thêm đi' kèm file PDF"
    elif text:
        # Câu hỏi bình thường
        ket_qua = tra_cuu(text)
    else:
        ket_qua = "📌 Gửi file PDF kèm lệnh 'thêm đến' hoặc hỏi 'có bao nhiêu văn bản đến?'"
    
    # Gửi kết quả
    gui_telegram(ket_qua)

if __name__ == "__main__":
    main()
