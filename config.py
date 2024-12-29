# 文章輸出欄位設定
POST_FIELDS = {
    'title': True,        # 文章標題
    'url': True,         # 文章網址
    'hits': True,        # 點擊數
    'acceptedDate': True, # 發文日期
    'id': False,         # 文章ID
    'timestamp': False,  # 時間戳記
    'number': True       # 文章編號
}

# 留言輸出欄位設定
COMMENT_FIELDS = {
    'tag': True,         # 留言標籤 (推/噓/→)
    'content': True,     # 留言內容
    'total_comments': True,  # 總留言數
    'like_count': True,     # 推文數
    'dislike_count': True,  # 噓文數
    'neutral_count': True   # 箭頭數
}
