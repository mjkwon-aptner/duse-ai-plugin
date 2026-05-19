"""Google Sheets 셀 단위 read/write/format/append helpers.

gspread 6.x 기반. 모든 함수는 시트 URL 또는 ID 어느 쪽이든 받습니다.

CLI 사용:
    python sheets.py read   <url> <sheet> <A1:D10>
    python sheets.py write  <url> <sheet> <A1>      '<JSON 2D array>'
    python sheets.py append <url> <sheet>           '<JSON 2D array>'
    python sheets.py format <url> <sheet> <A1:B1>   '<JSON format dict>'
    python sheets.py add_sheet <url> <new_tab_title>
    python sheets.py create <title>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# 같은 폴더의 auth.py를 import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from auth import ensure_authed  # noqa: E402

_CLIENT = None


def get_client():
    """싱글톤 gspread Client. 첫 호출 시 ensure_authed() 실행."""
    global _CLIENT
    if _CLIENT is None:
        creds = ensure_authed()
        import gspread
        _CLIENT = gspread.authorize(creds)
    return _CLIENT


def extract_spreadsheet_id(url_or_id: str) -> str:
    """시트 URL 또는 ID 문자열에서 ID만 추출.

    >>> extract_spreadsheet_id("https://docs.google.com/spreadsheets/d/ABC123/edit#gid=0")
    'ABC123'
    >>> extract_spreadsheet_id("ABC123")
    'ABC123'
    """
    if not url_or_id:
        raise ValueError("빈 시트 URL/ID")
    if "/" not in url_or_id:
        return url_or_id.strip()
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url_or_id)
    if m:
        return m.group(1)
    raise ValueError(f"시트 ID 추출 실패: {url_or_id}")


def _open(url_or_id: str):
    sid = extract_spreadsheet_id(url_or_id)
    return get_client().open_by_key(sid)


def _ws(url_or_id: str, sheet_name: str = None):
    """워크시트 조회. sheet_name이 None/빈/매칭 실패 시 첫 워크시트 fallback.

    locale 차이로 default 탭 이름이 'Sheet1'/'시트1' 등 다를 수 있어 fallback 안전.
    """
    sh = _open(url_or_id)
    if not sheet_name:
        return sh.sheet1
    try:
        return sh.worksheet(sheet_name)
    except Exception:
        worksheets = sh.worksheets()
        if not worksheets:
            raise
        fallback = worksheets[0]
        print(f"⚠️ '{sheet_name}' 탭 없음 → 첫 탭 '{fallback.title}' 사용", file=sys.stderr)
        return fallback


# ─────────────────────────────────────────────────────────────
#  Read
# ─────────────────────────────────────────────────────────────

def read_range(url_or_id: str, sheet_name: str, range_a1: str) -> list:
    """A1 표기 범위의 셀 값을 2D list로 반환.

    Example:
        read_range(url, 'Sheet1', 'A1:D10')
    """
    ws = _ws(url_or_id, sheet_name)
    return ws.get(range_a1)


def read_cell(url_or_id: str, sheet_name: str, a1: str) -> str:
    """단일 셀 값 반환."""
    ws = _ws(url_or_id, sheet_name)
    return ws.acell(a1).value


def list_sheet_tabs(url_or_id: str) -> list:
    """스프레드시트의 모든 탭(워크시트) 이름 리스트."""
    sh = _open(url_or_id)
    return [ws.title for ws in sh.worksheets()]


# ─────────────────────────────────────────────────────────────
#  Write
# ─────────────────────────────────────────────────────────────

def write_range(url_or_id: str, sheet_name: str, range_a1: str, values: list) -> dict:
    """범위에 값 일괄 쓰기 (gspread 6.x: values=, range_name= 키워드).

    Example:
        write_range(url, 'Sheet1', 'A1', [['이름','부서'],['김철수','AX']])
    """
    if not isinstance(values, list) or (values and not isinstance(values[0], list)):
        raise ValueError("values는 2D list여야 합니다. 예: [['a','b'],['c','d']]")
    ws = _ws(url_or_id, sheet_name)
    return ws.update(values=values, range_name=range_a1, value_input_option="USER_ENTERED")


def write_cell(url_or_id: str, sheet_name: str, a1: str, value) -> dict:
    """단일 셀 쓰기."""
    ws = _ws(url_or_id, sheet_name)
    return ws.update_acell(a1, value)


def append_rows(url_or_id: str, sheet_name: str, rows: list) -> dict:
    """마지막 row 뒤에 새 row(들) 추가.

    Example:
        append_rows(url, 'Sheet1', [['새 행 A','새 행 B']])
    """
    if not isinstance(rows, list) or (rows and not isinstance(rows[0], list)):
        raise ValueError("rows는 2D list여야 합니다. 예: [['a','b'],['c','d']]")
    ws = _ws(url_or_id, sheet_name)
    return ws.append_rows(rows, value_input_option="USER_ENTERED")


def clear_range(url_or_id: str, sheet_name: str, range_a1: str = None) -> dict:
    """범위 또는 시트 전체 셀 값 삭제 (포맷팅은 유지)."""
    ws = _ws(url_or_id, sheet_name)
    if range_a1:
        return ws.batch_clear([range_a1])
    return ws.clear()


# ─────────────────────────────────────────────────────────────
#  Format
# ─────────────────────────────────────────────────────────────

def format_range(url_or_id: str, sheet_name: str, range_a1: str, fmt: dict) -> dict:
    """셀 포맷팅.

    fmt 예시:
        {'textFormat': {'bold': True, 'fontSize': 12}}
        {'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}}
        {'horizontalAlignment': 'CENTER'}
        {'numberFormat': {'type': 'CURRENCY', 'pattern': '$#,##0.00'}}
    """
    ws = _ws(url_or_id, sheet_name)
    return ws.format(range_a1, fmt)


def freeze_rows(url_or_id: str, sheet_name: str, rows: int = 1, cols: int = 0) -> dict:
    """첫 N개 행/열 고정."""
    ws = _ws(url_or_id, sheet_name)
    return ws.freeze(rows=rows, cols=cols)


def merge_cells(url_or_id: str, sheet_name: str, range_a1: str, merge_type: str = "MERGE_ALL") -> dict:
    """셀 병합 (MERGE_ALL / MERGE_COLUMNS / MERGE_ROWS)."""
    ws = _ws(url_or_id, sheet_name)
    return ws.merge_cells(range_a1, merge_type=merge_type)


# ─────────────────────────────────────────────────────────────
#  Spreadsheet / Worksheet 관리
# ─────────────────────────────────────────────────────────────

def add_sheet(url_or_id: str, sheet_title: str, rows: int = 1000, cols: int = 26):
    """새 탭(워크시트) 추가."""
    sh = _open(url_or_id)
    return sh.add_worksheet(title=sheet_title, rows=rows, cols=cols)


def delete_sheet(url_or_id: str, sheet_name: str) -> None:
    """탭(워크시트) 삭제. 신중하게 사용."""
    sh = _open(url_or_id)
    ws = sh.worksheet(sheet_name)
    sh.del_worksheet(ws)


def create_spreadsheet(title: str, parent_folder_id: str = None) -> str:
    """새 스프레드시트 생성. URL 반환.

    parent_folder_id 주면 해당 Drive 폴더 안에 생성.
    """
    gc = get_client()
    sh = gc.create(title, folder_id=parent_folder_id) if parent_folder_id else gc.create(title)
    return f"https://docs.google.com/spreadsheets/d/{sh.id}/edit"


def share_spreadsheet(url_or_id: str, email: str, role: str = "writer", notify: bool = False) -> None:
    """시트를 다른 사람과 공유. role: 'reader' | 'commenter' | 'writer' | 'owner'."""
    sh = _open(url_or_id)
    sh.share(email, perm_type="user", role=role, notify=notify)


# ─────────────────────────────────────────────────────────────
#  CLI 진입점 (테스트/디버깅용)
# ─────────────────────────────────────────────────────────────

def _print_result(result):
    if result is None:
        print("✅ done")
    elif isinstance(result, (list, dict)):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result)


_USAGE = """\
usage:
  sheets.py read       <url> <sheet> <range_a1>
  sheets.py read_cell  <url> <sheet> <a1>
  sheets.py write      <url> <sheet> <range_a1>     '<JSON 2D array>'
  sheets.py append     <url> <sheet>                '<JSON 2D array>'
  sheets.py format     <url> <sheet> <range_a1>     '<JSON dict>'
  sheets.py add_sheet  <url> <new_tab_title>        [rows] [cols]
  sheets.py list_tabs  <url>
  sheets.py create     <title>                      [parent_folder_id]
  sheets.py share      <url> <email>                [role]
"""


def _cli(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(_USAGE)
        return 0
    cmd = argv[0]
    try:
        if cmd == "read":
            url, sheet, rng = argv[1], argv[2], argv[3]
            _print_result(read_range(url, sheet, rng))
        elif cmd == "read_cell":
            url, sheet, a1 = argv[1], argv[2], argv[3]
            _print_result(read_cell(url, sheet, a1))
        elif cmd == "write":
            url, sheet, rng, values_json = argv[1], argv[2], argv[3], argv[4]
            _print_result(write_range(url, sheet, rng, json.loads(values_json)))
        elif cmd == "append":
            url, sheet, rows_json = argv[1], argv[2], argv[3]
            _print_result(append_rows(url, sheet, json.loads(rows_json)))
        elif cmd == "format":
            url, sheet, rng, fmt_json = argv[1], argv[2], argv[3], argv[4]
            _print_result(format_range(url, sheet, rng, json.loads(fmt_json)))
        elif cmd == "add_sheet":
            url, title = argv[1], argv[2]
            rows = int(argv[3]) if len(argv) > 3 else 1000
            cols = int(argv[4]) if len(argv) > 4 else 26
            ws = add_sheet(url, title, rows=rows, cols=cols)
            print(f"✅ 새 탭 추가: '{ws.title}' (rows={ws.row_count}, cols={ws.col_count})")
        elif cmd == "list_tabs":
            _print_result(list_sheet_tabs(argv[1]))
        elif cmd == "create":
            title = argv[1]
            parent = argv[2] if len(argv) > 2 else None
            print(create_spreadsheet(title, parent_folder_id=parent))
        elif cmd == "share":
            url, email = argv[1], argv[2]
            role = argv[3] if len(argv) > 3 else "writer"
            share_spreadsheet(url, email, role=role)
            print(f"✅ 공유: {email} ({role})")
        else:
            print(f"❌ unknown command: {cmd}")
            print(_USAGE)
            return 1
    except IndexError:
        print(f"❌ 인자 부족: {cmd}")
        print(_USAGE)
        return 1
    except Exception as e:
        print(f"❌ Error: {e.__class__.__name__}: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
