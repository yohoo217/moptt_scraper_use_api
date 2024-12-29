import json
import glob
from collections import Counter
from datetime import datetime
import re
import csv
import os
from ptt_analysis import load_json_file, load_all_json_files, find_top_comments_posts

class AdvancedAnalysis:
    def __init__(self):
        print("載入資料中...")
        self.board_data = load_all_json_files()
        self.stop_words = {'推推', '推文', '感謝', '謝謝', '這個', '那個', '所以', '因為', '可是', '但是', '什麼', '如果', '的話'}

    def search_posts_by_keywords_and_time(self, keywords, start_time, end_time, output_csv=False):
        """搜尋特定時間區間內包含關鍵字的文章，並可選擇輸出成CSV"""
        start_datetime = datetime.strptime(start_time, "%Y-%m-%d")
        end_datetime = datetime.strptime(end_time, "%Y-%m-%d")
        
        matching_posts = []
        total_count = 0
        
        for board, posts in self.board_data.items():
            for post in posts:
                try:
                    post_time_str = post.get('acceptedDate', '').split('T')[0]
                    post_time = datetime.strptime(post_time_str, "%Y-%m-%d")
                    
                    if start_datetime <= post_time <= end_datetime:
                        title = post.get('title', '').lower()
                        content = ''
                        comments_summary = ''
                        
                        if 'comments_data' in post:
                            if 'content' in post['comments_data']:
                                content = post['comments_data']['content'].lower()
                            if 'comments' in post['comments_data']:
                                comments_summary = '; '.join([c.get('content', '') for c in post['comments_data']['comments'][:5]])
                        
                        # 檢查是否包含所有關鍵字
                        text_to_search = title + ' ' + content
                        if all(keyword.lower() in text_to_search for keyword in keywords):
                            total_count += 1
                            matching_posts.append({
                                'board': board,
                                'title': post['title'],
                                'date': post_time_str,
                                'url': post['url'],
                                'content': content[:500] + '...' if len(content) > 500 else content,
                                'comments': comments_summary
                            })
                except (ValueError, AttributeError) as e:
                    continue

        # 輸出結果
        if matching_posts:
            print(f"\n找到 {total_count} 篇符合的文章：")
            
            if output_csv:
                filename = f"search_{'_'.join(keywords)}_{start_time}_{end_time}.csv"
                with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=['board', 'title', 'date', 'url', 'content', 'comments'])
                    writer.writeheader()
                    writer.writerows(matching_posts)
                print(f"搜尋結果已保存到 {filename}")
            
            for post in matching_posts:
                print(f"\n版面：{post['board']}")
                print(f"標題：{post['title']}")
                print(f"日期：{post['date']}")
                print(f"網址：{post['url']}")
                print("內容摘要：", post['content'][:200] + '...')
                if post['comments']:
                    print("部分留言：", post['comments'][:200] + '...')
                print()
        else:
            print(f"\n在指定時間區間內，未找到包含關鍵字的文章")
        
        return total_count, matching_posts

    def count_keyword_by_board(self, keywords, output_csv=False):
        """計算關鍵字在各個版位出現的次數，並可選擇輸出成CSV"""
        if isinstance(keywords, str):
            keywords = [keywords]
        
        counts = {}
        matching_posts = {}
        
        for board, posts in self.board_data.items():
            board_count = 0
            board_matching_posts = []
            
            for post in posts:
                title = post.get('title', '').lower()
                content = ''
                comments_summary = ''
                
                if 'comments_data' in post:
                    if 'content' in post['comments_data']:
                        content = post['comments_data']['content'].lower()
                    if 'comments' in post['comments_data']:
                        comments_summary = '; '.join([c.get('content', '') for c in post['comments_data']['comments'][:5]])
                
                if all(keyword.lower() in (title + ' ' + content) for keyword in keywords):
                    board_count += 1
                    board_matching_posts.append({
                        'title': post['title'],
                        'url': post['url'],
                        'date': post.get('acceptedDate', '').split('T')[0],
                        'content': content[:500] + '...' if len(content) > 500 else content,
                        'comments': comments_summary
                    })
            
            if board_count > 0:
                counts[board] = board_count
                matching_posts[board] = board_matching_posts

        # 輸出結果
        print(f"\n包含所有關鍵字 {', '.join(keywords)} 的文章在各版位的出現次數：")
        for board, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
            print(f"{board}: {count} 篇")

        if output_csv:
            filename = f"keyword_analysis_{'_'.join(keywords)}.csv"
            with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Board', 'Count', 'Title', 'Date', 'URL', 'Content', 'Comments'])
                for board in sorted(matching_posts.keys(), key=lambda x: counts[x], reverse=True):
                    for post in matching_posts[board]:
                        writer.writerow([
                            board,
                            counts[board],
                            post['title'],
                            post['date'],
                            post['url'],
                            post['content'],
                            post['comments']
                        ])
            print(f"\n詳細資料已保存到 {filename}")

        return counts

    def find_most_common_strings(self, board_name, top_n=20, custom_stop_words=None):
        """找出特定版位最常出現的字串，可自定義停用詞"""
        if board_name not in self.board_data:
            return []
        
        if custom_stop_words:
            self.stop_words.update(custom_stop_words)
        
        text = ""
        for post in self.board_data[board_name]:
            text += post.get('title', '') + " "
            if 'comments_data' in post:
                if 'content' in post['comments_data']:
                    text += post['comments_data']['content'] + " "
                if 'comments' in post['comments_data']:
                    for comment in post['comments_data']['comments']:
                        if 'content' in comment:
                            text += comment['content'] + " "
        
        words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        filtered_words = [word for word in words if word not in self.stop_words]
        
        return Counter(filtered_words).most_common(top_n)

def main():
    analyzer = AdvancedAnalysis()
    
    while True:
        print("\n請選擇要執行的功能：")
        print("1. 顯示所有版位留言數最多的前二十篇文章")
        print("2. 搜尋特定時間區段內的關鍵字文章（支援多關鍵字，可選擇輸出CSV）")
        print("3. 分析關鍵字在各版位的分布（支援多關鍵字，可選擇輸出CSV）")
        print("4. 分析特定版位的熱門討論詞彙（可自訂排除字詞）")
        print("5. 退出")
        
        choice = input("請輸入選項（1-5）：")
        
        if choice == '1':
            top_posts = find_top_comments_posts(analyzer.board_data)
            print("\n留言數最多的前二十篇文章：")
            for i, post in enumerate(top_posts, 1):
                print(f"{i}. 版面：{post['board']}")
                print(f"   標題：{post['title']}")
                print(f"   留言數：{post['total_comments']}")
                print(f"   日期：{post['date']}")
                print(f"   網址：{post['url']}\n")
        
        elif choice == '2':
            keywords = input("請輸入關鍵字（多個關鍵字請用空格分隔）：").split()
            start_date = input("請輸入開始日期（YYYY-MM-DD）：")
            end_date = input("請輸入結束日期（YYYY-MM-DD）：")
            save_csv = input("是否要將結果保存為CSV檔案？(y/n)：").lower() == 'y'
            
            total_count, matching_posts = analyzer.search_posts_by_keywords_and_time(
                keywords, start_date, end_date, output_csv=save_csv)
        
        elif choice == '3':
            keywords = input("請輸入關鍵字（多個關鍵字請用空格分隔）：").split()
            save_csv = input("是否要將結果保存為CSV檔案？(y/n)：").lower() == 'y'
            
            counts = analyzer.count_keyword_by_board(keywords, output_csv=save_csv)
        
        elif choice == '4':
            board_name = input("請輸入要分析的版位名稱（例如：Beauty）：")
            custom_stop_words = input("請輸入要排除的字詞（用空格分隔，直接按Enter跳過）：").split()
            
            common_strings = analyzer.find_most_common_strings(board_name, custom_stop_words=custom_stop_words)
            print(f"\n{board_name} 版最常出現的前二十個字串：")
            for word, count in common_strings:
                print(f"{word}: {count} 次")
        
        elif choice == '5':
            print("程式結束")
            break
        
        else:
            print("無效的選項，請重新輸入")

if __name__ == "__main__":
    main()
