"""
截图工具 - 为接单作品集生成截图
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

OUTPUT_DIR = r"C:\Users\hp\Desktop\作品集截图"
os.makedirs(OUTPUT_DIR, exist_ok=True)

APP_URL = "http://localhost:8512"


def setup_driver():
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.edge.service import Service
    from webdriver_manager.microsoft import EdgeChromiumDriverManager

    opts = EdgeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1440,900")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.binary_location = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    service = Service(EdgeChromiumDriverManager().install())
    return webdriver.Edge(service=service, options=opts)


def wait_and_screenshot(driver, name, wait_sec=3):
    time.sleep(wait_sec)
    path = os.path.join(OUTPUT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    print(f"  ✅ {name}.png")
    return path


def main():
    # 先创建测试用户
    from app.database import init_db
    from app.auth import create_user
    init_db()
    if not create_user("demo", "demo123", display_name="演示用户"):
        print("用户已存在")

    driver = setup_driver()
    try:
        # ========== 截图 1: 登录页面 ==========
        print("\n📸 截图 1: 登录页面")
        driver.get(APP_URL)
        wait_and_screenshot(driver, "01-登录页面")

        # ========== 截图 2: 注册页面 ==========
        print("\n📸 截图 2: 注册标签")
        try:
            register_tab = driver.find_element(By.XPATH, "//button[text()='注册']")
            register_tab.click()
            time.sleep(1)
        except:
            pass
        wait_and_screenshot(driver, "02-注册页面")

        # ========== 截图 3: 登录 ==========
        print("\n📸 截图 3: 主界面")
        try:
            login_tab = driver.find_element(By.XPATH, "//button[text()='登录']")
            login_tab.click()
            time.sleep(1)
        except:
            pass

        # 尝试多种方式定位输入框
        import re
        for input_elem in driver.find_elements(By.TAG_NAME, "input"):
            placeholder = input_elem.get_attribute("placeholder") or ""
            aria = input_elem.get_attribute("aria-label") or ""
            if "用户" in placeholder or "用户" in aria or "名" in placeholder:
                input_elem.send_keys("demo")
                break

        for input_elem in driver.find_elements(By.TAG_NAME, "input"):
            tp = input_elem.get_attribute("type") or ""
            if tp == "password":
                input_elem.send_keys("demo123")
                break

        # 找所有按钮点击
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            txt = btn.text.strip()
            if txt == "登录":
                btn.click()
                break
        time.sleep(3)
        wait_and_screenshot(driver, "03-主界面")

        # ========== 截图 4: 知识库管理 ==========
        print("\n📸 截图 4: 知识库管理")
        wait_and_screenshot(driver, "04-知识库管理")

        # ========== 截图 5: 问答界面 ==========
        print("\n📸 截图 5: 问答界面")
        try:
            # Streamlit chat input 是 textarea
            for ta in driver.find_elements(By.TAG_NAME, "textarea"):
                ph = ta.get_attribute("placeholder") or ""
                if "问题" in ph or "输入" in ph:
                    ta.send_keys("双碳目标下这个文件讲了什么")
                    break
            # Streamlit chat send 按钮
            for btn in driver.find_elements(By.TAG_NAME, "button"):
                if "Send" in (btn.get_attribute("aria-label") or ""):
                    btn.click()
                    break
            time.sleep(8)
        except:
            pass
        wait_and_screenshot(driver, "05-问答界面")

        # ========== 截图 6: 文档列表 ==========
        print("\n📸 截图 6: 文档列表")
        wait_and_screenshot(driver, "06-文档列表")

        print(f"\n🎉 截图完成！保存在: {OUTPUT_DIR}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
