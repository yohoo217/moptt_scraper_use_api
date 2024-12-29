# 可配置的設定
BOARD_NAMES = ["Baseball", "Gossiping", "Stock", "NBA", "C_Chat", "LoL", "Japandrama", "Makeup", "marvel", "BabyMother", "KoreaStar"]
# BOARD_NAMES = ["HatePolitics", "Beauty", "Lifeismoney", "KoreaStar", "Japandrama", "MakeUp", "marvel", "BabyMother"]
API_KEY = 'cMIS1Icr95gnR2U19hxO2K7r6mYQ96vp'  # API金鑰
BASE_URL = "https://moptt.tw/ptt/"
MAX_RETRIES = 3  # 最大重試次數
RETRY_DELAY = 1  # 重試延遲秒數
REQUEST_TIMEOUT = 3  # 請求超時秒數

import requests
import json
import re
import os
import time
from urllib.parse import urlparse, unquote
import urllib3
from config import COMMENT_FIELDS

# 關閉 InsecureRequestWarning 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CommentScraper:
    def __init__(self, board_name):
        self.base_url = BASE_URL
        self.headers = {
            'Authorization': API_KEY
        }
        self.board_name = board_name
        self.input_file = f"moptt_{board_name}.json"
        self.max_retries = MAX_RETRIES
        self.retry_delay = RETRY_DELAY

    def convert_url_to_api_endpoint(self, ptt_url):
        """將PTT URL轉換為API端點"""
        # 解析URL
        parsed = urlparse(ptt_url)
        path_parts = parsed.path.split('/')
        
        # 取得看板名稱和文章ID
        board = path_parts[2]
        article_id = path_parts[3].replace('.html', '')
        
        # 組合API端點
        api_endpoint = f"{self.base_url}{board}.{article_id}"
        return api_endpoint

    def fetch_comments(self, api_url, article_info=None):
        """從API獲取留言資料"""
        retries = 0
        while retries < self.max_retries:
            try:
                # 設定3秒超時，關閉SSL驗證
                response = requests.get(api_url, headers=self.headers, timeout=REQUEST_TIMEOUT, verify=False)
                response.raise_for_status()
                data = response.json()
                
                # 檢查回應是否包含必要的欄位
                if not data.get('comments') or not isinstance(data['comments'], dict):
                    raise ValueError("回應缺少 'comments' 欄位或格式不正確")

                comments = data['comments']
                
                # 提取所需的資料，使用設定檔控制輸出欄位
                comments_data = {}
                
                # 添加統計資料
                if COMMENT_FIELDS.get('total_comments'):
                    comments_data['total_comments'] = comments.get('total', 0)
                if COMMENT_FIELDS.get('like_count'):
                    comments_data['like_count'] = comments.get('like', 0)
                if COMMENT_FIELDS.get('dislike_count'):
                    comments_data['dislike_count'] = comments.get('dislike', 0)
                if COMMENT_FIELDS.get('neutral_count'):
                    comments_data['neutral_count'] = comments.get('neutral', 0)
                
                # 添加文章內容
                if COMMENT_FIELDS.get('content'):
                    comments_data['content'] = data.get('content', '')
                
                # 提取每個留言的資料
                if isinstance(comments.get('items', []), list):
                    comments_data['comments'] = []
                    for comment in comments['items']:
                        if isinstance(comment, dict):
                            comment_item = {}
                            if COMMENT_FIELDS.get('tag'):
                                comment_item['tag'] = comment.get('tag', '')
                            if COMMENT_FIELDS.get('content'):
                                comment_item['content'] = comment.get('content', '')
                            comments_data['comments'].append(comment_item)
                
                return comments_data
                
            except requests.Timeout:
                title = article_info.get('title', '無標題') if article_info else '無標題'
                print(f"\n跳過文章：{title}")
                print(f"文章網址：{article_info.get('url', 'N/A') if article_info else 'N/A'}")
                print(f"原因：請求超時（超過{REQUEST_TIMEOUT}秒）")
                return None
            except requests.HTTPError as e:
                title = article_info.get('title', '無標題') if article_info else '無標題'
                print(f"\n跳過文章：{title}")
                print(f"文章網址：{article_info.get('url', 'N/A') if article_info else 'N/A'}")
                print(f"原因：{str(e)}")
                return None
            except (ValueError, KeyError, TypeError) as e:
                title = article_info.get('title', '無標題') if article_info else '無標題'
                print(f"\n跳過文章：{title}")
                print(f"文章網址：{article_info.get('url', 'N/A') if article_info else 'N/A'}")
                print(f"原因：API回應格式錯誤 - {str(e)}")
                return None
            except Exception as e:
                retries += 1
                if retries < self.max_retries:
                    print(f"發生錯誤：{str(e)}，將在 {self.retry_delay} 秒後重試...")
                    time.sleep(self.retry_delay)
                else:
                    title = article_info.get('title', '無標題') if article_info else '無標題'
                    print(f"\n跳過文章：{title}")
                    print(f"文章網址：{article_info.get('url', 'N/A') if article_info else 'N/A'}")
                    print(f"原因：{str(e)}")
                    return None

    def process_urls_from_file(self):
        """處理JSON檔案中的文章並更新評論資料"""
        try:
            # 檢查檔案是否存在
            if not os.path.exists(self.input_file):
                print(f"找不到輸入檔案: {self.input_file}")
                return

            # 讀取現有的文章資料
            with open(self.input_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)

            total_processed = 0
            skipped_count = 0
            
            # 處理每個文章的URL
            for i, article in enumerate(articles):
                try:
                    if 'url' in article:
                        # 檢查是否已經有評論資料
                        if 'comments_data' in article:
                            print(f"\r已處理: {total_processed}/{len(articles)} 篇文章 (已跳過: {skipped_count} 篇)", end='')
                            continue

                        print(f"\r處理中: {i+1}/{len(articles)} 篇文章，已完成: {total_processed} 篇 (已跳過: {skipped_count} 篇)")
                        api_url = self.convert_url_to_api_endpoint(article['url'])
                        comments_data = self.fetch_comments(api_url, article)
                        
                        if comments_data:
                            # 直接在文章資料中加入評論資料
                            article['comments_data'] = comments_data
                            total_processed += 1
                        else:
                            skipped_count += 1
                            
                        # 每處理100篇文章就更新一次檔案
                        if (total_processed + skipped_count) % 100 == 0:
                            with open(self.input_file, 'w', encoding='utf-8') as f:
                                json.dump(articles, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"\n處理文章時發生錯誤: {e}")
                    skipped_count += 1  # 計入錯誤的文章到跳過數量
                    continue  # 繼續處理下一篇文章

            # 最後再儲存一次，確保所有資料都有保存
            with open(self.input_file, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            print(f"\r{self.board_name} 看板處理完成，共 {total_processed}/{len(articles)} 篇文章 (跳過 {skipped_count} 篇)")
            
        except Exception as e:
            print(f"\r處理時發生錯誤: {e}")

if __name__ == "__main__":
    # 設定要處理的看板
    for board in BOARD_NAMES:
        scraper = CommentScraper(board)
        scraper.process_urls_from_file()