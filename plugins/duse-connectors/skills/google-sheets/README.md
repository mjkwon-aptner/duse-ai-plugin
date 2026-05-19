# google-sheets skill (두꺼비세상 사내 배포)

Claude Code가 Google Sheets를 셀 단위로 직접 다룰 수 있게 해주는 skill.
TSV 복붙·CSV 다운로드 같은 우회 없이, "이 시트에 정리해줘" 한 마디로 끝납니다.

## 무엇이 가능한가

- 셀/범위 read / write (batch 일괄 처리)
- 마지막 행 뒤에 append
- 포맷팅 (굵게, 색상, 셀 병합, 행 고정, 통화 포맷 등)
- 새 탭(워크시트) 추가/삭제
- 새 스프레드시트 생성
- 다른 사람에게 공유 권한 부여

## 설치 (직원 1회만)

### 1. skill 폴더 복사

이 폴더 통째로 다음 위치에 복사:

```bash
~/.claude/skills/google-sheets/
```

(이미 AX팀이 사내 배포본을 만들어 두었을 가능성 — 슬랙에서 확인)

### 2. credentials.json 받기

**옵션 A — AX팀 공유본 사용 (권장)**
AX팀이 사내 공용 OAuth Client JSON을 슬랙/Drive로 공유해 둡니다. 받아서 다음 위치에 저장:

```bash
mv ~/Downloads/client_secret_*.json ~/.claude/skills/google-sheets/credentials.json
```

**옵션 B — 본인이 직접 GCP에서 만들기**

```bash
python ~/.claude/skills/google-sheets/scripts/auth.py --setup-guide
```

화면에 출력되는 6단계 따라가면 5~7분 소요.

### 3. Python 의존성 설치

```bash
pip install -r ~/.claude/skills/google-sheets/scripts/requirements.txt
```

`pip` 대신 `pip3`, `python3 -m pip install ...` 등 환경에 맞게.

### 4. 첫 인증 (브라우저 한 번)

```bash
python ~/.claude/skills/google-sheets/scripts/auth.py
```

브라우저가 자동으로 열림 → @aptner.com 계정으로 로그인 → "Duse Claude Sheets가 본인의 Google 스프레드시트에 접근하려 합니다" → **[허용]** 클릭 → 완료.

이후 토큰은 `~/.config/gspread/authorized_user.json`에 저장되어 영구 자동 인증.

## 사용

Claude에게 자연어로 요청:

```
"이 시트 A1:D10 읽어줘: https://docs.google.com/spreadsheets/d/.../edit"
"방금 분석 결과를 새 시트로 만들어서 정리해줘"
"https://docs.google.com/... 의 Sheet1 첫 번째 행을 굵게 + 회색 배경으로 해줘"
"새 탭 '시나리오' 추가하고 거기에 [[A,B,C],[1,2,3]] 써줘"
"이 시트에 새로운 행 append해줘"
```

내부적으로 `scripts/sheets.py`의 함수들이 호출됩니다.

### CLI로 직접 호출 (테스트)

```bash
SHEET="https://docs.google.com/spreadsheets/d/XXXXX/edit"

python ~/.claude/skills/google-sheets/scripts/sheets.py read     "$SHEET" Sheet1 A1:D10
python ~/.claude/skills/google-sheets/scripts/sheets.py write    "$SHEET" Sheet1 A1   '[["a","b"],["c","d"]]'
python ~/.claude/skills/google-sheets/scripts/sheets.py append   "$SHEET" Sheet1      '[["new row"]]'
python ~/.claude/skills/google-sheets/scripts/sheets.py format   "$SHEET" Sheet1 A1:B1 '{"textFormat":{"bold":true}}'
python ~/.claude/skills/google-sheets/scripts/sheets.py add_sheet "$SHEET" "새탭"
python ~/.claude/skills/google-sheets/scripts/sheets.py create   "테스트 시트"
python ~/.claude/skills/google-sheets/scripts/sheets.py list_tabs "$SHEET"
```

## FAQ

**Q. 첫 사용 시 브라우저가 안 열려요**
A. SSH/원격 환경일 가능성. `python scripts/auth.py` 직접 실행 → 콘솔에 표시된 URL을 수동 복사해서 본인 PC 브라우저에 붙여넣기.

**Q. 토큰을 다시 발급하고 싶어요**
```bash
python ~/.claude/skills/google-sheets/scripts/auth.py --reset
```

**Q. 외부 회사 시트 (다른 도메인)에 쓸 수 있어요?**
A. OAuth Client가 Internal (@aptner.com 전용)이라 본인의 @aptner.com 계정으로만 인증. 그 계정에 편집 권한 있는 시트라면 어디든 가능.

**Q. `drive.file` scope란?**
A. **본 skill이 만들거나 사용자가 명시적으로 연 파일**만 접근 가능. 본인 Drive 전체를 스캔하지 않음 → 보안 안심.

**Q. rate limit이 걸리면?**
A. 사용자당 60 req/min. 대량 작업은 `write_range`로 batch 처리. 그래도 자주 부족하면 잠시 sleep 후 재시도.

**Q. 인증된 계정이 누군지 확인**
```bash
cat ~/.config/gspread/authorized_user.json | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('client_id','?'))"
```

**Q. 다른 PC로 옮기려면?**
A. 본 폴더 + `~/.config/gspread/authorized_user.json` 함께 복사. 또는 새 PC에서 다시 OAuth flow.

## 파일 구조

```
~/.claude/skills/google-sheets/
├── SKILL.md              # Claude가 자동 로딩하는 skill 정의
├── README.md             # 이 파일 (사람용)
├── credentials.json      # GCP OAuth Client (gitignore, 직원별)
├── .gitignore
└── scripts/
    ├── auth.py           # OAuth flow + 토큰 관리
    ├── sheets.py         # read/write/format/append 핵심 함수
    └── requirements.txt
```

## 트러블슈팅 / 보고

- AX팀 권민재 (mj.kwon@aptner.com)
- 슬랙: `#ax-claude` 채널 (TBD)

## 보안 노트

- `credentials.json`: 회사 OAuth Client. git 커밋 금지. 분실 시 AX팀에 재발급 요청.
- `~/.config/gspread/authorized_user.json`: 본인의 Google 계정 access token. 외부 유출 금지.
- OAuth scope는 `spreadsheets` + `drive.file`로 최소 권한. Drive 전체 스캔 안 됨.
- Internal OAuth Client라 외부인이 client_id 알아도 @aptner.com 외엔 인증 거부.
