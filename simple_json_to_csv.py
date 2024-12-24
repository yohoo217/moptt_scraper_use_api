import json
import csv
import sys
from datetime import datetime
from dateutil import parser
import glob

def clean_text(text):
    """清理文字，移除可能造成 CSV 格式問題的字元"""
    if not text:
        return ''
    # 移除換行符和多餘的空白
    text = ' '.join(str(text).split())
    # 移除引號，避免 CSV 格式問題
    text = text.replace('"', '').replace("'", '')
    # 移除逗號，因為這是 CSV 分隔符
    text = text.replace(',', '；')
    return text

def convert_to_simple_csv(input_file, output_file=None):
    """將 JSON 資料轉換為簡單的 CSV 格式，每則留言一行"""
    try:
        # 讀取 JSON 檔案
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 如果沒有指定輸出檔案，使用預設名稱
        if output_file is None:
            output_file = input_file.replace('.json', '_simple.csv')
        
        # 定義欄位
        fields = ['id', 'title', 'time', 'views', 'comments', 'likes', 'dislikes', 
                 'neutral', 'content', 'comment_number', 'comment_type', 'comment_text']
        
        # 寫入 CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            
            # 處理每一筆資料
            for item in data:
                comments_data = item.get('comments_data', {})
                
                # 處理時間格式
                try:
                    dt = parser.parse(item.get('timestamp', ''))
                    time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    time_str = ''
                
                # 處理文章內容
                content = clean_text(item.get('description', ''))
                
                # 基本資料
                base_row = {
                    'id': item.get('id', ''),
                    'title': clean_text(item.get('title', '')),
                    'time': time_str,
                    'views': str(item.get('hits', 0)),
                    'comments': str(comments_data.get('total_comments', 0)),
                    'likes': str(comments_data.get('like_count', 0)),
                    'dislikes': str(comments_data.get('dislike_count', 0)),
                    'neutral': str(comments_data.get('neutral_count', 0)),
                    'content': content
                }
                
                # 處理留言
                comments = comments_data.get('comments', [])
                if not comments:
                    # 如果沒有留言，寫入一行基本資料
                    base_row.update({
                        'comment_number': '0',
                        'comment_type': '',
                        'comment_text': ''
                    })
                    writer.writerow(base_row)
                else:
                    # 為每則留言寫入一行
                    for i, comment in enumerate(comments, 1):
                        text = clean_text(comment.get('content', ''))
                        if text and not text.startswith('http'):  # 排除圖片連結
                            row = base_row.copy()
                            row.update({
                                'comment_number': str(i),
                                'comment_type': comment.get('type', ''),  # 推/噓/→
                                'comment_text': text
                            })
                            writer.writerow(row)
        
        print(f"\n成功將 {input_file} 轉換為 {output_file}")
        print(f"\n欄位資訊：")
        print("- id: 文章ID")
        print("- title: 標題")
        print("- time: 發文時間")
        print("- views: 觀看次數")
        print("- comments: 總留言數")
        print("- likes: 推文數")
        print("- dislikes: 噓文數")
        print("- neutral: 中立數")
        print("- content: 文章內容")
        print("- comment_number: 留言編號")
        print("- comment_type: 留言類型（推/噓/→）")
        print("- comment_text: 留言內容")
        
        return True
        
    except Exception as e:
        print(f"錯誤：{str(e)}")
        return False

def list_json_files():
    """列出當前目錄下所有的 JSON 檔案"""
    json_files = glob.glob("*.json")
    if not json_files:
        print("\n當前目錄下沒有找到 JSON 檔案")
        return None
    
    print("\n可用的 JSON 檔案：")
    for i, file in enumerate(json_files, 1):
        print(f"{i}. {file}")
    
    while True:
        try:
            choice = input("\n請選擇要轉換的檔案編號 (輸入 q 退出): ")
            if choice.lower() == 'q':
                return None
            choice = int(choice)
            if 1 <= choice <= len(json_files):
                return json_files[choice-1]
            print("無效的選擇，請重新輸入")
        except ValueError:
            print("請輸入有效的數字")

def main():
    # 如果提供命令列參數，直接使用
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        # 否則進入互動模式
        input_file = list_json_files()
        if input_file is None:
            return
        output_file = None
    
    if convert_to_simple_csv(input_file, output_file):
        print("\n轉換完成！")
    else:
        print("\n轉換失敗！")

if __name__ == "__main__":
    main()
