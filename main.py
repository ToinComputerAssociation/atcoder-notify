from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
#from selenium.webdriver.chrome.service import Service
import time

#ドライバのpathを指定
path = 'chromedriver-win64\chromedriver.exe'
#ブラウザのウィンドウを表すオブジェクト"driver"を作成
options = Options()
options.add_argument('--blink-settings=imagesEnabled=false')
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)
url = 'https://kenkoooo.com/atcoder/#/contest/show/c7f01330-a215-42f5-aac9-b6fdc062de32?activeTab=Standings'

driver.get(url)
time.sleep(3)
w = driver.execute_script('return document.body.scrollWidth')
h = driver.execute_script('return document.body.scrollHeight')
driver.set_window_size(h, 6400)
# 範囲を指定してスクリーンショットを撮る
png = driver.find_element(By.XPATH, '//*[@id="root"]/div/div[2]/div[6]/div[2]/div/table').screenshot_as_png
# ファイルに保存
with open('image/screenshot.png', 'wb') as f:
    f.write(png)
#driver.save_screenshot('image/screenshot.png')
driver.quit()