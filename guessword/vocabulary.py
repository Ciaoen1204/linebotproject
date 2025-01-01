import requests
from bs4 import BeautifulSoup
import pandas as pd


# 目標網址
url = "https://wecan.tw/index.php/2018-12-02-08-34-31/2019-01-03-18-18-31/2000-basic-vocabulary"

# 發送 GET 請求
response = requests.get(url)
response.encoding = 'utf-8'

# 解析 HTML
soup = BeautifulSoup(response.text, 'html.parser')

# 找到包含單字的表格
table = soup.find('table')

# 提取表格中的資料
words = []
for row in table.find_all('tr')[1:]:  # 跳過表頭
    cols = row.find_all('td')
    word = cols[0].text.strip()
    meaning = cols[1].text.strip()
    # 去除單字前面的數字
    word = ''.join([i for i in word if not i.isdigit() and i != '.']).strip()
    words.append([word, meaning])

# 將資料存儲到 CSV 檔案
df = pd.DataFrame(words, columns=['Word', 'Meaning'])
df.to_csv('vocabulary.csv', index=False, encoding='utf-8-sig')

print("單字已成功存儲到 vocabulary.csv")