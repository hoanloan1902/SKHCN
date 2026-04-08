#!/usr/bin/env python3
"""
Bot Telegram trả lời tin nhắn thông minh
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict
import telebot

TOKEN = os.environ.get("TELEGRAM_TOKEN")
DA_GUI_FILE = "da_gui.json"

if not TOKEN:
    print("❌ Thiếu TELEGRAM_TOKEN")
    exit(1)

bot = telebot.TeleBot(TOKEN)

def load_danh_sach_chi_tiet() -> List[Dict]:
    """Đọc danh sách chi tiết văn bản từ JSON"""
    if os.path.exists(DA_GUI_FILE):
        try:
            with open(DA_GUI_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('danh_sach_chi_tiet', [])
        except:
            pass
    return []

def thong_ke_theo_ngay(ngay: datetime) -> str:
    """Thống kê văn bản theo ngày cụ thể"""
    danh_sach = load_danh_sach_chi_tiet()
    ngay_str = ngay.strftime('%d/%m/%Y')
    
    vb_trong_ngay = [vb for vb in danh_sach if vb.get('ngay') == ngay_str]
    
    if not vb_trong_ngay:
        return f"📭 Không có văn bản nào ngày {ngay_str}"
    
    vb_trong_ngay.sort(key=lambda x: x.get('so_hieu', ''))
    
    msg = f"📊 *THỐNG KÊ NGÀY {ngay_str}*\n"
    msg += f"Tổng số: {len(vb_trong_ngay)} văn bản\n\n"
    
    for i, vb in enumerate(vb_trong_ngay[:15], 1):
        msg += f"{i}. `{vb['so_hieu']}`\n"
        msg += f"   🏢 {vb['co_quan']}\n"
        msg += f"   📝 {vb['trich_yeu'][:80]}...\n"
        
        if vb.get('han_xu_ly') and vb['han_xu_ly'] != "Không có hạn":
            ngay_con = vb.get('ngay_con_lai', 999)
            if ngay_con < 0:
                msg += f"   ⚠️ *QUÁ HẠN {abs(ngay_con)} ngày*\n"
            elif ngay_con == 0:
                msg += f"   🔴 *HẾT HẠN HÔM NAY*\n"
            elif ngay_con <= 3:
                msg += f"   🟡 *Còn {ngay_con} ngày*\n"
            else:
                msg += f"   📅 Hạn: {vb['han_xu_ly']}\n"
        msg += "\n"
    
    if len(vb_trong_ngay) > 15:
        msg += f"... và {len(vb_trong_ngay) - 15} văn bản khác\n"
        msg += f"📌 Gõ /list_all để xem toàn bộ"
    
    return msg

def thong_ke_theo_tuan() -> str:
    """Thống kê văn bản trong tuần này"""
    danh_sach = load_danh_sach_chi_tiet()
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    
    vb_trong_tuan = []
    for vb in danh_sach:
        try:
            ngay = datetime.strptime(vb.get('ngay', ''), '%d/%m/%Y')
            if ngay >= start_of_week:
                vb_trong_tuan.append(vb)
        except:
            continue
    
    if not vb_trong_tuan:
        return "📭 Không có văn bản nào trong tuần này"
    
    theo_ngay = {}
    for vb in vb_trong_tuan:
        ngay = vb.get('ngay', '')
        if ngay not in theo_ngay:
            theo_ngay[ngay] = []
        theo_ngay[ngay].append(vb)
    
    msg = f"📊 *THỐNG KÊ TUẦN NÀY*\n"
    msg += f"Tổng số: {len(vb_trong_tuan)} văn bản\n\n"
    
    for ngay in sorted(theo_ngay.keys()):
        msg += f"📅 *{ngay}*: {len(theo_ngay[ngay])} văn bản\n"
    
    return msg

def thong_ke_theo_thang() -> str:
    """Thống kê văn bản trong tháng này"""
    danh_sach = load_danh_sach_chi_tiet()
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    vb_trong_thang = []
    for vb in danh_sach:
        try:
            ngay = datetime.strptime(vb.get('ngay', ''), '%d/%m/%Y')
            if ngay.month == current_month and ngay.year == current_year:
                vb_trong_thang.append(vb)
        except:
            continue
    
    if not vb_trong_thang:
        return f"📭 Không có văn bản nào trong tháng {current_month}/{current_year}"
    
    theo_ngay = {}
    for vb in vb_trong_thang:
        ngay = vb.get('ngay', '')
        if ngay not in theo_ngay:
            theo_ngay[ngay] = []
        theo_ngay[ngay].append(vb)
    
    msg = f"📊 *THỐNG KÊ THÁNG {current_month}/{current_year}*\n"
    msg += f"Tổng số: {len(vb_trong_thang)} văn bản\n"
    msg += f"Số ngày có văn bản: {len(theo_ngay)} ngày\n\n"
    
    top_ngay = sorted(theo_ngay.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    msg += "*Top ngày có nhiều văn bản:*\n"
    for ngay, list_vb in top_ngay:
        msg += f"   📅 {ngay}: {len(list_vb)} văn bản\n"
    
    return msg

def danh_sach_sap_het_han() -> str:
    """Liệt kê các văn bản sắp hết hạn"""
    danh_sach = load_danh_sach_chi_tiet()
    
    qua_han = [vb for vb in danh_sach if vb.get('ngay_con_lai', 999) < 0]
    het_han_hom_nay = [vb for vb in danh_sach if vb.get('ngay_con_lai', 999) == 0]
    sap_het_han = [vb for vb in danh_sach if 0 < vb.get('ngay_con_lai', 999) <= 3]
    
    if not qua_han and not het_han_hom_nay and not sap_het_han:
        return "✅ Không có văn bản nào sắp hết hạn trong 3 ngày tới"
    
    msg = f"⚠️ *CẢNH BÁO HẠN XỬ LÝ VĂN BẢN*\n\n"
    
    if qua_han:
        msg += f"🔴 *QUÁ HẠN XỬ LÝ:* {len(qua_han)} văn bản\n"
        for vb in sorted(qua_han, key=lambda x: x.get('ngay_con_lai', 0))[:10]:
            msg += f"   • `{vb['so_hieu']}` - Quá hạn {abs(vb['ngay_con_lai'])} ngày\n"
            msg += f"     🏢 {vb['co_quan']}\n"
        msg += "\n"
    
    if het_han_hom_nay:
        msg += f"🔴 *HẾT HẠN HÔM NAY:* {len(het_han_hom_nay)} văn bản\n"
        for vb in het_han_hom_nay[:10]:
            msg += f"   • `{vb['so_hieu']}` - {vb['co_quan']}\n"
        msg += "\n"
    
    if sap_het_han:
        msg += f"🟡 *SẮP HẾT HẠN (3 ngày tới):* {len(sap_het_han)} văn bản\n"
        for vb in sorted(sap_het_han, key=lambda x: x.get('ngay_con_lai', 0))[:10]:
            msg += f"   • `{vb['so_hieu']}` - Còn {vb['ngay_con_lai']} ngày\n"
            msg += f"     📅 Hạn: {vb['han_xu_ly']}\n"
    
    return msg

def gui_tat_ca_van_ban(message):
    """Gửi toàn bộ danh sách văn bản"""
    danh_sach = load_danh_sach_chi_tiet()
    
    if not danh_sach:
        bot.reply_to(message, "📭 Chưa có dữ liệu văn bản nào")
        return
    
    try:
        danh_sach.sort(key=lambda x: datetime.strptime(x.get('ngay', '01/01/2000'), '%d/%m/%Y'), reverse=True)
    except:
        pass
    
    bot.send_message(message.chat.id, 
                     f"📋 *DANH SÁCH TOÀN BỘ VĂN BẢN* ({len(danh_sach)} cái)\n"
                     f"⏳ Đang gửi từng trang...",
                     parse_mode='Markdown')
    
    chunk_size = 15
    for i in range(0, len(danh_sach), chunk_size):
        chunk = danh_sach[i:i+chunk_size]
        msg = f"📄 *Trang {i//chunk_size + 1}* / { (len(danh_sach)-1)//chunk_size + 1}\n\n"
        
        for j, vb in enumerate(chunk, 1):
            ngay_con = vb.get('ngay_con_lai', 999)
            if ngay_con < 0:
                emoji = "🔴"
                warn = f" (QUÁ HẠN {abs(ngay_con)} ngày)"
            elif ngay_con == 0:
                emoji = "🔴"
                warn = " (HẾT HẠN HÔM NAY)"
            elif ngay_con <= 3:
                emoji = "🟡"
                warn = f" (Còn {ngay_con} ngày)"
            else:
                emoji = "📄"
                warn = ""
            
            msg += f"{emoji} *{vb['so_hieu']}*{warn}\n"
            msg += f"   📅 {vb['ngay']}"
            if vb.get('han_xu_ly') and vb['han_xu_ly'] != "Không có hạn":
                msg += f" | ⏰ Hạn: {vb['han_xu_ly']}\n"
            else:
                msg += f"\n"
            msg += f"   🏢 {vb['co_quan']}\n"
            msg += f"   📝 {vb['trich_yeu'][:80]}...\n\n"
        
        bot.send_message(message.chat.id, msg, parse_mode='Markdown')
    
    bot.send_message(message.chat.id, "✅ Đã gửi xong toàn bộ danh sách")

def thong_ke_tong_hop() -> str:
    """Thống kê tổng hợp hệ thống"""
    danh_sach = load_danh_sach_chi_tiet()
    
    if not danh_sach:
        return "📭 Chưa có dữ liệu"
    
    qua_han = len([vb for vb in danh_sach if vb.get('ngay_con_lai', 999) < 0])
    het_han_hom_nay = len([vb for vb in danh_sach if vb.get('ngay_con_lai', 999) == 0])
    sap_het_han = len([vb for vb in danh_sach if 0 < vb.get('ngay_con_lai', 999) <= 3])
    con_han = len([vb for vb in danh_sach if vb.get('ngay_con_lai', 999) > 3])
    khong_han = len([vb for vb in danh_sach if vb.get('han_xu_ly', 'Không có hạn') == 'Không có hạn'])
    
    last_update = "Chưa cập nhật"
    if os.path.exists(DA_GUI_FILE):
        try:
            with open(DA_GUI_FILE, 'r') as f:
                data = json.load(f)
                last_update = data.get('last_update', 'Chưa cập nhật')
        except:
            pass
    
    msg = f"📊 *THỐNG KÊ HỆ THỐNG HSCV*\n\n"
    msg += f"📋 Tổng số văn bản đang chờ: *{len(danh_sach)}*\n\n"
    msg += f"*PHÂN LOẠI THEO HẠN XỬ LÝ:*\n"
    msg += f"🔴 Quá hạn: {qua_han}\n"
    msg += f"🔴 Hết hạn hôm nay: {het_han_hom_nay}\n"
    msg += f"🟡 Sắp hết hạn (≤3 ngày): {sap_het_han}\n"
    msg += f"🟢 Còn hạn: {con_han}\n"
    msg += f"⚪ Không có hạn: {khong_han}\n\n"
    msg += f"🕐 Cập nhật lúc: {last_update[:16] if last_update != 'Chưa cập nhật' else last_update}"
    
    return msg

# ==================== TELEGRAM COMMANDS ====================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    msg = (
        "🤖 *BOT HSCV - QUẢN LÝ VĂN BẢN ĐẾN*\n\n"
        "*Các lệnh:*\n"
        "/stats - Xem thống kê tổng hợp\n"
        "/han - Xem danh sách văn bản sắp hết hạn\n"
        "/list_all - Xem toàn bộ danh sách văn bản\n\n"
        "*Hỏi bằng tiếng Việt:*\n"
        "• \"Có bao nhiêu văn bản đến hôm nay?\"\n"
        "• \"Thống kê tuần này\"\n"
        "• \"Văn bản nào sắp hết hạn?\"\n"
        "• \"Báo cáo tháng này\"\n\n"
        "📌 Dữ liệu được cập nhật tự động mỗi 30 phút"
    )
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def send_stats(message):
    msg = thong_ke_tong_hop()
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['han'])
def send_han(message):
    msg = danh_sach_sap_het_han()
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['list_all'])
def send_list_all(message):
    gui_tat_ca_van_ban(message)

@bot.message_handler(func=lambda m: True)
def smart_reply(message):
    text = message.text.lower()
    
    if "bao nhiêu" in text and ("văn bản" in text or "công văn" in text):
        if "hôm nay" in text:
            reply = thong_ke_theo_ngay(datetime.now())
        elif "hôm qua" in text:
            reply = thong_ke_theo_ngay(datetime.now() - timedelta(days=1))
        elif "tuần này" in text:
            reply = thong_ke_theo_tuan()
        elif "tháng này" in text:
            reply = thong_ke_theo_thang()
        else:
            reply = "📊 Vui lòng hỏi cụ thể: 'hôm nay', 'hôm qua', 'tuần này', 'tháng này'"
        
        bot.reply_to(message, reply, parse_mode='Markdown')
        return
    
    elif "hạn" in text and ("công văn" in text or "văn bản" in text or "sắp" in text):
        reply = danh_sach_sap_het_han()
        bot.reply_to(message, reply, parse_mode='Markdown')
        return
    
    elif "thống kê" in text or "tổng hợp" in text:
        reply = thong_ke_tong_hop()
        bot.reply_to(message, reply, parse_mode='Markdown')
        return
    
    elif "chào" in text or "hi" in text or "hello" in text:
        bot.reply_to(message, "Xin chào! Tôi là bot quản lý văn bản HSCV. Gõ /help để xem hướng dẫn.")
        return

if __name__ == "__main__":
    print("🤖 Bot đang chạy polling mode...")
    bot.infinity_polling()
