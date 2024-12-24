import json
import pandas as pd
import sys
import os
import glob
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

# Google Sheets API 設置
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_google_sheets_credentials():
    """獲取 Google Sheets API 認證"""
    creds = None
    # 檢查是否有已存在的 token
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # 如果沒有有效的認證（或沒有認證）
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("錯誤：找不到 credentials.json 檔案")
                print("請先從 Google Cloud Console 下載 OAuth 2.0 憑證檔案並命名為 credentials.json")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 儲存認證以供後續使用
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def upload_to_google_sheets(df, spreadsheet_name):
    """上傳 DataFrame 到 Google Sheets"""
    try:
        creds = get_google_sheets_credentials()
        if not creds:
            return False
        
        service = build('sheets', 'v4', credentials=creds)
        
        # 創建新的試算表
        spreadsheet = {
            'properties': {
                'title': spreadsheet_name
            }
        }
        spreadsheet = service.spreadsheets().create(body=spreadsheet,
                                                  fields='spreadsheetId').execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')
        
        # 準備數據
        values = [df.columns.values.tolist()]  # 標題行
        values.extend(df.values.tolist())      # 數據行
        
        body = {
            'values': values
        }
        
        # 寫入數據
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='A1',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"已創建新的 Google Sheets：https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        return True
        
    except Exception as e:
        print(f"上傳到 Google Sheets 時發生錯誤：{str(e)}")
        return False

def list_json_files():
    """列出當前目錄下所有的 JSON 檔案"""
    json_files = glob.glob("*.json")
    if not json_files:
        print("當前目錄下沒有找到 JSON 檔案")
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

def convert_json_to_csv(input_file, output_file=None):
    """
    Convert a JSON file containing PTT board data to CSV format
    
    Args:
        input_file (str): Path to the input JSON file
        output_file (str, optional): Path to the output CSV file. If not provided,
                                   will use the same name as input file with .csv extension
    """
    try:
        # Read JSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Process the data to flatten the comments
        processed_data = []
        for item in data:
            comments_data = item.get('comments_data', {})
            base_data = {k: v for k, v in item.items() if k != 'comments_data'}
            
            # Add comment statistics
            base_data['total_comments'] = comments_data.get('total_comments', 0)
            base_data['like_count'] = comments_data.get('like_count', 0)
            base_data['dislike_count'] = comments_data.get('dislike_count', 0)
            base_data['neutral_count'] = comments_data.get('neutral_count', 0)
            
            # Convert comments list to string to avoid nested structure
            comments = comments_data.get('comments', [])
            comments_str = json.dumps(comments, ensure_ascii=False)
            base_data['comments'] = comments_str
            
            processed_data.append(base_data)
        
        # Convert to DataFrame
        df = pd.DataFrame(processed_data)
        
        # If output_file is not specified, use input filename with .csv extension
        if output_file is None:
            output_file = os.path.splitext(input_file)[0] + '.csv'
        
        # Save to CSV
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"成功將 {input_file} 轉換為 {output_file}")
        
        # 詢問是否要上傳到 Google Sheets
        while True:
            upload = input("\n是否要上傳到 Google Sheets? (y/n): ").lower()
            if upload in ['y', 'n']:
                break
            print("請輸入 y 或 n")
        
        if upload == 'y':
            spreadsheet_name = os.path.splitext(os.path.basename(input_file))[0]
            if upload_to_google_sheets(df, spreadsheet_name):
                print("成功上傳到 Google Sheets！")
        
        return df
        
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {input_file}")
    except json.JSONDecodeError:
        print(f"錯誤：{input_file} 不是有效的 JSON 檔案")
    except Exception as e:
        print(f"發生錯誤：{str(e)}")

def main():
    if len(sys.argv) > 1:
        # 如果提供命令列參數，直接使用
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        # 否則進入互動模式
        input_file = list_json_files()
        if input_file is None:
            return
        output_file = None
    
    convert_json_to_csv(input_file, output_file)

if __name__ == "__main__":
    main()
