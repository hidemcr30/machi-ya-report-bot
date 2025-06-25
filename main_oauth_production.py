import datetime
import time
import pandas as pd
import streamlit as st
from typing import List, Tuple, Optional
import sys
import os

from utils import (
    get_gsheet_service, get_campfire_data, get_campfire_data_batch, get_campfire_data_batch_with_progress,
    read_sheet_range, write_sheet_batch, is_valid_date_string, should_fetch_project_data, 
    AuthenticationError, ScrapingError, SheetsError
)
from config import (
    get_spreadsheet_config, get_scopes, UI_CONFIG, BATCH_SIZE, ERROR_MESSAGES
)

# --- 設定の取得 ---
SPREADSHEET_CONFIG = get_spreadsheet_config("production")
SCOPES = get_scopes("sheets_only")

def process_production_project_data_fast(
    rows: List[List[str]], 
    start_row: int, 
    target_date: datetime.date,
    max_workers: int = 2,
    progress_callback=None
) -> List[Tuple[int, str, str, str, str]]:
    """
    プロダクション用プロジェクトデータを高速処理（並行実行版）
    
    Args:
        rows: 全行データ
        start_row: 開始行番号
        target_date: 対象日
        max_workers: 最大並行実行数
        progress_callback: プログレス更新コールバック関数
    
    Returns:
        (行番号, プロジェクトID, 金額, 人数, ステータス) のタプルのリスト
    """
    results = []
    fetch_targets = []  # 実際にHTTPリクエストが必要なプロジェクト
    total_rows = len(rows)
    
    # Phase 1: 事前フィルタリング（高速）
    for i, row_data in enumerate(rows, start=start_row):
        pj_id = row_data[0] if len(row_data) > 0 else ""
        
        # 事前チェックでHTTPリクエスト不要なケースを除外
        if not should_fetch_project_data(row_data, target_date):
            # 詳細な理由を判定
            if not pj_id:
                results.append((i, ERROR_MESSAGES["no_id"], "-", "-", ERROR_MESSAGES["skip"]))
            elif not (row_data[5] if len(row_data) > 5 else ""):
                results.append((i, pj_id, "-", "-", "終了日なし"))
            elif not is_valid_date_string(row_data[5] if len(row_data) > 5 else ""):
                results.append((i, pj_id, "-", "-", ERROR_MESSAGES["date_parse_error"]))
            else:
                results.append((i, pj_id, "-", "-", "対象外"))
        else:
            # HTTPリクエストが必要なプロジェクト
            fetch_targets.append((i, pj_id))
    
    # プログレス更新（フィルタリング完了）
    if progress_callback:
        progress_callback(0.2, f"事前フィルタリング完了: {len(fetch_targets)}件の並行取得を開始")
    
    # Phase 2: 並行データ取得（最適化済み）
    if fetch_targets:
        project_ids = [pj_id for _, pj_id in fetch_targets]
        
        # バッチ処理で並行取得（プログレス付き）
        fetch_results = get_campfire_data_batch_with_progress(
            project_ids, 
            max_workers=max_workers,
            progress_callback=lambda p, msg: progress_callback(0.2 + p * 0.7, msg) if progress_callback else None
        )
        
        # 結果をマージ
        for (row_index, pj_id), (_, (amount, count)) in zip(fetch_targets, fetch_results):
            if "エラー" in amount or amount == "取得不可":
                results.append((row_index, pj_id, "-", "-", f"取得エラー"))
            else:
                results.append((row_index, pj_id, amount, count, "取得OK"))
    
    # プログレス更新（並行取得完了）
    if progress_callback:
        progress_callback(0.9, "データ処理中...")
    
    # 行番号順でソート
    results.sort(key=lambda x: x[0])
    
    # プログレス更新（完了）
    if progress_callback:
        progress_callback(1.0, "処理完了")
    
    return results


def process_production_project_data(
    row_data: List[str], 
    row_index: int, 
    target_date: datetime.date
) -> Tuple[int, str, str, str, str]:
    """
    プロダクション用プロジェクトデータを処理（単体処理版・互換性維持）
    
    Args:
        row_data: 行データ
        row_index: 行インデックス
        target_date: 対象日
    
    Returns:
        (行番号, プロジェクトID, 金額, 人数, ステータス) のタプル
    """
    try:
        pj_id = row_data[0] if len(row_data) > 0 else ""
        end_date_str = row_data[5] if len(row_data) > 5 else ""

        if not pj_id:
            return (row_index, ERROR_MESSAGES["no_id"], "-", "-", ERROR_MESSAGES["skip"])

        if not end_date_str:
            return (row_index, pj_id, "-", "-", "終了日なし")

        if not is_valid_date_string(end_date_str):
            return (row_index, pj_id, "-", "-", ERROR_MESSAGES["date_parse_error"])

        project_end_date = datetime.datetime.strptime(end_date_str, "%Y/%m/%d").date()
        if project_end_date < target_date:
            return (row_index, pj_id, "-", "-", "対象外")

        amount, count = get_campfire_data(pj_id)
        return (row_index, pj_id, amount, count, "取得OK")
    
    except (ScrapingError,) as e:
        return (row_index, pj_id if 'pj_id' in locals() else "不明", "-", "-", f"エラー: {str(e)}")
    except Exception as e:
        return (row_index, pj_id if 'pj_id' in locals() else "不明", "-", "-", f"予期しないエラー: {str(e)}")

# --- Streamlit UI ---
st.title("machi-ya 本番スプシ：金額・人数更新ツール")
st.markdown("E列のプロジェクトIDをもとに、N列に金額、P列に人数を書き込みます")

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

if "results" not in st.session_state:
    st.session_state["results"] = []

# --- パフォーマンス設定 ---
performance_mode = st.selectbox(
    "処理モード",
    ["高速モード（並行処理）", "安全モード（順次処理）"],
    index=0,
    help="高速モードは並行処理でサーバー負荷を配慮しつつ高速化。安全モードは従来の順次処理。"
)

max_workers = st.slider(
    "並行実行数（高速モード時）",
    min_value=1,
    max_value=4,
    value=2,
    help="同時実行するリクエスト数。多すぎるとサーバー負荷が高くなります。"
)

# --- データ取得処理 ---
if st.button("▶️ 金額・人数を取得（書き込みはまだ）"):
    try:
        service = get_gsheet_service(SCOPES)
        
        range_str = f"{SPREADSHEET_CONFIG['sheet_name']}!E{start_row}:J{end_row}"
        rows = read_sheet_range(service, SPREADSHEET_CONFIG["id"], range_str)
        
        # 処理開始時刻記録
        start_time = time.time()
        
        if performance_mode == "高速モード（並行処理）":
            st.info(f"🚀 高速モードで処理中... （並行数: {max_workers}）")
            
            # 事前フィルタリング統計
            valid_count = sum(1 for row_data in rows if should_fetch_project_data(row_data, target_date))
            total_count = len(rows)
            
            st.write(f"📊 処理統計: 全{total_count}件中、{valid_count}件を並行取得、{total_count - valid_count}件を事前除外")
            
            # プログレスバーとステータス表示
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(progress: float, message: str):
                progress_bar.progress(progress)
                status_text.text(message)
            
            # 高速並行処理（プログレス付き）
            results = process_production_project_data_fast(
                rows, start_row, target_date, max_workers, update_progress
            )
            
        else:
            st.info("🐢 安全モードで処理中...")
            results = []
            progress = st.progress(0)
            total = end_row - start_row + 1

            for i, row_data in enumerate(rows, start=start_row):
                result = process_production_project_data(row_data, i, target_date)
                results.append(result)
                progress.progress((i - start_row + 1) / total)
        
        # 処理時間計測
        end_time = time.time()
        processing_time = end_time - start_time
        
        st.session_state["results"] = results
        st.success(f"取得完了 ✅ (処理時間: {processing_time:.2f}秒)")
        
        # 全結果の表示
        df_all = pd.DataFrame(results, columns=["行", "プロジェクトID", "金額", "人数", "ステータス"])
        
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
    except (ScrapingError, SheetsError) as e:
        st.error(f"データ取得エラー: {str(e)}")
    except Exception as e:
        st.error(f"予期しないエラーが発生しました: {str(e)}")

# --- データ書き込み処理（飛び飛び行バッチ更新＋進捗表示付き） ---
if st.session_state["results"]:
    if st.button("📝 スプレッドシートに書き込み（飛び飛びバッチ処理）"):
        try:
            service = get_gsheet_service(SCOPES)
            results = st.session_state["results"]
            total = len(results)

            progress = st.progress(0)
            log_placeholder = st.empty()

            write_log = []
            batch_data = []

            for idx, (row, pj_id, amount, count, status) in enumerate(results):
                # 取得OKでない場合はすべてスキップ
                if status != "取得OK":
                    write_log.append((row, pj_id, f"スキップ({status})"))
                    continue

                # 金額と人数の両方を追加
                batch_data.append({
                    "range": f"{SPREADSHEET_CONFIG['sheet_name']}!N{row}",
                    "values": [[amount]]
                })
                batch_data.append({
                    "range": f"{SPREADSHEET_CONFIG['sheet_name']}!P{row}",
                    "values": [[count]]
                })

                write_log.append((row, pj_id, "バッチ準備OK"))

                # バッチサイズに達したら送信（金額＋人数で2倍のサイズ）
                if len(batch_data) >= BATCH_SIZE * 2:
                    write_sheet_batch(service, SPREADSHEET_CONFIG["id"], batch_data)
                    batch_data = []

                # プログレスバーとログ更新
                progress.progress((idx + 1) / total)
                log_placeholder.text(f"{idx + 1}/{total} 行目 処理中...")

            # 残りのデータを送信
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
