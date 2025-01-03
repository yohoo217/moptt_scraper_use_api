# 可配置的設定
BOARD_NAMES = ["KoreaStar", "LoL"]
# BOARD_NAMES = ["Baseball","Gossiping", "Stock", "NBA", "Lol", "HatePolitics", "Beauty", "Lifeismoney", "KoreaStar", "sex", "Japandrama", "MakeUp", "marvel"]
API_KEY = 'cMIS1Icr95gnR2U19hxO2K7r6mYQ96vp'
BASE_URL = "https://moptt.azurewebsites.net/api/v2/hotpost"

import requests
import json
import time
import os
from urllib.parse import quote
from config import POST_FIELDS

class MopttScraper:
    def __init__(self, board_name):
        self.base_url = BASE_URL
        self.board_name = board_name
        self.all_posts = []
        self.json_file = f"moptt_{board_name}.json"
        self.headers = {
            'Authorization': API_KEY
        }

    def load_existing_posts(self):
        """載入現有的文章資料"""
        if os.path.exists(self.json_file):
            with open(self.json_file, 'r', encoding='utf-8') as f:
                try:
                    posts = json.load(f)
                    # 確保每個文章都有 _id 欄位
                    return [post for post in posts if isinstance(post, dict) and '_id' in post]
                except json.JSONDecodeError:
                    return []
        return []

    def save_posts_to_json(self):
        """儲存文章資料到JSON檔案"""
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_posts, f, ensure_ascii=False, indent=2)
        print(f"\r已儲存 {len(self.all_posts)} 篇文章至 {self.json_file}", end="")

    def fetch_posts(self, page_param=None):
        """獲取指定頁面的文章"""
        url = f"{self.base_url}?b={self.board_name}"
        if page_param:
            # URL encode the page parameter
            encoded_page = quote(page_param)
            url = f"{url}&page={encoded_page}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # 檢查是否有錯誤
            data = response.json()
            
            # 只保留需要的欄位
            if 'posts' in data:
                filtered_posts = []
                for post in data['posts']:
                    # 檢查是否至少有一個時間欄位
                    timestamp = post.get('timestamp', '')
                    accepted_date = post.get('acceptedDate', '')
                    if not timestamp and not accepted_date:
                        print(f"警告：文章缺少時間資訊 (ID: {post.get('_id', 'unknown')})")
                        continue

                    # 使用 timestamp 或 acceptedDate 作為時間判斷
                    post_time = timestamp if timestamp else accepted_date
                    
                    filtered_post = {
                        '_id': post['_id'],  # 保留用於去重
                        '_post_time': post_time  # 內部使用，不會輸出
                    }
                    # 根據設定檔決定要保留哪些欄位
                    for field, include in POST_FIELDS.items():
                        if include and field in post:
                            filtered_post[field] = post[field]
                    filtered_posts.append(filtered_post)
                data['posts'] = filtered_posts
            
            return data
        except requests.RequestException as e:
            print(f"獲取文章時發生錯誤: {e}")
            return None

    def scrape(self):
        """爬取所有文章"""
        # 載入現有的文章
        self.all_posts = self.load_existing_posts()
        existing_ids = {post['_id'] for post in self.all_posts}

        page_param = None
        total_new_posts = 0
        page_count = 0
        current_number = len(self.all_posts) + 1  # 從現有文章數量開始編號

        while True:
            page_count += 1
            print(f"\r正在爬取第 {page_count} 頁...", end='')
            
            data = self.fetch_posts(page_param)
            if not data or 'posts' not in data:
                break

            new_posts = []
            dec_2023_count = sum(1 for post in self.all_posts if post.get('_post_time', '').startswith('2023-12'))
            
            for post in data['posts']:
                # 檢查是否已經找到足夠的2023年12月文章
                post_time = post.get('_post_time', '')
                if post_time.startswith('2023-12'):
                    dec_2023_count += 1
                    if dec_2023_count >= 5:
                        print("\r已找到5篇2023年12月的文章，停止爬取", end="")
                        if post['_id'] not in existing_ids:
                            post['number'] = current_number
                            current_number += 1
                            # 移除內部使用的時間欄位
                            if '_post_time' in post:
                                del post['_post_time']
                            new_posts.append(post)
                        self.all_posts.extend(new_posts)
                        self.save_posts_to_json()
                        return self.all_posts

                if post['_id'] not in existing_ids:
                    post['number'] = current_number  # 添加編號
                    current_number += 1
                    # 移除內部使用的時間欄位
                    if '_post_time' in post:
                        del post['_post_time']
                    new_posts.append(post)
                    existing_ids.add(post['_id'])

            if new_posts:
                self.all_posts.extend(new_posts)
                total_new_posts += len(new_posts)

            # 檢查是否有下一頁
            if data.get('nextPage') and isinstance(data['nextPage'], dict) and 'skip' in data['nextPage']:
                page_param = json.dumps({"skip": data['nextPage']['skip']})
                # time.sleep(0.5)  # 避免請求過於頻繁
            else:
                break

            # 每5頁儲存一次
            if page_count % 100 == 0:
                self.save_posts_to_json()

        # 最後儲存一次
        self.save_posts_to_json()
        print(f"\r爬取完成！總共新增 {total_new_posts} 篇文章", end="\n")
        return self.all_posts

if __name__ == "__main__":
    # 可以設定要爬取的看板名稱
    for board in BOARD_NAMES:
        print(f"\r開始爬取 {board} 看板", end="")
        scraper = MopttScraper(board)
        scraper.scrape()
