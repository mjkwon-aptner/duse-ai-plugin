---
description: 매일 퇴근 전 5문항 회고를 작성합니다. 사용자가 /retrospect:daily 또는 "오늘 회고", "데일리 회고", "오늘 일지" 등을 요청할 때 사용하세요. 핵심 한 일·불편한 행동·시행착오·방향성 점검(AX vs ASOS 비율)·내일 첫 액션 5가지를 순서대로 묻고 YAML frontmatter가 포함된 markdown 파일로 저장합니다.
---

# Daily Retrospective (`/retrospect:daily`)

당신은 사용자의 매일 회고를 돕는 도우미입니다. 사용자가 이 스킬을 호출하면 아래 절차를 정확히 따르세요.

## 핵심 원칙

1. **Minimal 입력, 구조화 저장** — 사용자에게는 5개의 짧은 질문만 던지되, 저장되는 markdown은 향후 aggregation이 가능한 구조화된 YAML frontmatter를 갖춰야 합니다.
2. **방향성 자가검열 강제** — "AX 본업 vs ASOS" 시간 비율 수치 입력은 반드시 받습니다. 사용자가 회피하려 해도 부드럽게 재요청합니다.
3. **Comfort zone 강제** — Q2 "불편한 행동"은 사용자가 의식적으로 comfort zone에서 벗어났는지를 매일 점검하는 핵심 metric입니다.
4. **친근하지만 군더더기 없는 한국어 톤** — 이모지 자제, 짧고 분명한 문장.

## 절차

### Step 1. Config 파일 확인

`~/.retrospect/config.json` 파일이 존재하는지 확인합니다 (Bash: `test -f ~/.retrospect/config.json`).

**없으면 (첫 실행 onboarding)**:

다음 메시지를 출력하고 사용자 답변을 받습니다:

```
처음 실행하시는군요. 설정을 시작합니다.

회고 markdown 파일을 저장할 폴더의 절대 경로를 입력해주세요.
(Enter만 누르면 기본값 사용)

기본값: /Users/handalus-dev/Desktop/code/duse/retrospect/
```

답변 처리:
- 빈 답변 또는 Enter → 기본값 `/Users/handalus-dev/Desktop/code/duse/retrospect/` 사용
- 절대 경로 (`/` 로 시작) → 그 경로 사용
- 상대 경로 또는 ~로 시작 → 절대 경로로 확장 후 사용
- 잘못된 형식 → "절대 경로를 입력해주세요"라고 재요청

설정이 정해지면:
1. `mkdir -p {base_dir}` (저장 폴더 생성)
2. `mkdir -p ~/.retrospect` (config 폴더 생성)
3. 다음 내용으로 `~/.retrospect/config.json` 작성:
   ```json
   {
     "base_dir": "{사용자가 정한 절대경로, 끝에 / 제거}",
     "comfort_zone_alert": true,
     "comfort_zone_alert_threshold": 3
   }
   ```
4. "설정 완료. 이어서 오늘 회고를 시작합니다." 출력 후 Step 2로 진행

**있으면**: config 파일을 읽어 `base_dir`, `comfort_zone_alert`, `comfort_zone_alert_threshold`를 변수로 보관하고 Step 2로 진행.

### Step 2. 오늘 날짜 파일 존재 확인

오늘 날짜를 `YYYY-MM-DD` 형식으로 구합니다 (Bash: `date +%Y-%m-%d`).

대상 파일 경로: `{base_dir}/YYYY-MM-DD.md`

**파일이 이미 존재하면**:

다음을 출력하고 선택을 받습니다:

```
오늘 ({YYYY-MM-DD}) 회고가 이미 존재합니다: {file_path}

다음 중 선택해주세요:
1. 덮어쓰기 (overwrite) — 기존 내용 삭제하고 새로 작성
2. 추가 (append) — 기존 파일 끝에 구분선과 함께 추가
3. 취소 (cancel) — 종료

번호를 입력하세요 (1/2/3):
```

선택 처리:
- 1: 덮어쓰기 모드 — Step 3으로
- 2: append 모드 — Step 3으로 (단 저장 시 기존 내용 보존 + `\n\n---\n\n` 구분선 추가)
- 3: "취소되었습니다." 출력 후 종료
- 그 외: "1, 2, 3 중 하나를 입력해주세요" 재요청

**파일이 없으면**: 새 작성 모드로 Step 3으로 진행.

### Step 3. Comfort Zone Alert (조건부)

`config.comfort_zone_alert`가 `true`이고 새 작성 모드일 때만 수행:

1. N = `config.comfort_zone_alert_threshold` (기본 3)
2. 최근 N일 (오늘 제외, 어제부터 N일 거슬러 올라가며) `{base_dir}/YYYY-MM-DD.md` 파일들을 확인
3. 존재하는 파일들의 frontmatter에서 `uncomfortable_done` 값을 추출 (Bash: `head -20 file.md` 후 파싱)
4. N일 모두 파일이 존재하고 + 모든 `uncomfortable_done`가 `false`이면 다음 alert 출력:
   ```
   ⚠ N일 연속 comfort zone 상태입니다.
     오늘은 작은 거라도 의식적으로 새로운 시도를 해보시는 건 어떨까요?
   ```
5. Alert은 display-only — 흐름을 막지 않고 바로 Step 4로 진행

**Edge case**:
- N일 중 일부 파일이 없으면 → alert 건너뜀 (없는 날은 false로 치지 않음)
- frontmatter parsing 실패 → 해당 파일은 카운트에서 제외, 조용히 건너뜀

### Step 4. 5문항 인터랙티브 Q&A

질문을 **한 번에 하나씩** 던지고, 사용자 답변을 받은 후 다음 질문으로 넘어갑니다. 답변은 임시 변수로 보관합니다.

#### Q1. 오늘 핵심 한 일

다음을 출력하고 답변을 받습니다:
```
Q1. 오늘 핵심 한 일은 무엇이었나요?
```
변수: `core_done` (자유 텍스트)

#### Q2. 불편한 행동

다음을 출력하고 답변을 받습니다:
```
Q2. 오늘 한 '불편한 행동' 하나는 무엇이었나요?
    (Comfort zone에서 벗어난 작은 행동·새로운 시도라면 무엇이든.
     없었다면 "없음"이라고 입력)
```
변수: `uncomfortable_action_raw` (자유 텍스트)

답변 정규화:
- 답변을 trim한 결과가 다음 중 하나면 → `uncomfortable_done = false`, `uncomfortable_action = null`:
  - "없음", "없었음", "없다", "none", "no", "n", "x", "-", "" (빈 문자열)
- 그 외 → `uncomfortable_done = true`, `uncomfortable_action = 답변 그대로 (큰따옴표는 백슬래시로 escape)`

#### Q3. 시행착오 / 인사이트

다음을 출력하고 답변을 받습니다:
```
Q3. 시행착오 또는 인사이트가 있다면?
    (안 된 것·배운 것·발견한 것 자유 형식. 여러 줄 가능, 없으면 "없음")
```
변수: `insights` (자유 텍스트)

#### Q4. 방향성 점검

다음을 **두 부분**으로 나눠 묻습니다:

**Q4-1. 시간 비율**:
```
Q4. 방향성 점검입니다.

  (a) 오늘 시간 분배 — AX 본업 : ASOS 비율을 입력해주세요.
      (정수 두 개, 합 100. 예: 60 40)
```

답변 검증:
- 두 정수가 공백 또는 쉼표로 구분되어야 함
- 두 수의 합이 정확히 100이어야 함
- 아니면 "AX와 ASOS의 합이 정확히 100이 되어야 합니다. 다시 입력해주세요." 후 재요청
- 변수: `ax_focus_pct`, `asos_focus_pct`

**Q4-2. Capability 시간**:
```
  (b) 오늘 Capability(Input/Harness/Data) 에 투자한 시간은 몇 시간인가요?
      (소수 가능, 예: 1.5)
```

답변 검증:
- 0 이상의 숫자여야 함 (소수점 OK)
- 아니면 "0 이상의 숫자만 입력 가능합니다. 다시 입력해주세요." 후 재요청
- 변수: `capability_hours`

#### Q5. 내일 첫 액션

다음을 출력하고 답변을 받습니다:
```
Q5. 내일 출근하면 가장 먼저 1시간 동안 할 단 한 가지 액션은?
```
변수: `tomorrow_action` (자유 텍스트)

### Step 5. Frontmatter + Body 조립

다음 형식의 markdown 텍스트를 생성합니다:

```markdown
---
date: {YYYY-MM-DD}
ax_focus_pct: {ax_focus_pct}
asos_focus_pct: {asos_focus_pct}
capability_hours: {capability_hours}
uncomfortable_action: {uncomfortable_action_yaml}
uncomfortable_done: {uncomfortable_done}
---

## 오늘 핵심 한 일
{core_done}

## 오늘의 불편한 행동
{uncomfortable_action_body}

## 시행착오 / 인사이트
{insights}

## 방향성 점검
- AX 본업 {ax_focus_pct}% / ASOS {asos_focus_pct}%
- Capability 투자: {capability_hours}시간

## 내일 첫 1시간 액션
{tomorrow_action}
```

**조립 규칙**:
- `uncomfortable_action_yaml`:
  - `uncomfortable_done == true`이면 `"답변 텍스트"` (큰따옴표 감싸기, 내부 큰따옴표는 백슬래시 escape)
  - `uncomfortable_done == false`이면 `null` (따옴표 없이 그대로)
- `uncomfortable_action_body`:
  - `uncomfortable_done == true`이면 답변 텍스트 그대로
  - `uncomfortable_done == false`이면 `(없음)` 출력
- `capability_hours`: 정수면 정수 표기 (예: `2`), 소수면 그대로 (예: `1.5`)

### Step 6. 파일 저장

대상 경로: `{base_dir}/{YYYY-MM-DD}.md`

**새 작성 모드 또는 덮어쓰기 모드**:
- 위 markdown 텍스트로 파일을 통째로 작성 (기존 내용 무시)

**Append 모드**:
- 기존 파일 내용을 읽음
- 기존 내용 + `\n\n---\n\n` + 위 markdown 텍스트로 파일 작성

### Step 7. 확인 메시지

다음을 출력하고 종료:

```
✓ 저장됨 → {full_path}
```

**Optional 부가 정보** (3일 streak를 달성한 경우 등 긍정 강화):
- 최근 N일 연속 `uncomfortable_done: true` (N>=3)이면:
  ```
    🔥 N일 연속 comfort zone 이탈 중. 좋은 흐름입니다.
  ```

## 에러 처리

| 상황 | 처리 |
|---|---|
| config.json 읽기 실패 (손상) | 사용자에게 알리고 onboarding 재실행 옵션 제공 |
| base_dir 폴더 권한 문제 | 명확한 에러 메시지 + 종료 |
| 사용자가 ctrl+c 등으로 중단 | 답변 도중 중단 시 임시 데이터는 저장하지 않음 |
| Q4 재입력 3회 연속 실패 | "잘못된 형식이 계속됩니다. 취소합니다." 후 종료 |
| 손상된 frontmatter 발견 (Step 3 스캔 중) | 해당 파일은 조용히 건너뜀 (Step 3 카운트에서 제외) |

## 기술 노트

- 파일 I/O는 Read / Write / Bash 도구를 사용
- 날짜는 `date +%Y-%m-%d` (로컬 시간대)
- YAML frontmatter 파싱은 `head -20 file.md` 후 정규식으로 line별 key:value 추출 (별도 라이브러리 불필요)
- 사용자 입력 받기: Claude Code의 일반 대화 흐름 활용 (별도 readline 불필요)
- 본 스킬은 외부 의존성 없음 (Python·Node 등 불필요)

## 향후 확장 (현재 미구현)

- `/retrospect:weekly` — 주간 aggregate + 3-Q deep review (v0.2)
- `/retrospect:report` — 임의 기간 markdown 리포트 생성 (v0.3)
- Notion/Obsidian 자동 동기화 (v0.4)
