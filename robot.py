def quet_lotus_v18():
    url_login = "https://hscvkhcn.dienbien.gov.vn/login"
    url_target = "https://hscvkhcn.dienbien.gov.vn/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm"
    
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://hscvkhcn.dienbien.gov.vn',
        'Referer': url_login
    }
    
    try:
        # Buoc 1: Lay cookie
        r0 = session.get(url_login, verify=False, timeout=15)
        print(f"[B1] Status trang login: {r0.status_code} | URL: {r0.url}")

        # Buoc 2: Dang nhap
        login_data = {
            'Username': USER_NAME,
            'Password': PASS_WORD,
            'RedirectTo': '/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm',
            '__Click': '0'
        }
        res_login = session.post(url_login, data=login_data, headers=headers, verify=False, allow_redirects=True)
        print(f"[B2] Status sau dang nhap: {res_login.status_code} | URL cuoi: {res_login.url}")
        
        # DEBUG: In 1000 ky tu dau cua trang sau dang nhap
        print("===== HTML SAU DANG NHAP (1000 ky tu dau) =====")
        print(res_login.text[:1000])
        print("===== HET =====")

        # Buoc 3: Truy cap trang du lieu
        response = session.get(url_target, headers=headers, verify=False, timeout=25)
        print(f"[B3] Status trang du lieu: {response.status_code} | URL: {response.url}")
        
        # DEBUG: In 1000 ky tu dau cua trang du lieu
        print("===== HTML TRANG DU LIEU (1000 ky tu dau) =====")
        print(response.text[:1000])
        print("===== HET =====")

        # Parse nhu cu
        soup = BeautifulSoup(response.text, 'html.parser')
        ds_van_ban = []
        rows = soup.find_all('tr')
        print(f"[B3] Tim thay {len(rows)} dong <tr>")
        
        for row in rows:
            cols = row.find_all(['td', 'font'])
            txt = [re.sub(r'\s+', ' ', c.get_text().strip()) for c in cols if c.get_text().strip()]
            found_date = None
            for t in txt:
                if re.search(r'\d{2}/\d{2}/\d{4}', t):
                    found_date = t
                    break
            if found_date:
                so_hieu = ""
                noi_dung = ""
                for t in txt:
                    if "/" in t and t != found_date: so_hieu = t
                    if len(t) > 25: noi_dung = t
                if so_hieu:
                    ds_van_ban.append([so_hieu, found_date, noi_dung])
        
        return ds_van_ban

    except Exception as e:
        print(f"❌ Loi chi tiet: {e}")
    return []
