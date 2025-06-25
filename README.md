# Machi-ya Report Bot

CAMPFIREプロジェクトの情報を自動取得し、Google Sheetsに書き込むStreamlitアプリケーション群です。

## 📁 ファイル構成

```
machi-ya-report-bot/
├── README.md                    # プロジェクト概要・運用ガイド
├── CLAUDE.md                    # 開発仕様書・実装方針
├── config.py                   # 設定管理モジュール
├── utils.py                    # 共通ユーティリティ関数
├── machi-ya_chokkin_report.py  # 貯金箱プロジェクト金額更新ツール
├── main_oauth_ga4.py           # GA4セッション数更新ツール
├── main_oauth_production.py    # 本番環境金額・人数更新ツール
├── credentials.json            # Google API認証情報（非共有）
└── token.json                  # OAuth トークン（自動生成）
```

## 🎯 各スクリプトの目的

### 1. machi-ya_chokkin_report.py
- **目的**: CAMPFIREプロジェクトの金額データを取得・更新
- **対象**: 貯金箱関連プロジェクト
- **機能**: プロジェクトIDから金額を取得してD列に書き込み
- **スプレッドシート**: 53期シート

### 2. main_oauth_ga4.py
- **目的**: Google Analytics 4からセッション数を取得・更新
- **対象**: 新machi-yaプロジェクト
- **機能**: プロジェクトIDでフィルタしたセッション数をX列に書き込み
- **データソース**: GA4 API + Webスクレイピング

### 3. main_oauth_production.py
- **目的**: 本番環境での金額・人数データ取得・更新
- **対象**: 新machi-yaプロジェクト
- **機能**: 金額をN列、人数をP列に一括書き込み
- **特徴**: バッチ処理による高速更新

## 🚀 セットアップ手順

### 1. 依存関係のインストール
```bash
pip install streamlit pandas requests beautifulsoup4 google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client google-analytics-data
```

### 2. Google API設定
1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成
2. Google Sheets API と Google Analytics Data API を有効化
3. OAuth 2.0 クライアントIDを作成
4. `credentials.json`をダウンロードしてプロジェクトルートに配置

### 3. 実行方法
```bash
# 各スクリプトを個別に実行
streamlit run machi-ya_chokkin_report.py
streamlit run main_oauth_ga4.py
streamlit run main_oauth_production.py
```

## ⚙️ 運用方針

### 自動化設定
- **Mac Automator**で各スクリプトを定期実行
- スクリプト名は変更禁止（Automator設定に影響）
- 実行ログは自動でStreamlitに表示

### データ更新フロー
1. **データ取得フェーズ**: 対象範囲のデータを一括取得・検証
2. **確認フェーズ**: 取得結果をテーブル表示で目視確認
3. **書き込みフェーズ**: 確認後にスプレッドシートへ一括書き込み

### セキュリティ対策
- `credentials.json`と`token.json`はGit管理対象外
- OAuth認証による安全なAPI アクセス
- 環境変数での機密情報管理をサポート

## 🔧 2024年12月リファクタリング成果

### 改善点
- **コード重複削除**: 認証処理・API操作を`utils.py`に共通化
- **設定一元化**: ハードコードされた値を`config.py`に移動
- **型安全性向上**: 型ヒント追加でIDEサポート強化
- **エラーハンドリング強化**: カスタム例外クラスによる適切な例外処理
- **保守性向上**: 単一責任原則に従った関数分離

### 技術的改善
- マジックナンバーの定数化
- バッチ処理サイズの設定化
- 日付フォーマットの統一
- エラーメッセージの標準化

## 🛠️ トラブルシューティング

### よくある問題

#### 1. 認証エラー
**症状**: `AuthenticationError: 認証ファイルが見つかりません`
**解決法**:
```bash
# credentials.jsonの存在確認
ls -la credentials.json

# ファイルが存在しない場合は Google Cloud Console から再ダウンロード
```

#### 2. スプレッドシートアクセスエラー
**症状**: `SheetsError: シート読み取りでエラー`
**解決法**:
1. スプレッドシートIDが正しいか確認
2. Google Sheets APIが有効になっているか確認
3. OAuth認証スコープに`spreadsheets`が含まれているか確認

#### 3. GA4データ取得エラー
**症状**: `GA4Error: GA4データ取得でエラー`
**解決法**:
1. GA4プロパティIDが正しいか確認（config.py内）
2. Google Analytics Data APIが有効か確認
3. 認証アカウントにGA4プロパティへのアクセス権限があるか確認

#### 4. スクレイピングエラー
**症状**: `ScrapingError: プロジェクト XXX のデータ取得でネットワークエラー`
**解決法**:
1. インターネット接続確認
2. CAMPFIREサイトのアクセス可能性確認
3. レート制限に引っかかっていないか確認（少し時間を置いて再実行）

#### 5. Streamlitアプリが起動しない
**症状**: `ModuleNotFoundError` または `ImportError`
**解決法**:
```bash
# 必要なモジュールの再インストール
pip install -r requirements.txt

# Python環境の確認
python --version
python -c "import streamlit; print('Streamlit OK')"
```

### デバッグ方法

#### ログレベル調整
```python
# config.py でログレベルを変更
LOG_CONFIG = {
    "level": "DEBUG",  # INFO から DEBUG に変更
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
}
```

#### 手動テスト
```python
# Pythonインタープリターで個別機能テスト
from utils import get_campfire_data
result = get_campfire_data("test_project_id")
print(result)
```

### パフォーマンス最適化

#### 大量データ処理時
- バッチサイズを調整（config.py の `BATCH_SIZE`）
- タイムアウト値を増加（config.py の `REQUEST_TIMEOUT`）
- 処理範囲を分割して実行

#### メモリ使用量削減
- セッション状態のクリア（Streamlit画面でブラウザリフレッシュ）
- 不要な変数の削除

## 📊 監視・メンテナンス

### 定期チェック項目
- [ ] OAuth トークンの有効期限（自動更新されるが念のため）
- [ ] スプレッドシートアクセス権限
- [ ] CAMPFIREサイトの構造変更（セレクタが無効になっていないか）
- [ ] GA4プロパティの設定変更
- [ ] 依存ライブラリの更新

### ログ確認
```bash
# Streamlitアプリのログ確認
# 各アプリの実行時にブラウザコンソールでエラー確認
```

### バックアップ
- 定期的に `credentials.json` をバックアップ
- 重要な設定変更前にコード全体をバックアップ

## 🔄 今後の改善計画

### 短期改善
- [ ] より詳細なログ出力機能
- [ ] リトライ機能の実装
- [ ] データ検証機能の強化

### 中期改善
- [ ] Web UIの改善（進捗表示・エラー通知）
- [ ] 複数プロジェクト並行処理
- [ ] データベース連携による履歴管理

### 長期改善
- [ ] 完全な自動化（人的確認不要）
- [ ] リアルタイム監視ダッシュボード
- [ ] 機械学習による異常値検出

## 📞 サポート

技術的な問題が発生した場合は、以下の情報とともにエラーログを記録してください：

1. 実行していたスクリプト名
2. エラーが発生した具体的な操作
3. エラーメッセージの全文
4. 実行環境（Python バージョン、OS等）

---

**最終更新**: 2024年12月  
**担当**: Claude Code によるリファクタリング実装