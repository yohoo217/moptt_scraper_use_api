import json
import pandas as pd
import sys
import os
import glob
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_google_sheets_credentials():
    """取得 Google Sheets API 認證"""
    creds = None
    # token.pickle 儲存使用者的存取和更新令牌
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # 如果沒有可用的（有效的）憑證，讓使用者登入
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"更新憑證時發生錯誤：{str(e)}")
                # 刪除過期的 token.pickle
                if os.path.exists('token.pickle'):
                    os.remove('token.pickle')
                return None
        else:
            try:
                if not os.path.exists('credentials.json'):
                    print("\n錯誤：找不到 credentials.json 檔案")
                    print("請確保您已經：")
                    print("1. 從 Google Cloud Console 下載了正確的憑證檔案")
                    print("2. 選擇了「桌面應用程式」作為應用程式類型")
                    print("3. 將檔案重新命名為 credentials.json 並放在正確的目錄中")
                    return None
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                try:
                    creds = flow.run_local_server(port=0)
                except Exception as auth_error:
                    error_str = str(auth_error)
                    if "Access blocked" in error_str:
                        print("\n錯誤：應用程式尚未通過 Google 驗證")
                        print("\n請按照以下步驟設定：")
                        print("1. 前往 Google Cloud Console")
                        print("2. 在左側選單中選擇「OAuth 同意畫面」")
                        print("3. 在「測試用戶」區域中添加您的 Google 帳號")
                        print("4. 確保您使用已添加為測試用戶的 Google 帳號進行授權")
                        print("\n如果問題持續發生，您也可以：")
                        print("- 確認專案已啟用了 Google Sheets API")
                        print("- 檢查 OAuth 同意畫面中的應用程式資訊是否完整")
                        return None
                    else:
                        print(f"\n認證過程發生錯誤：{error_str}")
                        return None
                    
            except Exception as e:
                print(f"取得新憑證時發生錯誤：{str(e)}")
                return None
                
        # 儲存憑證以供下次使用
        try:
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        except Exception as e:
            print(f"儲存憑證時發生錯誤：{str(e)}")

    return creds

def create_new_spreadsheet(service, title):
    """建立新的 Google Sheets"""
    spreadsheet = {
        'properties': {
            'title': title
        }
    }
    try:
        spreadsheet = service.spreadsheets().create(body=spreadsheet,
                                              fields='spreadsheetId').execute()
        return spreadsheet.get('spreadsheetId')
    except HttpError as e:
        print(f"建立 spreadsheet 時發生錯誤：{str(e)}")
        return None

def create_new_sheet(service, spreadsheet_id, sheet_title):
    """建立新的工作表"""
    try:
        request = {
            'addSheet': {
                'properties': {
                    'title': sheet_title
                }
            }
        }
        
        body = {'requests': [request]}
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        return response['replies'][0]['addSheet']['properties']['sheetId']
    except Exception as e:
        print(f"建立新工作表時發生錯誤：{str(e)}")
        return None

def split_comments_horizontally(comments_list, max_chars=40000):
    """將留言列表橫向分割，每個部分不超過指定字元數"""
    result = []
    current_chunk = []
    current_length = 0
    
    for comment in comments_list:
        comment_str = json.dumps([comment], ensure_ascii=False)
        comment_length = len(comment_str)
        
        if current_length + comment_length > max_chars and current_chunk:
            result.append(json.dumps(current_chunk, ensure_ascii=False))
            current_chunk = [comment]
            current_length = comment_length
        else:
            current_chunk.append(comment)
            current_length += comment_length
    
    if current_chunk:
        result.append(json.dumps(current_chunk, ensure_ascii=False))
    
    return result

def process_json_file(input_file):
    """處理 JSON 檔案並轉換成 DataFrame"""
    try:
        # 讀取 JSON 檔案
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 處理資料
        processed_data = []
        max_comment_parts = 1  # 追蹤最大的留言分割數
        
        # 第一次遍歷：處理資料並找出最大分割數
        for item in data:
            comments_data = item.get('comments_data', {})
            row_data = {k: v for k, v in item.items() if k != 'comments_data'}
            
            # 新增留言統計
            row_data['total_comments'] = comments_data.get('total_comments', 0)
            row_data['like_count'] = comments_data.get('like_count', 0)
            row_data['dislike_count'] = comments_data.get('dislike_count', 0)
            row_data['neutral_count'] = comments_data.get('neutral_count', 0)
            
            # 分割留言
            comments = comments_data.get('comments', [])
            comments_parts = split_comments_horizontally(comments)
            row_data['comments_parts'] = comments_parts
            
            max_comment_parts = max(max_comment_parts, len(comments_parts))
            processed_data.append(row_data)
        
        # 建立 DataFrame 欄位
        columns = list(processed_data[0].keys())
        columns.remove('comments_parts')
        for i in range(max_comment_parts):
            columns.append(f'comments_{i+1}')
        
        # 建立最終資料
        final_data = []
        for row in processed_data:
            comments_parts = row.pop('comments_parts')
            row_data = list(row.values())
            # 加入分割的留言
            row_data.extend(comments_parts)
            # 如果留言部分不足，補充空值
            while len(row_data) < len(columns):
                row_data.append('')
            final_data.append(row_data)
        
        return pd.DataFrame(final_data, columns=columns)
        
    except Exception as e:
        print(f"處理檔案時發生錯誤：{str(e)}")
        return None

def update_sheet_values(service, spreadsheet_id, data_df):
    """更新 Google Sheets 的值"""
    try:
        # 準備要上傳的數據
        values = [data_df.columns.values.tolist()]  # 標題列
        values.extend(data_df.values.tolist())      # 數據列

        # 檢查每個儲存格的內容長度
        max_length = 0
        for row in values:
            for cell in row:
                if isinstance(cell, str):
                    length = len(cell)
                    if length > max_length:
                        max_length = length
                    if length > 50000:
                        print(f"警告：發現超過 50,000 字元的儲存格內容（長度：{length}）")
                        return None

        # 分批上傳數據
        BATCH_SIZE = 100  # 每次上傳100行
        SHEET_MAX_ROWS = 1000  # Google Sheets 每個工作表的最大行數
        total_rows = len(values)
        current_sheet = 1
        
        for start_idx in range(0, total_rows, BATCH_SIZE):
            end_idx = min(start_idx + BATCH_SIZE, total_rows)
            current_batch = values[start_idx:end_idx]
            
            # 計算目前應該使用的工作表
            sheet_number = (start_idx // SHEET_MAX_ROWS) + 1
            
            # 如果需要新的工作表
            if sheet_number > current_sheet:
                sheet_title = f'Sheet{sheet_number}'
                print(f"\n建立新工作表：{sheet_title}")
                sheet_id = create_new_sheet(service, spreadsheet_id, sheet_title)
                if sheet_id is None:
                    return None
                current_sheet = sheet_number
                
                # 在新工作表的第一行加入標題
                if start_idx > 0:
                    header_body = {'values': [values[0]]}  # 只有標題行
                    service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f'{sheet_title}!A1',
                        valueInputOption='RAW',
                        body=header_body
                    ).execute()
            
            # 計算在當前工作表中的相對位置
            relative_start = (start_idx % SHEET_MAX_ROWS) + 1
            sheet_name = f'Sheet{sheet_number}'
            range_name = f'{sheet_name}!A{relative_start}'
            
            # 重試機制
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    body = {'values': current_batch}
                    service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=range_name,
                        valueInputOption='RAW',
                        body=body
                    ).execute()
                    print(f"成功上傳第 {start_idx + 1} 到 {end_idx} 行 (工作表：{sheet_name})")
                    break
                except HttpError as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        print(f"上傳第 {start_idx + 1} 到 {end_idx} 行失敗：{str(e)}")
                        if "Internal error" in str(e):
                            print("Google Sheets API 內部錯誤，請稍後再試")
                        return None
                    print(f"重試第 {retry_count} 次...")
                    import time
                    time.sleep(2)  # 等待2秒後重試
        
        # 為每個工作表調整欄寬
        for sheet_num in range(1, current_sheet + 1):
            try:
                print(f"\n正在調整工作表 Sheet{sheet_num} 的欄寬...")
                requests = []
                for i in range(len(data_df.columns)):
                    requests.append({
                        "autoResizeDimensions": {
                            "dimensions": {
                                "sheetId": sheet_num - 1,  # 第一個工作表的 ID 是 0
                                "dimension": "COLUMNS",
                                "startIndex": i,
                                "endIndex": i + 1
                            }
                        }
                    })
                
                # 重試機制
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        service.spreadsheets().batchUpdate(
                            spreadsheetId=spreadsheet_id,
                            body={"requests": requests}
                        ).execute()
                        print(f"成功調整工作表 Sheet{sheet_num} 的欄寬")
                        break
                    except Exception as e:
                        retry_count += 1
                        if retry_count == max_retries:
                            print(f"調整工作表 Sheet{sheet_num} 欄寬時發生錯誤：{str(e)}")
                        else:
                            print(f"重試調整欄寬第 {retry_count} 次...")
                            time.sleep(2)
                
            except Exception as e:
                print(f"調整工作表 Sheet{sheet_num} 欄寬時發生錯誤：{str(e)}")
        
        return True
        
    except HttpError as e:
        print(f"更新表格內容時發生錯誤：{str(e)}")
        if "Your input contains more than the maximum of 50000 characters in a single cell" in str(e):
            print("\n提示：已自動將留言內容分割成多個欄位")
        return None

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

def main():
    # 選擇 JSON 檔案
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = list_json_files()
        if input_file is None:
            return

    # 處理 JSON 檔案
    df = process_json_file(input_file)
    if df is None:
        return

    try:
        # 取得 Google Sheets API 認證
        print("正在連接 Google Sheets...")
        creds = get_google_sheets_credentials()
        if creds is None:
            print("無法取得 Google Sheets 認證，請檢查錯誤訊息並重試")
            return
            
        service = build('sheets', 'v4', credentials=creds)

        # 建立新的 spreadsheet
        spreadsheet_title = f"PTT_{os.path.splitext(input_file)[0]}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
        spreadsheet_id = create_new_spreadsheet(service, spreadsheet_title)
        if spreadsheet_id is None:
            return
        
        print(f"已建立新的 spreadsheet：{spreadsheet_title}")
        
        # 更新表格內容
        print("正在上傳資料到 Google Sheets...")
        update_sheet_values(service, spreadsheet_id, df)
        print(f"\n成功上傳資料！")
        print(f"Spreadsheet URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")

    except Exception as e:
        print(f"上傳到 Google Sheets 時發生錯誤：{str(e)}")

if __name__ == '__main__':
    main()
