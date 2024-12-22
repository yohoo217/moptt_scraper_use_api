"""
MOPTT 文章內容爬蟲 (Playwright版本)
專門用於爬取文章的詳細內容（互動數據、回應等）
"""
import json
import time
import random
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError, Error

# ====== 設定區域開始 ======
# 等待時間設定（秒）
WAIT_TIME = 0.5
MAX_RETRY = 3
# ====== 設定區域結束 ======


class MopttContentScraper:
    """
    MOPTT 文章內容爬蟲類別 (使用 Playwright)
    負責爬取文章的詳細內容（互動數據、回應等）
    """

    def __init__(self, playwright):
        """初始化爬蟲設定"""
        self.playwright = playwright
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context()

    def get_article_content(self, article_info):
        """
        擷取單篇文章的詳細內容
        
        Args:
            article_info: 包含文章基本資訊的字典
            
        Returns:
            dict: 包含文章所有資訊的字典
        """
        for attempt in range(1, MAX_RETRY + 1):
            page = None
            try:
                # 重新開一個 page，避免單一 page 在多次跳轉後被關閉
                page = self.context.new_page()

                # 隨機休息一下，減少被網站偵測機率（可依需求啟用）
                # time.sleep(random.uniform(1, 3))

                # 將 PTT URL 轉換為 MOPTT URL
                ptt_url = article_info['url']
                article_id = ptt_url.split('/')[-1].replace('.html', '')
                board_name = ptt_url.split('/')[-2]
                moptt_url = f'https://moptt.tw/p/{board_name}.{article_id}'

                # 訪問頁面
                page.goto(moptt_url)
                page.wait_for_load_state('networkidle')
                time.sleep(WAIT_TIME)

                # 擷取發文時間
                post_time = ""
                time_element = page.locator("div.o_pqSZvuHj7qfwrPg7tI time").first
                if time_element:
                    # 若元素存在，取得其 datetime 屬性
                    post_time = time_element.get_attribute('datetime', timeout=1000)

                # 擷取互動數據
                likes = comments = boos = 0
                interaction_divs = page.locator(".T86VdSgcSk_wVSJ87Jd_").all()
                for div in interaction_divs:
                    try:
                        icon = div.locator("i").first
                        count_text = div.inner_text().strip()
                        count = int(count_text) if count_text.isdigit() else 0
                        icon_class = icon.get_attribute("class") or ""

                        if "fa-thumbs-up" in icon_class:
                            likes = count
                        elif "fa-thumbs-down" in icon_class:
                            boos = count
                        elif "fa-comment-dots" in icon_class:
                            comments = count
                    except:
                        continue

                # 擷取回應內容
                comments_content = []
                try:
                    # 嘗試點擊「顯示全部回應」按鈕
                    show_all_button = page.locator("div.FEfFxCwDtx6IcnHAFaMR").first
                    if show_all_button:
                        show_all_button.click()
                        time.sleep(WAIT_TIME)

                    # 擷取回應
                    comment_spans = page.locator(".qIm88EMEzWPkVVqwCol0").all()
                    for span in comment_spans:
                        comment_text = span.inner_text().strip()
                        if comment_text:
                            comments_content.append(comment_text)
                except:
                    pass

                # 更新文章資訊
                article_info.update({
                    'url': moptt_url,  # 更新為 MOPTT URL
                    'post_time': post_time,
                    'likes': likes,
                    'responses': comments,
                    'boos': boos,
                    'responses_content': comments_content,
                    'content_fetched': True
                })

                # 只要成功就回傳
                return article_info

            except Exception as e:
                print(f"\n[第 {attempt}/{MAX_RETRY} 次重試] 擷取文章內容時發生錯誤: {str(e)}", end='')
                if attempt == MAX_RETRY:
                    # 重試次數已達上限，直接回傳原始資料
                    print(" -> 已達最大重試次數，跳過本篇。", end='')
                    return article_info
            finally:
                # 每次都關掉 page，避免堆疊過多
                if page:
                    page.close()

    def process_articles(self, json_file):
        """
        處理 JSON 檔案中的所有文章
        
        Args:
            json_file: JSON 檔案路徑
        """
        try:
            # 讀取文章列表
            with open(json_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)

            total_articles = len(articles)
            print(f"\n開始處理 {total_articles} 篇文章的內容")

            # 處理每篇文章
            for i, article in enumerate(articles):
                # 檢查是否已經爬取過內容
                if article.get('content_fetched'):
                    continue

                # 印出進度
                title_preview = article['title'][:30]
                if len(article['title']) > 30:
                    title_preview += '...'
                print(f"\r處理進度: {i+1}/{total_articles} | 當前: {title_preview}", end='')

                # 爬取文章內容
                updated_article = self.get_article_content(article)
                articles[i] = updated_article

                # 定期儲存進度
                if (i + 1) % 5 == 0 or i == len(articles) - 1:
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(articles, f, ensure_ascii=False, indent=2)
                    print(f"\r\n已儲存進度，完成 {i+1}/{total_articles} 篇", end='')

                time.sleep(WAIT_TIME)

            print(f"\n文章內容爬取完成，共處理 {total_articles} 篇文章")

        except KeyboardInterrupt:
            print("\n使用者中斷了程式。")
        except Exception as e:
            print(f"\n處理文章時發生錯誤: {str(e)}")

    def close(self):
        """關閉瀏覽器和 Playwright"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        # 不在這裡呼叫 self.playwright.stop() 
        # 因為我們會在主程式的 with block 結束時自動清理
        # 如果想手動關閉，也可以在這裡 stop()
        # self.playwright.stop()


if __name__ == "__main__":
    # 使用 with sync_playwright() as p: 來確保資源自動關閉
    with sync_playwright() as p:
        # 設定要處理的看板
        board_names = ["sex", "Baseball", "Gossiping", "Stock", "HatePolitics", "NBA", "C_Chat"]

        for board_name in board_names:
            json_file_path = f'moptt_{board_name}.json'

            # 建立爬蟲實例並執行爬蟲
            scraper = MopttContentScraper(p)
            scraper.process_articles(json_file_path)
            scraper.close()
            print(f"\n{board_name} 看板文章內容處理完成")