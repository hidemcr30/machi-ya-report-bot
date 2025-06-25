# CLAUDE.md - 開発仕様書・実装方針

このドキュメントは、Claude Code による今後の開発・保守作業のための技術仕様書です。

## 🏗️ アーキテクチャ概要

### システム構成
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit UI  │───▶│  Business Logic  │───▶│  External APIs  │
│                 │    │                  │    │                 │
│ ├ 貯金箱ツール   │    │ ├ utils.py      │    │ ├ CAMPFIRE      │
│ ├ GA4ツール     │    │ ├ config.py     │    │ ├ Google Sheets │
│ └ 本番ツール     │    │ └ 各main*.py    │    │ └ Google GA4    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### モジュール依存関係
```
machi-ya_chokkin_report.py
main_oauth_ga4.py           ─┬─▶ utils.py ─┬─▶ Google APIs
main_oauth_production.py    ─┘             │
                                          └─▶ config.py
```

## 📋 開発環境仕様

### 必須環境
- **Python**: 3.9+
- **OS**: macOS (Automator連携のため)
- **IDE**: Claude Code対応環境
- **認証**: Google OAuth 2.0

### 依存ライブラリ
```python
# Core libraries
streamlit>=1.28.0
pandas>=1.5.0
requests>=2.28.0
beautifulsoup4>=4.11.0

# Google APIs
google-auth>=2.17.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.1.0
google-api-python-client>=2.70.0
google-analytics-data>=0.16.0

# Type hints
typing_extensions>=4.4.0
```

## 🎯 実装方針

### 1. 設計原則
- **単一責任原則**: 各関数は一つの責任のみを持つ
- **DRY原則**: コードの重複を避ける
- **設定外部化**: ハードコードを避け、config.pyで管理
- **例外安全**: 適切な例外処理でアプリケーションの安定性を確保

### 2. コーディング規約
```python
# 型ヒントを必須とする
def process_data(pj_id: str, target_date: datetime.date) -> Tuple[str, str]:
    pass

# 例外処理は具体的なエラークラスを使用
try:
    result = api_call()
except AuthenticationError as e:
    handle_auth_error(e)
except SheetsError as e:
    handle_sheets_error(e)

# 関数名は動詞+名詞の形式
def get_campfire_data(pj_id: str) -> Tuple[str, str]:
def process_project_data(service, row: int) -> Tuple[int, str, str]:
def write_sheet_batch(service, spreadsheet_id: str, batch_data: List[Dict]) -> None:
```

### 3. エラーハンドリング戦略
```python
# カスタム例外クラスの使用
class AuthenticationError(Exception): pass
class ScrapingError(Exception): pass
class SheetsError(Exception): pass
class GA4Error(Exception): pass

# 例外の適切な伝播
def low_level_function():
    try:
        # 危険な操作
        pass
    except SpecificError as e:
        raise CustomError(f"詳細なエラー情報: {str(e)}")

def high_level_function():
    try:
        low_level_function()
    except CustomError as e:
        st.error(f"ユーザー向けメッセージ: {str(e)}")
```

## 🔧 開発ガイドライン

### 新機能追加時の手順

#### 1. 設定の追加
```python
# config.py に新しい設定を追加
NEW_FEATURE_CONFIG = {
    "api_endpoint": "https://api.example.com",
    "timeout": 30,
    "batch_size": 50
}
```

#### 2. ユーティリティ関数の実装
```python
# utils.py に共通機能を追加
def get_new_api_data(
    endpoint: str, 
    params: Dict[str, str],
    timeout: int = 30
) -> Dict[str, Any]:
    """
    新しいAPIからデータを取得
    
    Args:
        endpoint: APIエンドポイント
        params: リクエストパラメータ
        timeout: タイムアウト時間
    
    Returns:
        APIレスポンスデータ
    
    Raises:
        ApiError: API呼び出しに失敗した場合
    """
    try:
        response = requests.get(endpoint, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise ApiError(f"API呼び出しエラー: {str(e)}")
```

#### 3. メインスクリプトでの利用
```python
# main_new_feature.py
from utils import get_new_api_data, AuthenticationError
from config import get_new_feature_config

try:
    config = get_new_feature_config()
    data = get_new_api_data(config["api_endpoint"], params)
    # 処理続行
except AuthenticationError as e:
    st.error(f"認証エラー: {str(e)}")
```

### 既存機能の修正時の注意点

#### 1. 後方互換性の維持
```python
# 悪い例: 既存の関数シグネチャを変更
def get_campfire_data(pj_id: str, new_param: str) -> Tuple[str, str]:
    pass

# 良い例: デフォルト値で互換性を維持
def get_campfire_data(pj_id: str, new_param: Optional[str] = None) -> Tuple[str, str]:
    pass
```

#### 2. 段階的な機能追加
```python
# フィーチャーフラグによる段階的リリース
def process_data_with_new_feature(data: List[str], enable_new_feature: bool = False):
    if enable_new_feature:
        return new_processing_logic(data)
    else:
        return legacy_processing_logic(data)
```

## 🧪 テスト戦略

### 単体テスト
```python
# test_utils.py (将来的な実装例)
import pytest
from utils import get_campfire_data, clean_numeric_string

def test_clean_numeric_string():
    assert clean_numeric_string("¥123,456円") == "123456"
    assert clean_numeric_string("") == ""
    assert clean_numeric_string("abc123def") == "123"

@pytest.mark.parametrize("input,expected", [
    ("2024/01/01", True),
    ("invalid", False),
    ("2024-01-01", False),
])
def test_is_valid_date_string(input, expected):
    assert is_valid_date_string(input) == expected
```

### 統合テスト
```python
# integration_test.py (将来的な実装例)
def test_full_workflow():
    """E2Eテストのサンプル"""
    # 1. 認証テスト
    service = get_gsheet_service(test_scopes)
    assert service is not None
    
    # 2. データ取得テスト
    test_data = read_sheet_range(service, test_sheet_id, "A1:B2")
    assert len(test_data) > 0
    
    # 3. 書き込みテスト
    write_sheet_cell(service, test_sheet_id, "C1", "test_value")
```

## 📊 監視・ログ仕様

### ログレベル定義
```python
# config.py でのログ設定
import logging

logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format=LOG_CONFIG["format"]
)

logger = logging.getLogger(__name__)

# 使用例
logger.info("データ取得開始")
logger.warning("予期しないレスポンス形式")
logger.error("API呼び出し失敗", exc_info=True)
```

### パフォーマンス監視
```python
# utils.py でのパフォーマンス計測例
import time
from functools import wraps

def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"{func.__name__} 実行時間: {end_time - start_time:.2f}秒")
        return result
    return wrapper

@measure_time
def get_campfire_data(pj_id: str) -> Tuple[str, str]:
    # 実装
    pass
```

## 🔒 セキュリティ考慮事項

### 1. 認証情報の管理
```python
# 環境変数での機密情報管理
import os

def get_sensitive_config():
    return {
        "api_key": os.getenv("API_KEY"),
        "secret": os.getenv("API_SECRET")
    }

# credentials.json の適切な権限設定
# chmod 600 credentials.json
```

### 2. API レート制限対応
```python
# utils.py でのレート制限対応
import time
from functools import wraps

def rate_limit(calls_per_second: int = 1):
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator

@rate_limit(calls_per_second=2)  # 秒間2回まで
def get_campfire_data(pj_id: str) -> Tuple[str, str]:
    # 実装
    pass
```

## 🚀 デプロイメント仕様

### 本番環境要件
- Python 3.9+ (macOS標準)
- 必要なライブラリがインストール済み
- `credentials.json` が適切に配置
- Automator による定期実行設定

### 設定ファイルの環境別管理
```python
# config.py での環境別設定例
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    SPREADSHEET_CONFIGS["production"]["id"] = os.getenv("PROD_SHEET_ID")
    GA4_PROPERTY_ID = os.getenv("PROD_GA4_PROPERTY_ID")
```

## 📝 コード修正時のチェックリスト

### 新機能追加時
- [ ] 型ヒントを追加
- [ ] 適切な例外処理を実装
- [ ] config.py に設定を外部化
- [ ] ドキュメントコメントを記述
- [ ] 既存機能への影響を確認
- [ ] エラーハンドリングをテスト

### バグ修正時
- [ ] 根本原因を特定
- [ ] 再発防止策を実装
- [ ] 関連する他の箇所への影響を確認
- [ ] ログ出力でデバッグ情報を追加

### リファクタリング時
- [ ] 既存の動作を完全に保持
- [ ] テストケースで動作確認
- [ ] パフォーマンスの劣化がないか確認
- [ ] コードの可読性が向上しているか確認

## 🔄 継続的改善方針

### 技術的改善
1. **型安全性の向上**: mypy による静的型チェック導入
2. **テスト自動化**: pytest による自動テストスイート構築
3. **CI/CD**: GitHub Actions による自動テスト・デプロイ
4. **監視強化**: 詳細なログ分析・アラート機能

### 機能的改善
1. **ユーザビリティ**: より直感的なUI設計
2. **パフォーマンス**: 非同期処理による高速化
3. **信頼性**: 自動リトライ・フェイルセーフ機能
4. **スケーラビリティ**: 大量データ処理の最適化

---

**Claude Code での開発時の重要事項**:
- このドキュメントを参照して一貫した実装を行う
- 新機能追加時は必ずこの仕様に従う
- 既存コードとの整合性を保つ
- セキュリティとパフォーマンスを常に考慮する

**最終更新**: 2024年12月  
**作成者**: Claude Code