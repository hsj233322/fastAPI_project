import time
import csv
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service as EdgeService

# ---------- 基本配置 ----------
USERNAME = "16638415737" 
PASSWORD = "Lzh09073514." 
MAX_PAGES = None                  # None 表示爬取所有页
DELAY = 5                       # 每次翻页间隔秒数，避免请求过快

# ---------- 接口和请求头 ----------
BASE_URL = "https://www.ncss.cn/student/jobs/jobslist/ajax/"
INIT_URL = "https://www.ncss.cn/student/jobs/internindex.html"
LOGIN_URL = "https://www.ncss.cn/student/signin.html"

HEADERS = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "connection": "keep-alive",
    "host": "www.ncss.cn",
    "referer": "https://www.ncss.cn/student/jobs/internindex.html",
    "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Microsoft Edge";v="150"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0",
    "x-requested-with": "XMLHttpRequest",
}

# ---------- 自动登录获取 Cookie ----------
def login_and_get_cookies(username: str, password: str):
    """
    用 Selenium 模拟登录，返回带登录态 Cookie 的 requests.Session
    """
    options = webdriver.EdgeOptions()
    # 无头模式，不打开浏览器窗口
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    service = EdgeService(executable_path=r"D:\Dev\Projects\fetch_project\msedgedriver.exe")
    driver = webdriver.Edge(service=service, options=options)

    try:
        print("🔄 正在打开求职者登录页面...")
        driver.get(LOGIN_URL)
        wait = WebDriverWait(driver, 10)

        # 填写手机号/邮箱
        username_input = wait.until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        password_input = driver.find_element(By.ID, "password")

        username_input.clear()
        username_input.send_keys(username)
        password_input.clear()
        password_input.send_keys(password)

        # 点击登录按钮
        login_btn = driver.find_element(By.CSS_SELECTOR, "input.btn_login[type='submit']")
        login_btn.click()

        # 等待登录成功标志
        try:
            _ = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(),'退出')]")))
        except:
            # 如果页面上没有“退出”，可以等 URL 变化或直接等待几秒
            time.sleep(3)
        print("✅ 登录成功！")

        # 提取浏览器中的所有 Cookie
        selenium_cookies = driver.get_cookies()
        driver.quit()

        # 构建 requests.Session 并注入 Cookie
        session = requests.Session()
        session.headers.update(HEADERS)

        # 先访问初始页面，让 Session 激活一些基础 Cookie
        _ = session.get(INIT_URL, timeout=15)

        # 将 Selenium 的 Cookie 写入 Session
        for cookie in selenium_cookies:
            _ = session.cookies.set(
                cookie['name'],
                cookie['value'],
                domain=cookie.get('domain', ''),
                path=cookie.get('path', '/')
            )

        # 重新设置 XSRF Token
        xsrf_token = session.cookies.get("XSRF-CCKTOKEN")
        if xsrf_token:
            session.headers["X-XSRF-TOKEN"] = xsrf_token
            print(f"🎫 XSRF Token 已设置: {xsrf_token[:16]}...")
        else:
            print("⚠️ 未找到 XSRF-CCKTOKEN，可能会影响请求")

        return session

    except Exception as e:
        print(f"❌ 登录失败：{e}")
        # 登录失败时保存截图方便排查
        driver.save_screenshot("login_error.png")
        driver.quit()
        return None

# ---------- 爬取单页数据 ----------
def fetch_page(session, page_no, page_size=10):
    """获取单页职位数据"""
    params = {
        "jobType": "03",
        "areaCode": "",
        "jobName": "",
        "monthPay": "",
        "industrySectors": "",
        "property": "",
        "categoryCode": "",
        "memberLevel": "",
        "recruitType": "",
        "offset": page_no,
        "limit": page_size,
        "keyUnits": "",
        "degreeCode": "",
        "sourcesName": "0",
        "sourcesType": "",
        "_": int(time.time() * 1000),
    }

    resp = session.get(BASE_URL, params=params, timeout=15)
    resp.raise_for_status()

    ct = resp.headers.get("Content-Type", "")
    if "json" not in ct.lower():
        print(f"❌ 第{page_no}页非JSON! Content-Type={ct}")
        print(f"📄 响应预览:\n{resp.text[:500]}")
        return None

    try:
        data = resp.json()
    except Exception as e:
        print(f"❌ 第{page_no}页 JSON解析失败: {e}")
        print(f"📄 响应预览:\n{resp.text[:500]}")
        return None

    if not data.get("flag"):
        print(f"[错误] 第{page_no}页业务失败: {data.get('errors')}")
        return None

    pagination = data["data"]["pagenation"]
    jobs = data["data"]["list"]
    print(f"[成功] 第{page_no}页 | {len(jobs)}条 | 总:{pagination['count']} | 共{pagination['total']}页")

    return {
        "jobs": jobs,
        "total_pages": pagination["total"],
        "total_records": pagination["count"],
    }

# ---------- 爬取多页 ----------
def crawl_all_jobs(session, max_pages=None, delay=5):
    """爬取多页职位数据，max_pages 为 None 时爬完所有"""
    all_jobs = []
    seen_ids = set()

    first_page = fetch_page(session, 1)
    if not first_page:
        return []

    for job in first_page["jobs"]:
        if job["jobId"] not in seen_ids:
            seen_ids.add(job["jobId"])
            all_jobs.append(job)

    total_pages = first_page["total_pages"]
    if max_pages:
        total_pages = min(total_pages, max_pages)

    print(f"\n📊 计划爬取 {total_pages} 页，预计 {(total_pages - 1) * delay} 秒完成\n")

    for page in range(2, total_pages + 1):
        time.sleep(delay)
        result = fetch_page(session, page)
        if result and result["jobs"]:
            new_count = 0
            for job in result["jobs"]:
                if job["jobId"] not in seen_ids:
                    seen_ids.add(job["jobId"])
                    all_jobs.append(job)
                    new_count += 1
            print(f"  ↳ 本页新增 {new_count} 条不重复数据，累计: {len(all_jobs)}")
        else:
            print(f"[跳过] 第{page}页无数据")

    return all_jobs

# ---------- 保存为 CSV ----------
def save_to_csv(jobs, filename="ncss_intern_jobs.csv"):
    """保存职位数据为 CSV 文件"""
    if not jobs:
        print("没有数据可保存")
        return

    fields = [
        "岗位名称", "单位名称", "省份", "月薪范围(k)",
        "招聘人数", "学历要求", "专业要求", "单位性质",
        "单位规模", "福利标签", "发布时间", "职位ID",
    ]

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        for job in jobs:
            pub_date = datetime.fromtimestamp(
                job["publishDate"] / 1000
            ).strftime("%Y-%m-%d %H:%M")
            writer.writerow([
                job["jobName"], job["recName"], job["areaCodeName"],
                f"{job['lowMonthPay']}-{job['highMonthPay']}",
                job["headCount"], job["degreeName"], job["major"],
                job["recProperty"], job["recScale"], job["recTags"],
                pub_date, job["jobId"],
            ])

    print(f"✅ 数据已保存至 {filename}，共 {len(jobs)} 条")

# ---------- 主程序 ----------
if __name__ == "__main__":
    session = None
    try:
        session = login_and_get_cookies(USERNAME, PASSWORD)
        if session:
            jobs = crawl_all_jobs(session, max_pages=MAX_PAGES, delay=DELAY)
            filename = f"ncss_intern_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            save_to_csv(jobs, filename)
    except Exception as e:
        print(f"脚本异常：{e}")
    finally:
        if session:
            session.close()   # 关闭 requests 会话
        print("脚本完全退出")