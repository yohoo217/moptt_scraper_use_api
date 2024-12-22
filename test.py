import requests
import json
import time
import os
from urllib.parse import quote

class MopttScraper:
    def __init__(self, board_name):
        self.base_url = "https://moptt.azurewebsites.net/api/v2/hotpost"
        self.board_name = board_name
        self.all_posts = []
        self.json_file = f"moptt_{board_name}.json"
        self.headers = {
            'Authorization': 'cMIS1Icr95gnR2U19hxO2K7r6mYQ96vp'
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
        print(f"\r已儲存 {len(self.all_posts)} 篇文章至 {self.json_file}")

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
                    filtered_post = {
                        '_id': post['_id'],  # 保留用於去重
                        'title': post['title'],
                        'timestamp': post['timestamp'],
                        'url': post['url'],
                        'hits': post['hits'],
                        'acceptedDate': post['acceptedDate'],
                        'description': post['description']
                    }
                    # 如果有編號，也保留下來
                    if 'number' in post:
                        filtered_post['number'] = post['number']
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
        consecutive_2023_count = 0  # 追蹤連續2023年的文章數量

        while True:
            page_count += 1
            print(f"\r正在爬取第 {page_count} 頁...", end='')
            
            data = self.fetch_posts(page_param)
            if not data or 'posts' not in data:
                break

            new_posts = []
            for post in data['posts']:
                # 檢查時間戳記是否為2023年
                timestamp = post.get('timestamp', '')
                if timestamp.startswith('2023'):
                    consecutive_2023_count += 1
                    if consecutive_2023_count >= 5:
                        print("\n已找到連續5篇2023年的文章，停止爬取")
                        self.all_posts.extend(new_posts)
                        self.save_posts_to_json()
                        return self.all_posts
                else:
                    consecutive_2023_count = 0  # 重置計數器

                if post['_id'] not in existing_ids:
                    post['number'] = current_number  # 添加編號
                    current_number += 1
                    new_posts.append(post)
                    existing_ids.add(post['_id'])

            if new_posts:
                self.all_posts.extend(new_posts)
                total_new_posts += len(new_posts)

            # 檢查是否有下一頁
            if 'nextPage' in data and 'skip' in data['nextPage']:
                page_param = json.dumps({"skip": data['nextPage']['skip']})
                time.sleep(0.5)  # 避免請求過於頻繁
            else:
                break

            # 每5頁儲存一次
            if page_count % 100 == 0:
                self.save_posts_to_json()

        # 最後儲存一次
        self.save_posts_to_json()
        print(f"\n爬取完成！總共新增 {total_new_posts} 篇文章")
        return self.all_posts

if __name__ == "__main__":
    # 可以設定要爬取的看板名稱
    BOARD_NAMES = ["sex", "Baseball", "Gossiping", "Stock", "HatePolitics", "NBA", "C_Chat"]

    
    for board in BOARD_NAMES:
        print(f"\n開始爬取 {board} 看板")
        scraper = MopttScraper(board)
        scraper.scrape()
