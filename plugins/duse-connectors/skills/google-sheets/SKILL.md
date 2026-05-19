---
name: google-sheets
description: Google Sheets 셀 단위 read/write/format/append/탭 추가. "구글 시트", "스프레드시트에 써줘/읽어줘/편집", "Google Sheets edit/read/write", "시트 셀에 값", "새 탭 추가" 같은 요청에 사용. 첫 사용 시 OAuth 브라우저 동의 1회 필요.
---

# google-sheets skill

Google Sheets API v4를 통해 시트를 셀 단위로 직접 조작합니다. 두꺼비세상 멀티 Workspace(@aptner.com / @duse.kr) 자동 분기 지원.

## 무엇을 하는가
- 셀 / 범위 read (`read_range`, `read_cell`)
- 셀 / 범위 write (`write_range`, `write_cell`) — batch 일괄 쓰기
- 마지막 행에 추가 (`append_rows`)
- 셀 포맷팅 (`format_range`) — 굵게, 색상, 정렬, 통화 포맷
- 행/열 고정 (`freeze_rows`), 셀 병합 (`merge_cells`)
- 새 탭 추가 (`add_sheet`) / 삭제 (`delete_sheet`)
- 새 스프레드시트 생성 (`create_spreadsheet`)
- 다른 사람에게 공유 (`share_spreadsheet`)
- 탭 목록 조회 (`list_sheet_tabs`)

## 사용 전 1회 셋업 (직원 본인이 1회만)

### 1. Python 의존성 설치
```bash
pip install -r <skill_dir>/scripts/requirements.txt
```

### 2. 첫 OAuth 동의
OAuth Client(`credentials_aptner.json`, `credentials_duse.json`)는 plugin에 이미 포함되어 있습니다. **별도로 받을 필요 없음**.

```bash
python <skill_dir>/scripts/auth.py
```
브라우저 자동 실행 → 본인 회사 계정 로그인 → [허용] → 끝. 이후 토큰은 `~/.config/gspread/authorized_user_<domain>.json`에 저장되어 영구 자동 인증.

### (선택) 개인 OAuth Client 사용
본인이 발급한 OAuth Client를 쓰고 싶으면 `~/.config/duse-connectors/credentials_<domain>.json`에 저장 → plugin 기본 credentials보다 우선 적용.

자동 탐색 우선순위:
1. `~/.config/duse-connectors/credentials_<domain>.json` (사용자 개인)
2. `<skill_dir>/credentials_<domain>.json` (plugin 기본, 사내 공용)

## Claude 호출 패턴

이 SKILL.md와 같은 디렉토리(`<skill_dir>`) 안의 `scripts/` 폴더를 Python path에 추가해서 import:

```python
import sys
from pathlib import Path

# 이 SKILL.md가 위치한 skill 디렉토리의 scripts/
SCRIPTS_DIR = Path("<skill_dir>/scripts").expanduser()
sys.path.insert(0, str(SCRIPTS_DIR))

from sheets import (
    ensure_authed, read_range, write_range, append_rows,
    format_range, add_sheet, create_spreadsheet, list_sheet_tabs,
    freeze_rows, merge_cells, share_spreadsheet,
)

ensure_authed()
url = "https://docs.google.com/spreadsheets/d/XXXXXXX/edit"

# 쓰기 (sheet_name=None이면 첫 탭 자동)
write_range(url, None, 'A1', [['이름','부서'],['김철수','AX']])

# 읽기
data = read_range(url, '시트1', 'A1:B10')

# 포맷팅
format_range(url, '시트1', 'A1:B1', {
    'textFormat': {'bold': True},
    'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
    'horizontalAlignment': 'CENTER',
})
freeze_rows(url, '시트1', rows=1)

# 새 탭 추가
add_sheet(url, '시나리오')

# 새 시트 만들기
new_url = create_spreadsheet('새 분석 결과')
```

**중요**: `<skill_dir>`은 Claude Code가 SKILL.md를 로딩한 plugin 경로. 본인 환경에서 실제 경로 확인은:
```bash
# plugin install 후 일반 경로
ls ~/.claude/plugins/duse-connectors/skills/google-sheets/scripts/
```

## CLI 호출 (디버깅·테스트용)

```bash
SCRIPTS=<skill_dir>/scripts
SHEET="https://docs.google.com/spreadsheets/d/XXX/edit"

python $SCRIPTS/sheets.py read      "$SHEET" 시트1 A1:D10
python $SCRIPTS/sheets.py write     "$SHEET" 시트1 A1    '[["a","b"],["c","d"]]'
python $SCRIPTS/sheets.py append    "$SHEET" 시트1       '[["new row"]]'
python $SCRIPTS/sheets.py format    "$SHEET" 시트1 A1:B1 '{"textFormat":{"bold":true}}'
python $SCRIPTS/sheets.py add_sheet "$SHEET" "새탭"
python $SCRIPTS/sheets.py create    "새 시트 제목"
python $SCRIPTS/sheets.py list_tabs "$SHEET"
```

## 작업 규칙 (Claude가 지킬 것)

1. **batch 우선**: 큰 데이터는 `write_range`로 범위 단위 한 번에. 개별 셀 update 반복 금지.
2. **시트 URL/ID 자유 입력**: `extract_spreadsheet_id`가 자동 처리 (URL이든 ID든 OK).
3. **인증 보장**: 함수들이 내부적으로 인증을 처리하지만, 첫 작업 전 한 번 `ensure_authed()` 직접 호출해 검증 권장.
4. **에러 메시지 그대로 보여주기**: credentials 없음 / 권한 없음 등은 사용자가 직접 액션해야 하므로 메시지 가공 없이 전달.
5. **시트 default 탭 이름은 locale에 따라 다름**: 한국어 워크스페이스 = "시트1", 영어 = "Sheet1". `sheet_name=None`이면 자동으로 첫 탭 사용.

## 트리거 키워드
- "구글 시트에 정리해줘 / 써줘"
- "스프레드시트에 / 시트에 셀 값 넣어줘"
- "Google Sheets 편집 / 읽기 / 쓰기"
- "시트 새 탭 추가"
- "이 시트 분석해줘 https://docs.google.com/..." (URL 동반)

## 에러 핸들링

| 에러 | 원인 | 액션 |
|------|------|------|
| `FileNotFoundError: credentials_*.json` | OAuth Client JSON 없음 | `python auth.py --setup-guide` 실행, AX팀에 공용 JSON 요청 |
| 브라우저 자동 안 열림 | SSH/원격 환경 | 콘솔에 출력된 URL을 수동 복사 → 본인 PC 브라우저에 붙여넣기 |
| `403 Permission denied` | 시트 편집 권한 없음 | 본인 회사 계정으로 시트에 편집자 권한 받기 |
| `429 Too Many Requests` | rate limit (60 req/min) | 잠시 대기 후 재시도. 가급적 batch로 합쳐 호출 |
| 토큰 만료 / refresh 실패 | 장기 미사용 | `python auth.py --reset` 후 재인증 |
| `WorksheetNotFound` | 탭 이름 mismatch | `list_sheet_tabs()`로 실제 탭 이름 확인 또는 `sheet_name=None` 사용 |

## Rate Limit
사용자당 60 req/min. 대량 작업은 `write_range`로 batch 처리.
