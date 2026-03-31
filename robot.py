from datetime import datetime

def loc_van_ban_thong_minh(text, data_rows):
    today = datetime.now().strftime("%d/%m/%Y")
    txt = text.lower()
    
    # --- 1. Lọc theo thời gian (Hôm nay/Sáng nay) ---
    if any(k in txt for k in ["hôm nay", "sáng nay", "mới về"]):
        results = [r for r in data_rows if today in r[1]] # r[1] là cột Ngày đến
        if not results: return "Sáng nay chưa có văn bản mới nào về hệ thống anh ạ."
        msg = f"📅 **Sáng nay có {len(results)} văn bản mới:**\n"
        for r in results: msg += f"• {r[0]}: {r[2][:80]}...\n"
        return msg

    # --- 2. Lọc xử lý GẤP (Check từ khóa mạnh) ---
    if any(k in txt for k in ["gấp", "khẩn", "hỏa tốc"]):
        keywords_gap = ["hỏa tốc", "khẩn", "gấp", "hạn", "trước ngày"]
        results = [r for r in data_rows if any(k in r[2].lower() for k in keywords_gap)]
        if not results: return "Hiện em không thấy văn bản nào ghi chú xử lý gấp anh nhé."
        msg = "🚨 **DANH SÁCH XỬ LÝ GẤP:**\n"
        for r in results: msg += f"⚠️ {r[0]}: {r[2][:100]}\n"
        return msg

    # --- 3. Thống kê chưa xử lý ---
    if "chưa xử lý" in txt or "tồn" in txt:
        # Giả định cột r[3] là trạng thái, nếu chưa có mình check theo logic riêng
        results = [r for r in data_rows if "chờ xử lý" in r[2].lower() or "chưa" in r[2].lower()]
        return f"⏳ Anh còn khoảng **{len(results)}** văn bản đang ở trạng thái chờ xử lý ạ."

    return "🤖 Em đang nghe đây anh Hoàn! Anh muốn lọc theo giờ, theo độ khẩn hay kiểm tra việc tồn đọng ạ?"
