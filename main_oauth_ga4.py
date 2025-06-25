import datetime
import time
import pandas as pd
import streamlit as st
from typing import List, Tuple, Optional
import sys
import os

from utils import (
    get_gsheet_service, read_sheet_range, write_sheet_batch,
    process_ga4_project_data, AuthenticationError, GA4Error, SheetsError
)
from config import (
    get_spreadsheet_config, get_scopes, GA4_PROPERTY_ID,
    UI_CONFIG, BATCH_SIZE, ERROR_MESSAGES
)

# --- 設定の取得 ---
SPREADSHEET_CONFIG = get_spreadsheet_config("ga4")
SCOPES = get_scopes("sheets_and_analytics")


# --- Streamlit UI ---
st.title("GA4 セッション数更新ツール")
st.markdown("E列のプロジェクトIDをもとに、X列にセッション数を書き込みます")

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
target_date = st.date_input(
    "更新対象：終了日がこの日以降のプロジェクト", 
    value=datetime.date.today()
)

ga4_start_date = st.date_input(
    "GA4 開始日", 
    value=datetime.date.today() - datetime.timedelta(days=7)
)
ga4_end_date = st.date_input(
    "GA4 終了日", 
    value=datetime.date.today()
)

if "results" not in st.session_state:
    st.session_state["results"] = []

# --- データ取得処理 ---
if st.button("▶️ GA4 データを取得（書き込みはまだ）"):
    try:
        service = get_gsheet_service(SCOPES)
        results = []

        progress = st.progress(0)
        total = end_row - start_row + 1

        range_str = f"{SPREADSHEET_CONFIG['sheet_name']}!E{start_row}:J{end_row}"
        rows = read_sheet_range(service, SPREADSHEET_CONFIG["id"], range_str)

        for i, row_data in enumerate(rows, start=start_row):
            result = process_ga4_project_data(
                service, row_data, i, GA4_PROPERTY_ID,
                target_date, ga4_start_date, ga4_end_date, SCOPES
            )
            results.append(result)
            progress.progress((i - start_row + 1) / total)

        st.session_state["results"] = results
        st.success("取得完了 ✅")
        
        # 全結果の表示
        df_all = pd.DataFrame(results, columns=["行", "プロジェクトID", "セッション数", "ステータス"])
        
        # 取得OKのプロジェクトのみ抽出
        df_ok = df_all[df_all["ステータス"] == "取得OK"]
        df_other = df_all[df_all["ステータス"] != "取得OK"]
        
        if len(df_ok) > 0:
            st.subheader(f"📝 書き込み対象プロジェクト ({len(df_ok)}件)")
            st.dataframe(df_ok)
        
        if len(df_other) > 0:
            st.subheader(f"ℹ️ 対象外プロジェクト ({len(df_other)}件)")
            st.dataframe(df_other)
    
    except AuthenticationError as e:
        st.error(f"認証エラー: {str(e)}")
    except (GA4Error, SheetsError) as e:
        st.error(f"データ取得エラー: {str(e)}")
    except Exception as e:
        st.error(f"予期しないエラーが発生しました: {str(e)}")

# --- データ書き込み処理（飛び飛び行バッチ更新＋進捗表示付き） ---
if st.session_state["results"]:
    if st.button("📝 スプレッドシートに書き込み（GA4）"):
        try:
            service = get_gsheet_service(SCOPES)
            results = st.session_state["results"]
            total = len(results)

            progress = st.progress(0)
            log_placeholder = st.empty()

            write_log = []
            batch_data = []

            for idx, (row, pj_id, sessions, status) in enumerate(results):
                # 取得OKでない場合はすべてスキップ
                if status != "取得OK":
                    write_log.append((row, pj_id, f"スキップ({status})"))
                    continue

                batch_data.append({
                    "range": f"{SPREADSHEET_CONFIG['sheet_name']}!X{row}",
                    "values": [[sessions]]
                })

                write_log.append((row, pj_id, "バッチ準備OK"))

                if len(batch_data) >= BATCH_SIZE:
                    write_sheet_batch(service, SPREADSHEET_CONFIG["id"], batch_data)
                    batch_data = []

                progress.progress((idx + 1) / total)
                log_placeholder.text(f"{idx + 1}/{total} 行目 処理中...")

            # 残りのデータを書き込み
            if batch_data:
                write_sheet_batch(service, SPREADSHEET_CONFIG["id"], batch_data)

            st.success("スプレッドシートへの飛び飛びバッチ書き込み完了 ✅")
            st.dataframe(pd.DataFrame(write_log, columns=["行", "プロジェクトID", "ステータス"]))
        
        except AuthenticationError as e:
            st.error(f"認証エラー: {str(e)}")
        except SheetsError as e:
            st.error(f"書き込みエラー: {str(e)}")
        except Exception as e:
            st.error(f"予期しないエラーが発生しました: {str(e)}")

# --- アプリ終了ボタン ---
if st.button("🛑 アプリを終了する"):
    st.warning("アプリを終了します...")
    time.sleep(1)  # ユーザーに終了通知を見せるため1秒待機
    os._exit(0)
