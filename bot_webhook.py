import os
import json
import logging
import requests
from datetime import datetime
from flask import Flask, request, jsonify

# ============================================================
# CẤU HÌNH
# ============================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GITHUB_REPO    = os.environ.get("GITHUB_REPO", "")   # vd: hoanloan1902/SKHCN
FILE_DA_GUI    = "da_gui.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)
app = Flask(__name__)


# ============================================================
# ĐỌC da_gui.json TỪ GITHUB PUBLIC (không cần token)
# ============================================================
def doc_du_lieu() -> list:
    try:
        # Dùng raw content — repo public không cần xác thực
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{FILE_DA_GUI}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        log.error(f"Lỗi đọc GitHub: {e}")
        return []


# ============================================================
# GỬI TELEGRAM
# ============================================================
def tra_loi(chat_id: int, msg: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        log.error(f"Lỗi gửi Telegram: {e}")


# ============================================================
# XỬ LÝ CÂU HỎI
# ============================================================
def xu_ly(chat_id: int, text: str):
    t = text.lower().strip()
    hom_nay = datetime.now().strftime("%d/%m/%Y")
    data = doc_du_lieu()
    la_dict = data and isinstance(data[0], dict)

    # --- Thống kê / bao nhiêu ---
    if any(k in t for k in ["bao nhiêu", "tổng số", "thống kê", "thong ke"]):
        tra_loi(chat_id, (
            f"📊 <b>THỐNG KÊ VĂN BẢN</b>\n"
            f"────────────────\n"
            f"✅ Tổng văn bản đã nhận: <b>{len(data)}</b>\n"
            f"⏰ Cập nhật: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ))

    # --- Hạn hôm nay ---
    elif any(k in t for k in ["hôm nay", "đến hạn", "hạn hôm", "den han"]):
        if la_dict:
            den_han = [d for d in data if d.get("han_xu_ly", "") == hom_nay]
            if den_han:
                msg = f"⏳ <b>ĐẾN HẠN HÔM NAY — {hom_nay}</b>\n────────────────\n"
                for d in den_han[:10]:
                    msg += (
                        f"📌 <code>{d.get('so_cv','?')}</code>\n"
                        f"   📝 {d.get('trich_yeu','')[:100]}\n\n"
                    )
                if len(den_han) > 10:
                    msg += f"...và {len(den_han)-10} văn bản khác."
            else:
                msg = f"✅ Không có văn bản nào đến hạn hôm nay ({hom_nay})."
            tra_loi(chat_id, msg)
        else:
            tra_loi(chat_id, (
                f"ℹ️ Dữ liệu chưa đủ để lọc theo hạn.\n"
                f"Hiện có <b>{len(data)}</b> văn bản đã ghi nhận."
            ))

    # --- Danh sách mới nhất ---
    elif any(k in t for k in ["danh sách", "mới nhất", "gần nhất", "danh sach"]):
        if la_dict:
            gan_nhat = list(reversed(data[-5:]))
            msg = f"📋 <b>5 VĂN BẢN MỚI NHẤT</b>\n────────────────\n"
            for d in gan_nhat:
                msg += (
                    f"📌 <code>{d.get('so_cv','?')}</code> — {d.get('ngay_den','')}\n"
                    f"   📝 {d.get('trich_yeu','')[:80]}\n"
                    f"   ⏳ Hạn: <b>{d.get('han_xu_ly','?')}</b>\n\n"
                )
            tra_loi(chat_id, msg)
        else:
            tra_loi(chat_id, f"📋 Đã ghi nhận <b>{len(data)}</b> văn bản.")

    # --- Help ---
    elif any(k in t for k in ["/start", "/help", "giúp", "hướng dẫn", "lệnh"]):
        tra_loi(chat_id, (
            "🤖 <b>HƯỚNG DẪN SỬ DỤNG</b>\n"
            "────────────────\n"
            "📊 Thống kê tổng số:\n"
            "   → <i>bao nhiêu văn bản</i>\n\n"
            "⏳ Văn bản đến hạn hôm nay:\n"
            "   → <i>hạn hôm nay</i>\n\n"
            "📋 Danh sách mới nhất:\n"
            "   → <i>danh sách mới nhất</i>"
        ))

    else:
        tra_loi(chat_id, "❓ Mình chưa hiểu. Gõ /help để xem hướng dẫn.")


# ============================================================
# WEBHOOK
# ============================================================
@app.route(f"/webhook/<token>", methods=["POST"])
def webhook(token):
    if token != TELEGRAM_TOKEN:
        return jsonify({"ok": False}), 403
    try:
        update = request.get_json()
        msg = update.get("message") or update.get("edited_message")
        if msg and msg.get("text"):
            chat_id = msg["chat"]["id"]
            log.info(f"Tin từ {chat_id}: {msg['text'][:60]}")
            xu_ly(chat_id, msg["text"])
    except Exception as e:
        log.error(f"Lỗi webhook: {e}", exc_info=True)
    return jsonify({"ok": True})


@app.route("/", methods=["GET"])
def health():
    return "Bot đang chạy ✅", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
