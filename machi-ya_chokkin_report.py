import streamlit as st
import pandas as pd
from typing import List, Tuple, Optional

from utils import (
    get_gsheet_service, get_campfire_amount, read_sheet_range, 
    write_sheet_cell, AuthenticationError, ScrapingError, SheetsError
)
from config import (
    get_spreadsheet_config, get_scopes, UI_CONFIG, ERROR_MESSAGES
)

# --- 設定の取得 ---
SPREADSHEET_CONFIG = get_spreadsheet_config("chokkin")
SCOPES = get_scopes("sheets_only")

# --- Streamlit UI ---
st.title("CAMPFIRE 金額更新ツール（2ステップ構成）")
st.markdown("1. 対象範囲の金額を取得 → 2. 内容確認後に書き込み")

start_row = st.number_input(
    "開始行（2以上）", 
    min_value=UI_CONFIG["min_row"], 
    value=UI_CONFIG["min_row"]
)
end_row = st.number_input(
    "終了行", 
    min_value=start_row, 
    value=start_row + UI_CONFIG["default_batch_size"]
)

# セッション状態に保存
if "results" not in st.session_state:
    st.session_state["results"] = []

def process_project_data(service, row: int) -> Tuple[int, str, str]:
    """
    プロジェクトデータを処理して金額を取得
    
    Args:
        service: Google Sheets APIサービス
        row: 処理する行番号
    
    Returns:
        (行番号, プロジェクトID, 金額) のタプル
    """
    try:
        cell_range = f"A{row}:A{row}"
        result = read_sheet_range(service, SPREADSHEET_CONFIG["id"], cell_range)
        
        if not result:
            return (row, ERROR_MESSAGES["no_id"], ERROR_MESSAGES["skip"])
        
        pj_id = result[0][0]
        amount = get_campfire_amount(pj_id)
        
        return (row, pj_id, amount)
    
    except (ScrapingError, SheetsError) as e:
        return (row, ERROR_MESSAGES["no_id"], f"エラー: {str(e)}")
    except Exception as e:
        return (row, ERROR_MESSAGES["no_id"], f"予期しないエラー: {str(e)}")

# --- Step 1: 金額取得 ---
if st.button("▶️ 金額を取得（書き込みはまだ）"):
    try:
        service = get_gsheet_service(SCOPES)
        results = []

        progress = st.progress(0)
        total = end_row - start_row + 1

        for i, row in enumerate(range(start_row, end_row + 1), 1):
            result = process_project_data(service, row)
            results.append(result)
            progress.progress(i / total)

        st.session_state["results"] = results
        st.success("取得完了 ✅")
        st.table(pd.DataFrame(results, columns=["行", "プロジェクトID", "金額"]))
    
    except AuthenticationError as e:
        st.error(f"認証エラー: {str(e)}")
    except Exception as e:
        st.error(f"予期しないエラーが発生しました: {str(e)}")

# --- Step 2: 書き込み ---
if st.session_state["results"]:
    if st.button("📝 スプレッドシートに書き込み"):
        try:
            service = get_gsheet_service(SCOPES)
            write_log = []

            for row, pj_id, amount in st.session_state["results"]:
                if (
                    ERROR_MESSAGES["fetch_failed"] in amount or 
                    "エラー" in amount or 
                    pj_id == ERROR_MESSAGES["no_id"]
                ):
                    write_log.append((row, pj_id, ERROR_MESSAGES["skip"]))
                    continue
                
                try:
                    write_sheet_cell(
                        service, 
                        SPREADSHEET_CONFIG["id"], 
                        f"D{row}", 
                        amount
                    )
                    write_log.append((row, pj_id, "書き込みOK"))
                except SheetsError as e:
                    write_log.append((row, pj_id, f"書き込みエラー: {str(e)}"))

            st.success("スプレッドシートへの書き込み完了 ✅")
            st.table(pd.DataFrame(write_log, columns=["行", "プロジェクトID", "ステータス"]))
        
        except AuthenticationError as e:
            st.error(f"認証エラー: {str(e)}")
        except Exception as e:
            st.error(f"予期しないエラーが発生しました: {str(e)}")