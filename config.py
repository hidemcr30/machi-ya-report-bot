"""
設定管理モジュール
各スクリプトで使用される定数と設定値を管理
"""
import os
from typing import List, Dict

# --- ファイルパス設定 ---
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

# --- Google Sheets設定 ---
SPREADSHEET_CONFIGS = {
    "chokkin": {
        "id": "1GEiRKTI8Yb5e420fRKLIxQJHCTIfhvCvraGo1QEohZo",
        "sheet_name": "53期"
    },
    "production": {
        "id": "1z3HB9R90zlobgc05v4u2tGFTHHsBs9uOeyEIBPwJus8",
        "sheet_name": "新machi-ya"
    },
    "ga4": {
        "id": "1z3HB9R90zlobgc05v4u2tGFTHHsBs9uOeyEIBPwJus8",
        "sheet_name": "新machi-ya"
    }
}

# --- GA4設定 ---
GA4_PROPERTY_ID = "267526441"

# --- OAuth スコープ設定 ---
SCOPES = {
    "sheets_only": ["https://www.googleapis.com/auth/spreadsheets"],
    "sheets_and_analytics": [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/analytics.readonly"
    ]
}

# --- ネットワーク設定 ---
REQUEST_TIMEOUT = 10  # 秒
MAX_RETRIES = 3

# --- バッチ処理設定 ---
BATCH_SIZE = 100
PROGRESS_UPDATE_INTERVAL = 1  # 秒

# --- CAMPFIRE設定 ---
CAMPFIRE_BASE_URL = "https://camp-fire.jp/projects"
CAMPFIRE_SELECTORS = {
    "amount": "p.backer-amount",
    "count": "p.backer"
}

# --- 日付フォーマット ---
DATE_FORMAT = "%Y/%m/%d"

# --- UI設定 ---
UI_CONFIG = {
    "min_row": 2,
    "default_batch_size": 10,
    "progress_sleep": 1
}

# --- エラーメッセージ ---
ERROR_MESSAGES = {
    "no_id": "IDなし",
    "fetch_failed": "取得不可",
    "date_parse_error": "日付解析エラー",
    "skip": "スキップ",
    "network_error": "ネットワークエラー",
    "auth_error": "認証エラー",
    "sheets_error": "シートエラー"
}

# --- ログ設定 ---
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
}


def get_spreadsheet_config(config_name: str) -> Dict[str, str]:
    """
    スプレッドシート設定を取得
    
    Args:
        config_name: 設定名 ("chokkin", "production", "ga4")
    
    Returns:
        スプレッドシート設定辞書
    
    Raises:
        KeyError: 設定名が存在しない場合
    """
    if config_name not in SPREADSHEET_CONFIGS:
        raise KeyError(f"未知の設定名: {config_name}")
    
    return SPREADSHEET_CONFIGS[config_name]


def get_scopes(scope_type: str) -> List[str]:
    """
    OAuth スコープを取得
    
    Args:
        scope_type: スコープタイプ ("sheets_only", "sheets_and_analytics")
    
    Returns:
        スコープのリスト
    
    Raises:
        KeyError: スコープタイプが存在しない場合
    """
    if scope_type not in SCOPES:
        raise KeyError(f"未知のスコープタイプ: {scope_type}")
    
    return SCOPES[scope_type]


def validate_environment() -> bool:
    """
    実行環境の妥当性を検証
    
    Returns:
        環境が妥当かどうかの真偽値
    """
    required_files = [CREDENTIALS_FILE]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"必要なファイルが見つかりません: {file_path}")
            return False
    
    return True


# --- 環境変数からの設定上書き（オプション） ---
def load_env_overrides():
    """
    環境変数から設定を上書き（セキュリティ向上のため）
    """
    global GA4_PROPERTY_ID
    
    # 環境変数からGA4プロパティIDを取得（設定されている場合）
    env_ga4_id = os.getenv("GA4_PROPERTY_ID")
    if env_ga4_id:
        GA4_PROPERTY_ID = env_ga4_id
    
    # 他の機密情報も同様に環境変数から取得可能


# 初期化時に環境変数の確認
load_env_overrides()