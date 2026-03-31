def quet_lotus_v18():
    base_url   = "https://hscvkhcn.dienbien.gov.vn"
    url_login  = f"{base_url}/qlvb/index.nsf/default?openform"
    url_post   = f"{base_url}/names.nsf?Login"
    url_target = f"{base_url}/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm"

    session = requests.Session()
    headers_get = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    headers_post = {
        **headers_get,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': base_url,
        'Referer': url_login,
    }

    try:
        # Buoc 1: Lay cookie
        print("🌐 [B1] Lay cookie...")
        r0 = session.get(url_login, headers=headers_get, verify=False, timeout=15)
        print(f"   Status: {r0.status_code}")

        # Buoc 2: Dang nhap
        print("🔑 [B2] Dang nhap...")
        login_data = {
            'Username': USER_NAME,
            'Password': PASS_WORD,
            'RedirectTo': '/qlvb/vbden.nsf/Private_ChoXL_KoHan?OpenForm',
        }
        res_login = session.post(url_post, data=login_data, headers=headers_post, verify=False, allow_redirects=True)
        print(f"   Status: {res_login.status_code} | URL: {res_login.url}")

        if 'Username' in res_login.text and 'Password' in res_login.text:
            print("❌ Dang nhap that bai!")
            return []
        print("✅ Dang nhap thanh cong!")

        # Buoc 3: Truy cap trang danh sach
        print("📄 [B3] Lay danh sach van ban...")
        response = session.get(url_target, headers=headers_get, verify=False, timeout=25)
        print(f"   Status: {response.status_code}")

        # Parse dung theo cau truc that: tab-separated
        soup = BeautifulSoup(response.text, 'html.parser')
        ds_van_ban = []

        rows = soup.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            if len(tds) < 5:
                continue

            # Lay text tung cot
            cols = [re.sub(r'\s+', ' ', td.get_text()).strip() for td in tds]

            # Tim cot co ngay dd/mm/yyyy
            so_den   = ""
            ngay_den = ""
            so_hieu  = ""
            co_quan  = ""
            trich_yeu = ""

            # Duyet cac cot tim ngay
            for i, c in enumerate(cols):
                if re.match(r'^\d{2}/\d{2}/\d{4}$', c):
                    ngay_den  = c
                    so_den    = cols[i-1] if i >= 1 else ""
                    so_hieu   = cols[i+1] if i+1 < len(cols) else ""
                    co_quan   = cols[i+2] if i+2 < len(cols) else ""
                    trich_yeu = cols[i+3] if i+3 < len(cols) else ""
                    break

            # Chi lay hang co du thong tin
            if ngay_den and so_hieu and re.search(r'\d+', so_den):
                # Loai bo hang chi co so thu tu hoac rong
                so_hieu_clean = so_hieu.strip()
                if so_hieu_clean and '/' in so_hieu_clean:
                    ds_van_ban.append([
                        so_hieu_clean,
                        ngay_den,
                        trich_yeu[:200],
                        co_quan,
                        so_den
                    ])

        print(f"✅ Parse xong: {len(ds_van_ban)} van ban")
        return ds_van_ban

    except requests.exceptions.ConnectionError as e:
        print(f"❌ Loi ket noi: {e}")
    except requests.exceptions.Timeout:
        print("❌ Timeout")
    except Exception as e:
        print(f"❌ Loi: {e}")
    return []
