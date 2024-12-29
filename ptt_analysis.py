import json
import glob
from collections import Counter
from datetime import datetime
import re

def load_json_file(file_path):
    """分批載入大型 JSON 檔案"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return []

def load_all_json_files():
    """載入所有 moptt_*.json 檔案"""
    json_files = glob.glob('moptt_*.json')
    board_data = {}
    for file in json_files:
        board_name = file.replace('moptt_', '').replace('.json', '')
        try:
            print(f"載入 {file} 中...")
            board_data[board_name] = load_json_file(file)
        except Exception as e:
            print(f"Error loading {file}: {e}")
    return board_data

def find_top_comments_posts(board_data, top_n=20):
    """找出所有版位中 total_comments 最多的前 N 篇文章"""
    all_posts = []
    for board, posts in board_data.items():
        for post in posts:
            # 檢查 comments_data 和 total_comments 是否存在
            if 'comments_data' in post and 'total_comments' in post['comments_data']:
                post_info = {
                    'board': board,
                    'title': post.get('title', ''),
                    'url': post.get('url', ''),
                    'total_comments': post['comments_data']['total_comments'],
                    'date': post.get('acceptedDate', '').split('T')[0]  # 只取日期部分
                }
                all_posts.append(post_info)
    
    # 根據 total_comments 排序
    sorted_posts = sorted(all_posts, 
                        key=lambda x: int(x['total_comments']) if x['total_comments'] is not None else 0, 
                        reverse=True)
    return sorted_posts[:top_n]

def search_posts_by_keywords_and_time(board_data, keywords, start_time, end_time):
    """搜尋特定時間區間內包含關鍵字的文章"""
    start_datetime = datetime.strptime(start_time, "%Y-%m-%d")
    end_datetime = datetime.strptime(end_time, "%Y-%m-%d")
    
    matching_posts = []
    total_count = 0
    for board, posts in board_data.items():
        for post in posts:
            try:
                # 使用 acceptedDate 欄位，並轉換成 datetime 物件
                post_time_str = post.get('acceptedDate', '').split('T')[0]  # 只取日期部分
                post_time = datetime.strptime(post_time_str, "%Y-%m-%d")
                
                if start_datetime <= post_time <= end_datetime:
                    title = post.get('title', '').lower()
                    content = ''
                    if 'comments_data' in post and 'content' in post['comments_data']:
                        content = post['comments_data']['content'].lower()
                    
                    if any(keyword.lower() in title or keyword.lower() in content 
                          for keyword in keywords):
                        total_count += 1
                        matching_posts.append({
                            'board': board,
                            'title': post['title'],
                            'date': post_time_str,
                            'url': post['url']
                        })
            except (ValueError, AttributeError) as e:
                continue
    
    # 印出找到的文章詳細資訊
    if matching_posts:
        print("\n找到的文章列表：")
        for post in matching_posts:
            print(f"版面：{post['board']}")
            print(f"標題：{post['title']}")
            print(f"日期：{post['date']}")
            print(f"網址：{post['url']}")
            print()
    
    return total_count

def count_keyword_by_board(board_data, keywords):
    """計算關鍵字在各個版位出現的次數
    
    Args:
        board_data: 版面資料
        keywords: 關鍵字列表，可以是單一字串或字串列表
    """
    if isinstance(keywords, str):
        keywords = [keywords]
    
    counts = {}
    matching_posts = {}  # 用於儲存符合條件的文章
    
    for board, posts in board_data.items():
        board_count = 0
        board_matching_posts = []
        
        for post in posts:
            title = post.get('title', '').lower()
            content = ''
            if 'comments_data' in post and 'content' in post['comments_data']:
                content = post['comments_data']['content'].lower()
            
            # 檢查所有關鍵字是否都出現在文章中
            if all(keyword.lower() in (title + ' ' + content) for keyword in keywords):
                board_count += 1
                board_matching_posts.append({
                    'title': post.get('title', ''),
                    'url': post.get('url', ''),
                    'date': post.get('acceptedDate', '').split('T')[0]
                })
        
        if board_count > 0:
            counts[board] = board_count
            matching_posts[board] = board_matching_posts
    
    # 印出詳細資訊
    print(f"\n包含所有關鍵字 {', '.join(keywords)} 的文章列表：")
    for board in sorted(matching_posts.keys(), key=lambda x: counts[x], reverse=True):
        print(f"\n{board} 版 (共 {counts[board]} 篇)：")
        for post in matching_posts[board]:
            print(f"標題：{post['title']}")
            print(f"日期：{post['date']}")
            print(f"網址：{post['url']}")
            print()
    
    return counts

def find_most_common_strings(board_data, board_name, top_n=20):
    """找出特定版位最常出現的字串"""
    if board_name not in board_data:
        return []
    
    # 將所有文章的標題和內容合併
    text = ""
    for post in board_data[board_name]:
        # 加入標題
        text += post.get('title', '') + " "
        
        # 加入文章內容
        if 'comments_data' in post and 'content' in post['comments_data']:
            text += post['comments_data']['content'] + " "
            
            # 加入留言內容
            if 'comments' in post['comments_data']:
                for comment in post['comments_data']['comments']:
                    if 'content' in comment:
                        text += comment['content'] + " "
    
    # 使用正則表達式找出中文詞組（2-4個字）
    words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
    
    # 過濾掉一些常見但無意義的詞組（可以根據需要添加更多）
    stop_words = {'推推', '推文', '感謝', '謝謝', '這個', '那個', '所以', '因為', '可是', '但是', '什麼', '如果', '的話'}
    filtered_words = [word for word in words if word not in stop_words]
    
    return Counter(filtered_words).most_common(top_n)

def main():
    # 載入所有 JSON 檔案
    print("載入資料中...")
    board_data = load_all_json_files()
    
    while True:
        print("\n請選擇要執行的功能：")
        print("1. 顯示所有版位留言數最多的前二十篇")
        print("2. 搜尋特定時間區段內包含關鍵字的文章總數")
        print("3. 計算關鍵字在各版位的出現次數")
        print("4. 顯示特定版位最常出現的前二十個字串")
        print("5. 退出")
        
        choice = input("請輸入選項（1-5）：")
        
        if choice == '1':
            top_posts = find_top_comments_posts(board_data)
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
            
            total_count = search_posts_by_keywords_and_time(board_data, keywords, start_date, end_date)
            print(f"\n在指定時間區間內，包含關鍵字的文章總數：{total_count}")
        
        elif choice == '3':
            keywords = input("請輸入關鍵字（多個關鍵字請用空格分隔）：").split()
            counts = count_keyword_by_board(board_data, keywords)
            print(f"\n包含所有關鍵字的文章在各版位的出現次數：")
            for board, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
                print(f"{board}: {count} 篇")
        
        elif choice == '4':
            board_name = input("請輸入要分析的版位名稱（例如：Beauty）：")
            common_strings = find_most_common_strings(board_data, board_name)
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
