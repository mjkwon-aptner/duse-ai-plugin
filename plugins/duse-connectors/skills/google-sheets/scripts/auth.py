"""Google OAuth Loopback Flow + 토큰 관리 (멀티 Workspace 지원).

두꺼비세상 그룹은 여러 Google Workspace를 운영:
  - @aptner.com  → credentials_aptner.json
  - @duse.kr     → credentials_duse.json

각 도메인별로 별도 OAuth Client + 별도 토큰 파일을 사용합니다.

credentials JSON 탐색 우선순위:
  1. ~/.config/duse-connectors/credentials_<domain>.json   (사용자 권장 위치)
  2. <skill_dir>/credentials_<domain>.json                  (legacy / dev)

사용:
    python auth.py                # 인증 확인 (필요 시 OAuth flow 실행)
    python auth.py --setup-guide  # GCP 셋업 step-by-step 출력
    python auth.py --reset        # 저장된 토큰 삭제 (재인증 강제)
    python auth.py --switch       # 도메인 다시 선택

환경변수 (override):
    DUSE_GROUP_DOMAIN=aptner.com  # 또는 duse.kr
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
USER_CONFIG_DIR = Path.home() / ".config" / "duse-connectors"
TOKEN_DIR = Path.home() / ".config" / "gspread"
DOMAIN_CACHE_FILE = TOKEN_DIR / ".duse_group_domain"

# 도메인별 메타 (credentials 파일명은 _resolve_credentials()로 동적 lookup)
DOMAIN_CONFIG = {
    "aptner.com": {
        "cred_filename": "credentials_aptner.json",
        "token": TOKEN_DIR / "authorized_user_aptner.json",
        "label": "아파트너 (@aptner.com)",
    },
    "duse.kr": {
        "cred_filename": "credentials_duse.json",
        "token": TOKEN_DIR / "authorized_user_duse.json",
        "label": "두꺼비세상 (@duse.kr)",
    },
}

# legacy single-tenant fallback
LEGACY_CRED_FILENAME = "credentials.json"
LEGACY_TOKEN = TOKEN_DIR / "authorized_user.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

SETUP_GUIDE = """
=========================================================
  Google Sheets Skill — GCP OAuth Client 셋업 가이드
=========================================================

[전제] 본인 회사 계정(@aptner.com 또는 @duse.kr)으로
       https://console.cloud.google.com 접속

1. 새 프로젝트 만들기
   - 상단 프로젝트 드롭다운 > '새 프로젝트'
   - 이름: duse-claude-sheets-<도메인>
       (예: duse-claude-sheets-aptner / duse-claude-sheets-duse)
   - 조직: 본인 회사 도메인(aptner.com 또는 duse.kr) 선택
   - 만들기

2. API 활성화
   - 좌측 메뉴 > API 및 서비스 > 라이브러리
   - 'Google Sheets API' 검색 → 사용 설정
   - 'Google Drive API' 검색 → 사용 설정

3. OAuth 동의 화면 설정
   - 좌측 메뉴 > API 및 서비스 > OAuth 동의 화면
   - 시작/구성 클릭
   - 앱 이름: Duse Claude Sheets
   - User Type: Internal ⭐ (조직 전용)
   - 이메일 입력 후 진행 → 만들기

4. 범위(Scope) 추가
   - 데이터 액세스 > 범위 추가 또는 삭제
   - 'spreadsheets' 검색 → .../auth/spreadsheets 체크
   - 'drive.file' 검색 → .../auth/drive.file 체크
   - 업데이트 → 저장

5. OAuth Client ID 만들기
   - API 및 서비스 > 사용자 인증 정보
   - + 사용자 인증 정보 만들기 > OAuth 클라이언트 ID
   - 애플리케이션 유형: 데스크톱 앱 ⭐
   - 이름: Duse Sheets Skill Desktop
   - 만들기 → JSON 다운로드

6. JSON 파일을 다음 위치에 저장 (사용자 권장 경로):
   mkdir -p ~/.config/duse-connectors
   mv ~/Downloads/client_secret_*.json \\
      ~/.config/duse-connectors/credentials_aptner.json   # 또는 _duse.json

7. 의존성 설치 (1회)
   pip install -r <plugin>/skills/google-sheets/scripts/requirements.txt

8. 첫 인증 (테스트)
   python <plugin>/skills/google-sheets/scripts/auth.py
   → 도메인 선택 (한 개만 있으면 자동) → 브라우저 자동 실행
   → 본인 회사 계정으로 로그인 → [허용] → 끝

[멀티 Workspace 안내]
  두꺼비세상 그룹은 aptner.com과 duse.kr 두 Workspace를 운영하므로
  각 도메인마다 별도 GCP 프로젝트 + OAuth Client가 필요합니다.
  AX팀이 두 곳 모두 셋업해두면, 직원은 본인 도메인으로 자동 분기됩니다.
"""


def _resolve_credentials(filename: str) -> Path:
    """credentials JSON 탐색 — user config 우선, skill 폴더 fallback.

    파일이 어느 쪽에도 없으면 권장 위치(USER_CONFIG_DIR)를 반환 (에러 메시지용).
    """
    for base in (USER_CONFIG_DIR, SKILL_DIR):
        f = base / filename
        if f.exists():
            return f
    return USER_CONFIG_DIR / filename


def get_creds_path(domain: str) -> Path:
    return _resolve_credentials(DOMAIN_CONFIG[domain]["cred_filename"])


def show_setup_guide() -> None:
    print(SETUP_GUIDE)
    print("\n[현재 상태]")
    for domain, cfg in DOMAIN_CONFIG.items():
        path = get_creds_path(domain)
        ok = "✅" if path.exists() else "❌"
        token_ok = "✅ 토큰 있음" if cfg["token"].exists() else "⏳ 토큰 없음"
        print(f"  {ok} {cfg['label']:30s} | credentials: {path} | {token_ok}")
    legacy_path = _resolve_credentials(LEGACY_CRED_FILENAME)
    if legacy_path.exists():
        print(f"  ℹ️  legacy credentials.json 발견: {legacy_path}")
    print(f"\n[권장 위치] {USER_CONFIG_DIR}/")
    print(f"[Skill 위치] {SKILL_DIR}/")


def detect_domain(interactive: bool = True) -> str | None:
    """사용자가 어느 회사 계정으로 인증할지 결정."""
    # 1. 환경변수
    env = os.environ.get("DUSE_GROUP_DOMAIN")
    if env:
        env = env.strip()
        if env in DOMAIN_CONFIG:
            return env

    # 2. 캐시
    if DOMAIN_CACHE_FILE.exists():
        cached = DOMAIN_CACHE_FILE.read_text().strip()
        if cached in DOMAIN_CONFIG:
            return cached

    # 3. credentials 파일 자동 감지
    available = [d for d in DOMAIN_CONFIG if get_creds_path(d).exists()]
    if len(available) == 1:
        domain = available[0]
        TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        DOMAIN_CACHE_FILE.write_text(domain)
        return domain
    if len(available) > 1 and interactive:
        print("\n어느 회사 계정으로 인증하시겠습니까?")
        for i, d in enumerate(available, 1):
            print(f"  {i}. {DOMAIN_CONFIG[d]['label']}")
        choice = input("선택 (번호 또는 도메인): ").strip()
        domain = None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(available):
                domain = available[idx]
        elif choice in available:
            domain = choice
        if not domain:
            domain = available[0]
            print(f"⚠️ 유효하지 않은 선택, 기본값 '{domain}' 사용")
        TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        DOMAIN_CACHE_FILE.write_text(domain)
        return domain

    return None


def _resolve_files() -> tuple[Path, Path, str | None]:
    """현재 사용할 (credentials_path, token_path, domain) 반환."""
    domain = detect_domain()
    if domain and domain in DOMAIN_CONFIG:
        return get_creds_path(domain), DOMAIN_CONFIG[domain]["token"], domain
    return _resolve_credentials(LEGACY_CRED_FILENAME), LEGACY_TOKEN, None


def reset_token(all_domains: bool = False) -> None:
    if all_domains:
        targets = [cfg["token"] for cfg in DOMAIN_CONFIG.values()] + [LEGACY_TOKEN, DOMAIN_CACHE_FILE]
    else:
        _, token_file, _ = _resolve_files()
        targets = [token_file]
    removed = 0
    for t in targets:
        if t.exists():
            t.unlink()
            print(f"🗑  삭제: {t}")
            removed += 1
    if removed == 0:
        print("   삭제할 파일 없음")
    print("   다음 호출 시 OAuth flow 재실행됩니다.")


def switch_domain() -> None:
    if DOMAIN_CACHE_FILE.exists():
        DOMAIN_CACHE_FILE.unlink()
        print("🔄 도메인 선택 초기화. 다음 호출 시 다시 선택합니다.")
    else:
        print("   캐시된 도메인 선택 없음")


def ensure_authed():
    """인증 보장 — 모든 sheets 작업 전 호출."""
    creds_file, token_file, domain = _resolve_files()

    if not creds_file.exists():
        domain_label = DOMAIN_CONFIG[domain]["label"] if domain else "(any)"
        hint = (
            f"\n   권장 위치: {USER_CONFIG_DIR / (DOMAIN_CONFIG[domain]['cred_filename'] if domain else LEGACY_CRED_FILENAME)}"
            if domain else f"\n   권장 위치: {USER_CONFIG_DIR / LEGACY_CRED_FILENAME}"
        )
        raise FileNotFoundError(
            f"\n❌ credentials 파일이 없습니다.\n"
            f"   도메인: {domain_label}{hint}\n"
            f"   셋업 가이드: python {Path(__file__)} --setup-guide\n"
        )

    TOKEN_DIR.mkdir(parents=True, exist_ok=True)

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        except Exception as e:
            print(f"⚠️ 기존 토큰 읽기 실패 ({e}). 재인증 진행.")
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            token_file.write_text(creds.to_json())
            return creds
        except Exception as e:
            print(f"⚠️ 토큰 갱신 실패 ({e}). OAuth flow 재실행.")
            creds = None

    domain_label = DOMAIN_CONFIG[domain]["label"] if domain else "(domain unknown)"
    print(f"🔐 Google OAuth 인증을 시작합니다. 도메인: {domain_label}")
    print(f"   브라우저가 자동으로 열립니다. 본인 회사 계정으로 로그인 후 [허용]을 클릭해주세요.")
    print(f"   (브라우저가 안 열리면 콘솔에 표시된 URL을 수동 복사해서 붙여넣으세요.)")

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
    creds = flow.run_local_server(
        port=0,
        open_browser=True,
        success_message="✅ 인증 완료. 이 창을 닫고 Claude 콘솔로 돌아가세요.",
    )
    token_file.write_text(creds.to_json())
    print(f"✅ 토큰 저장: {token_file}")
    return creds


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--setup-guide" in args or "-h" in args or "--help" in args:
        show_setup_guide()
    elif "--reset" in args:
        reset_token(all_domains="--all" in args)
    elif "--switch" in args:
        switch_domain()
    else:
        try:
            creds = ensure_authed()
            _, _, domain = _resolve_files()
            label = DOMAIN_CONFIG[domain]["label"] if domain else "단일 도메인 모드"
            print(f"✅ 인증 확인 완료 ({label}). 이제 시트 작업 가능.")
        except FileNotFoundError as e:
            print(e)
            print("👉 셋업 가이드: python scripts/auth.py --setup-guide")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 인증 실패: {e}")
            sys.exit(1)
