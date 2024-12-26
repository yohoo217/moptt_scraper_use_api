import json
import csv
import sys
from datetime import datetime
from dateutil import parser
import glob
import os

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

def convert_to_simple_csv(input_file, output_file=None, max_chars_per_cell=32000):
    """將 JSON 資料轉換為簡單的 CSV 格式，留言整合在同一個欄位中"""
    try:
        # 讀取 JSON 檔案
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 如果沒有指定輸出檔案，使用預設名稱
        if output_file is None:
            output_file = input_file.replace('.json', '_simple.csv')
        
        # 定義欄位
        base_fields = ['id', 'title', 'time', 'views', 'total_comments', 'likes', 'dislikes', 
                      'neutral', 'content', 'content_overflow']
        # 主要留言欄位和一個溢出欄位
        comment_fields = ['comments', 'comments_overflow']
        fields = base_fields + comment_fields
        
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
                
                # 處理文章內容，包含溢出處理
                full_content = clean_text(item.get('description', ''))
                if len(full_content) > max_chars_per_cell:
                    content = full_content[:max_chars_per_cell]
                    content_overflow = full_content[max_chars_per_cell:]
                else:
                    content = full_content
                    content_overflow = ''
                
                # 基本資料
                row = {
                    'id': item.get('id', ''),
                    'title': clean_text(item.get('title', '')),
                    'time': time_str,
                    'views': str(item.get('hits', 0)),
                    'total_comments': str(comments_data.get('total_comments', 0)),
                    'likes': str(comments_data.get('like_count', 0)),
                    'dislikes': str(comments_data.get('dislike_count', 0)),
                    'neutral': str(comments_data.get('neutral_count', 0)),
                    'content': content,
                    'content_overflow': content_overflow,
                    'comments': '',
                    'comments_overflow': ''
                }
                
                # 處理留言
                comments = comments_data.get('comments', [])
                if comments:
                    # 將所有有效留言組合成一個列表
                    valid_comments = []
                    for comment in comments:
                        text = clean_text(comment.get('content', ''))
                        if text and not text.startswith('http'):  # 排除圖片連結
                            comment_str = f"{comment.get('type', '')} {text}"
                            valid_comments.append(comment_str)
                    
                    # 將留言組合並分配到適當的欄位
                    if valid_comments:
                        current_cell = []
                        current_cell_length = 0
                        overflow_cell = []
                        
                        for comment in valid_comments:
                            comment_length = len(comment) + 1  # +1 for newline
                            
                            # 如果當前留言會導致超出限制，將後續留言放入溢出欄位
                            if current_cell_length + comment_length > max_chars_per_cell:
                                overflow_cell.append(comment)
                            else:
                                current_cell.append(comment)
                                current_cell_length += comment_length
                        
                        # 寫入主要留言欄位
                        if current_cell:
                            row['comments'] = '\n'.join(current_cell)
                        
                        # 寫入溢出留言欄位
                        if overflow_cell:
                            row['comments_overflow'] = '\n'.join(overflow_cell)
                
                writer.writerow(row)
        
        print(f"\n成功將 {input_file} 轉換為 {output_file}")
        print(f"\n欄位資訊：")
        print("- id: 文章ID")
        print("- title: 標題")
        print("- time: 發文時間")
        print("- views: 觀看次數")
        print("- total_comments: 總留言數")
        print("- likes: 推文數")
        print("- dislikes: 噓文數")
        print("- neutral: 中立數")
        print("- content: 文章內容")
        print("- content_overflow: 溢出的文章內容")
        print("- comments: 主要留言內容")
        print("- comments_overflow: 溢出的留言內容")
        
        return True
        
    except Exception as e:
        print(f"錯誤：{str(e)}")
        return False

def convert_all_json_files(max_chars_per_cell=32000):
    """轉換目錄下所有的 JSON 檔案為 CSV 格式"""
    json_files = glob.glob('*.json')
    if not json_files:
        print("找不到任何 JSON 檔案")
        return
    
    for json_file in json_files:
        output_file = json_file.replace('.json', '_simple.csv')
        print(f"正在轉換 {json_file} 到 {output_file}")
        convert_to_simple_csv(json_file, output_file, max_chars_per_cell)
    
    print(f"完成轉換 {len(json_files)} 個檔案")

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
    """主程式"""
    if len(sys.argv) < 2:
        print("使用方式：")
        print("1. 轉換單一檔案：python simple_json_to_csv.py <json檔案>")
        print("2. 轉換所有JSON檔案：python simple_json_to_csv.py --all")
        print("\n可用的JSON檔案：")
        list_json_files()
        return

    if sys.argv[1] == '--all':
        convert_all_json_files()
    else:
        input_file = sys.argv[1]
        if not input_file.endswith('.json'):
            print("錯誤：請指定 JSON 檔案")
            return
        if not os.path.exists(input_file):
            print(f"錯誤：找不到檔案 {input_file}")
            return
        
        convert_to_simple_csv(input_file)

if __name__ == "__main__":
    main()
