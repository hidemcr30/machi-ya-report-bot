"""
共通ユーティリティモジュール
各スクリプトで使用される共通機能を提供
"""
import os
import re
import requests
from typing import Optional, Tuple, List, Dict, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from bs4 import BeautifulSoup
from google.analytics.data_v1beta import BetaAnalyticsDataClient
import datetime


class AuthenticationError(Exception):
    """認証関連のエラー"""
    pass


class ScrapingError(Exception):
    """スクレイピング関連のエラー"""
    pass


class SheetsError(Exception):
    """Google Sheets関連のエラー"""
    pass


class GA4Error(Exception):
    """GA4関連のエラー"""
    pass


def get_gsheet_service(scopes: List[str], credentials_file: str = "credentials.json", token_file: str = "token.json"):
    """
    Google Sheets APIサービスオブジェクトを取得
    
    Args:
        scopes: 必要なスコープのリスト
        credentials_file: 認証情報ファイルのパス
        token_file: トークンファイルのパス
    
    Returns:
        Google Sheets APIサービスオブジェクト
    
    Raises:
        AuthenticationError: 認証に失敗した場合
    """
    try:
        creds = None
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, scopes)
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                elif not creds.has_scopes(scopes):
                    creds = None
        
        if not creds or not creds.valid or not creds.has_scopes(scopes):
            if not os.path.exists(credentials_file):
                raise AuthenticationError(f"認証ファイルが見つかりません: {credentials_file}")
            
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
            creds = flow.run_local_server(port=0)
            
            with open(token_file, "w") as token:
                token.write(creds.to_json())
        
        return build("sheets", "v4", credentials=creds)
    
    except Exception as e:
        raise AuthenticationError(f"認証処理でエラーが発生しました: {str(e)}")


def get_campfire_data(pj_id: str, timeout: int = 10) -> Tuple[str, str]:
    """
    CAMPFIREプロジェクトから金額と人数を取得
    
    Args:
        pj_id: プロジェクトID
        timeout: リクエストタイムアウト（秒）
    
    Returns:
        (金額, 人数) のタプル
    
    Raises:
        ScrapingError: スクレイピングに失敗した場合
    """
    url = f"https://camp-fire.jp/projects/{pj_id}/view"
    
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        response.encoding = "utf-8"
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        amount_elem = soup.find("p", class_="backer-amount")
        count_elem = soup.find("p", class_="backer")
        
        amount = re.sub(r"[^\d]", "", amount_elem.text.strip()) if amount_elem else "取得不可"
        count = re.sub(r"[^\d]", "", count_elem.text.strip()) if count_elem else "取得不可"
        
        return amount, count
    
    except requests.exceptions.RequestException as e:
        raise ScrapingError(f"プロジェクト {pj_id} のデータ取得でネットワークエラー: {str(e)}")
    except Exception as e:
        raise ScrapingError(f"プロジェクト {pj_id} のデータ取得でエラー: {str(e)}")


def get_campfire_amount(pj_id: str, timeout: int = 10) -> str:
    """
    CAMPFIREプロジェクトから金額のみを取得
    
    Args:
        pj_id: プロジェクトID
        timeout: リクエストタイムアウト（秒）
    
    Returns:
        金額文字列
    
    Raises:
        ScrapingError: スクレイピングに失敗した場合
    """
    try:
        amount, _ = get_campfire_data(pj_id, timeout)
        return amount
    except ScrapingError:
        raise
    except Exception as e:
        raise ScrapingError(f"プロジェクト {pj_id} の金額取得でエラー: {str(e)}")


def read_sheet_range(service, spreadsheet_id: str, range_str: str) -> List[List[str]]:
    """
    Google Sheetsから指定範囲のデータを読み取り
    
    Args:
        service: Google Sheets APIサービスオブジェクト
        spreadsheet_id: スプレッドシートID
        range_str: 読み取り範囲
    
    Returns:
        データのリスト
    
    Raises:
        SheetsError: Google Sheets操作に失敗した場合
    """
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, 
            range=range_str
        ).execute()
        return result.get("values", [])
    
    except Exception as e:
        raise SheetsError(f"シート読み取りでエラー: {str(e)}")


def write_sheet_cell(service, spreadsheet_id: str, cell_range: str, value: str) -> None:
    """
    Google Sheetsの単一セルに値を書き込み
    
    Args:
        service: Google Sheets APIサービスオブジェクト
        spreadsheet_id: スプレッドシートID
        cell_range: セル範囲
        value: 書き込み値
    
    Raises:
        SheetsError: Google Sheets操作に失敗した場合
    """
    try:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=cell_range,
            valueInputOption="USER_ENTERED",
            body={"values": [[value]]}
        ).execute()
    
    except Exception as e:
        raise SheetsError(f"セル書き込みでエラー: {str(e)}")


def write_sheet_batch(service, spreadsheet_id: str, batch_data: List[Dict[str, Any]]) -> None:
    """
    Google Sheetsにバッチで値を書き込み
    
    Args:
        service: Google Sheets APIサービスオブジェクト
        spreadsheet_id: スプレッドシートID
        batch_data: バッチデータのリスト
    
    Raises:
        SheetsError: Google Sheets操作に失敗した場合
    """
    try:
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": batch_data
        }
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
    
    except Exception as e:
        raise SheetsError(f"バッチ書き込みでエラー: {str(e)}")


def is_valid_date_string(date_str: str, date_format: str = "%Y/%m/%d") -> bool:
    """
    日付文字列の妥当性を検証
    
    Args:
        date_str: 日付文字列
        date_format: 日付フォーマット
    
    Returns:
        妥当性の真偽値
    """
    try:
        import datetime
        datetime.datetime.strptime(date_str, date_format)
        return True
    except ValueError:
        return False


def clean_numeric_string(text: str) -> str:
    """
    文字列から数値のみを抽出
    
    Args:
        text: 入力文字列
    
    Returns:
        数値のみの文字列
    """
    return re.sub(r"[^\d]", "", text.strip()) if text else ""


def get_ga4_sessions(
    pj_id: str, 
    property_id: str, 
    start_date: datetime.date, 
    end_date: datetime.date,
    scopes: List[str],
    credentials_file: str = "credentials.json", 
    token_file: str = "token.json"
) -> str:
    """
    GA4からセッション数を取得
    
    Args:
        pj_id: プロジェクトID
        property_id: GA4プロパティID
        start_date: 開始日
        end_date: 終了日
        scopes: OAuth スコープ
        credentials_file: 認証情報ファイルのパス
        token_file: トークンファイルのパス
    
    Returns:
        セッション数の文字列
    
    Raises:
        GA4Error: GA4データ取得に失敗した場合
        AuthenticationError: 認証に失敗した場合
    """
    try:
        # 認証処理
        creds = None
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, scopes)
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                elif not creds.has_scopes(scopes):
                    creds = None
        
        if not creds or not creds.valid or not creds.has_scopes(scopes):
            if not os.path.exists(credentials_file):
                raise AuthenticationError(f"認証ファイルが見つかりません: {credentials_file}")
            
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
            creds = flow.run_local_server(port=0)
            
            with open(token_file, "w") as token:
                token.write(creds.to_json())
        
        # GA4クライアント作成
        client = BetaAnalyticsDataClient(credentials=creds)
        
        # リクエスト作成
        request = {
            "property": f"properties/{property_id}",
            "date_ranges": [{"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}],
            "dimensions": [{"name": "pagePath"}],
            "metrics": [{"name": "sessions"}],
            "dimension_filter": {
                "filter": {
                    "field_name": "pagePath",
                    "string_filter": {"value": pj_id, "match_type": "CONTAINS"}
                }
            }
        }
        
        # データ取得
        response = client.run_report(request)
        
        if response.rows:
            return response.rows[0].metric_values[0].value
        else:
            return "0"
    
    except Exception as e:
        raise GA4Error(f"GA4データ取得でエラー: {str(e)}")


def process_ga4_project_data(
    service, 
    row_data: List[str], 
    row_index: int, 
    property_id: str,
    target_date: datetime.date,
    ga4_start_date: datetime.date,
    ga4_end_date: datetime.date,
    scopes: List[str]
) -> Tuple[int, str, str, str]:
    """
    GA4プロジェクトデータを処理
    
    Args:
        service: Google Sheets APIサービス
        row_data: 行データ
        row_index: 行インデックス
        property_id: GA4プロパティID
        target_date: 対象日
        ga4_start_date: GA4開始日
        ga4_end_date: GA4終了日
        scopes: OAuth スコープ
    
    Returns:
        (行番号, プロジェクトID, セッション数, ステータス) のタプル
    """
    try:
        pj_id = row_data[0] if row_data else ""
        if not pj_id:
            return (row_index, "IDなし", "-", "スキップ")
        
        end_date_str = row_data[5] if len(row_data) > 5 else ""
        if not end_date_str:
            return (row_index, pj_id, "-", "終了日なし")
        
        if not is_valid_date_string(end_date_str):
            return (row_index, pj_id, "-", "日付解析エラー")
        
        project_end_date = datetime.datetime.strptime(end_date_str, "%Y/%m/%d").date()
        if project_end_date < target_date:
            return (row_index, pj_id, "-", "対象外")
        
        sessions = get_ga4_sessions(
            pj_id, property_id, ga4_start_date, ga4_end_date, scopes
        )
        
        return (row_index, pj_id, sessions, "取得OK")
    
    except (GA4Error, AuthenticationError) as e:
        return (row_index, pj_id if 'pj_id' in locals() else "不明", "-", f"エラー: {str(e)}")
    except Exception as e:
        return (row_index, pj_id if 'pj_id' in locals() else "不明", "-", f"予期しないエラー: {str(e)}")