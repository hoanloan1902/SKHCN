import json
import re
from datetime import datetime, timedelta
from flask import Flask, request
import requests

app = Flask(__name__)

DATA_FILE = "da_guijson"
TOKEN = "YOUR_BOT_TOKEN"  # Sẽ được thay thế bằng biến môi trường
CHAT_ID = "YOUR_CHAT_ID"

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

def xu_ly_cau_hoi(cau_hoi):
    du_lieu = doc_du_lieu()
    danh_sach_vb = du_lieu.get("danh_sach_vb", [])
    cau_hoi = cau_hoi.lower().strip()
    
    if cau_hoi in ["thống kê", "/thongke"]:
        return bao_cao_ngay(danh_sach_vb)
    
    if "danh sách" in cau_hoi:
        return hien_thi_danh_sach(danh_sach_vb, cau_hoi)
    
    if "bao nhiêu" in cau_hoi or "mấy" in cau_hoi:
        return dem_van_ban(danh_sach_vb, cau_hoi)
    
    if cau_hoi == "sáng nay":
        return dem_van_ban(danh_sach_vb, "sáng nay có bao nhiêu")
    if cau_hoi == "hôm nay":
        return dem_van_ban(danh_sach_vb, "hôm nay có bao nhiêu")
    if cau_hoi == "hôm qua":
        return dem_van_ban(danh_sach_vb, "hôm qua có bao nhiêu")
    
    return "❓ Tôi chưa hiểu. Bạn có thể hỏi:\n- thống kê\n- sáng nay\n- hôm nay\n- danh sách hôm nay"

def hien_thi_danh_sach(danh_sach, cau_hoi):
    if "sáng nay" in cau_hoi:
        ds_loc = loc_theo_khung_gio(danh_sach, "sáng")
        tieu_de = "☀️ DANH SÁCH SÁNG NAY"
    elif "hôm nay" in cau_hoi:
        ngay_hom_nay = datetime.now().strftime("%d/%m/%Y")
        ds_loc = loc_theo_ngay(danh_sach, ngay_hom_nay)
        tieu_de = f"📋 DANH SÁCH HÔM NAY ({ngay_hom_nay})"
    else:
        return "❓ Hãy nói: 'danh sách sáng nay' hoặc 'danh sách hôm nay'"
    
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
        return f"☀️ Sáng nay có {len(loc_theo_khung_gio(danh_sach, 'sáng'))} văn bản."
    if "hôm nay" in cau_hoi:
        ngay_hom_nay = datetime.now().strftime("%d/%m/%Y")
        return f"📅 Hôm nay ({ngay_hom_nay}) có {len(loc_theo_ngay(danh_sach, ngay_hom_nay))} văn bản."
    if "hôm qua" in cau_hoi:
        ngay_hom_qua = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
        return f"📅 Hôm qua ({ngay_hom_qua}) có {len(loc_theo_ngay(danh_sach, ngay_hom_qua))} văn bản."
    return None

def bao_cao_ngay(danh_sach):
    ngay_hom_nay = datetime.now().strftime("%d/%m/%Y")
    ds_hom_nay = loc_theo_ngay(danh_sach, ngay_hom_nay)
    sang = len(loc_theo_khung_gio(ds_hom_nay, "sáng"))
    chieu = len(loc_theo_khung_gio(ds_hom_nay, "chiều"))
    return f"📊 {ngay_hom_nay}\n☀️ Sáng: {sang}\n🌤️ Chiều: {chieu}\n📌 Tổng: {len(ds_hom_nay)}"

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')
        reply = xu_ly_cau_hoi(text)
        send_message(chat_id, reply)
    return 'OK', 200

@app.route('/')
def index():
    return 'Bot is running!'

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(e)

if __name__ == '__main__':
    import os
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("CHAT_ID")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
