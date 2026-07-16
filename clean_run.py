"""
clean_run.py — 클린 런 전체 파이프라인 무인 실행 (임원 수집 포함, 진짜 처음부터)

A_1 → A_2 → A_3(재시도) → A_4(재시도) → B_1(3년) → B_2 → B_3
→ C_1 → C_2(재시도) → C_3 → C_4 → C_5 → B_4 → check_coverage

- 오래 걸리는 수집(A_3, A_4, C_2)은 API 오류로 끊기면 최대 3회 재시도.
  ※ A_3만 resume(이어받기) 기능이 있고, A_4·C_2는 재시도 시 처음부터 다시 돈다.
- 하나라도 실패하면 그 지점에서 중단.
- 전체 출력은 화면과 clean_run_log.txt 에 동시 기록.

예상 소요: A_3 15~20분 + A_4 10~15분 + C_2 30분± + 나머지 몇 분 = 약 1시간~1시간 20분

실행: python clean_run.py   (happy 루트에서)
"""
import os
import sys
import time
import subprocess
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "clean_run_log.txt")

# (스크립트, 추가 인자, 재시도 여부)
STEPS = [
    ("A_1_build_dataset.py",           [],    False),
    ("A_2_build_predict_targets.py",   [],    False),
    ("A_3_collect_raw_disclosures.py", [],    True),   # 공시 원자료 5년 (resume 가능)
    ("A_4_collect_current_execs.py",   [],    True),   # 현재 상장사 임원
    ("B_1_aggregate_features.py",      ["3"], False),  # 3년 창
    ("B_2_train_model.py",             [],    False),
    ("B_3_predict.py",                 [],    False),
    ("C_1_build_risky_set.py",         [],    False),
    ("C_2_collect_execs.py",           [],    True),   # 위험기업 임원 (C_1 이후여야 함)
    ("C_3_build_groups.py",            [],    False),
    ("C_4_match.py",                   [],    False),
    ("C_5_analyze_persons.py",         [],    False),
    ("B_4_validate_signals.py",        [],    False),
    ("check_coverage.py",              [],    False),
]

MAX_RETRY = 3
RETRY_WAIT = 60        # 재시도 전 대기(초)


def log(msg):
    line = msg if msg.endswith("\n") else msg + "\n"
    sys.stdout.write(line)
    sys.stdout.flush()
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line)


def run_script(script, args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.Popen(
        [sys.executable, "-u", os.path.join(ROOT, script), *args],
        cwd=ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    for line in p.stdout:
        log("    " + line.rstrip())
    p.wait()
    return p.returncode


def precheck():
    problems = []
    for rel in ["input_files/실질심사법인_전체.xls",
                "input_files/코스닥_상장.xls",
                "input_files/매매거래정지종목.xls"]:
        if not os.path.exists(os.path.join(ROOT, rel)):
            problems.append(f"입력 파일 없음: {rel}")
    if not os.path.exists(os.path.join(ROOT, ".env")):
        problems.append(".env 없음 (DART_API_KEY 필요)")
    # 고아 resume 로그: csv 없이 completed.txt만 있으면 수집이 통째로 건너뛰어짐
    raw_csv = os.path.join(ROOT, "data/raw_disclosures.csv")
    raw_log = os.path.join(ROOT, "data/raw_disclosures_completed.txt")
    if os.path.exists(raw_log) and not os.path.exists(raw_csv):
        os.remove(raw_log)
        log("[정리] raw_disclosures.csv 없이 completed 로그만 있어 로그를 삭제함 (재수집 위해)")
    return problems


def main():
    open(LOG, "w", encoding="utf-8").close()
    log(f"===== 클린 런 시작: {datetime.now():%Y-%m-%d %H:%M:%S} =====")
    log("임원 수집 포함 — 진짜 처음부터. 예상 1시간~1시간 20분\n")

    problems = precheck()
    if problems:
        log("[중단] 사전 확인 실패:")
        for pb in problems:
            log(f"  - {pb}")
        sys.exit(1)
    log("[사전 확인] 입력 파일·.env 확인됨")

    t_total = time.time()
    for script, args, retryable in STEPS:
        label = f"{script} {' '.join(args)}".strip()
        log(f"\n{'='*60}\n▶ {label}   ({datetime.now():%H:%M:%S})\n{'='*60}")
        t0 = time.time()

        attempts = MAX_RETRY if retryable else 1
        code = 1
        for i in range(1, attempts + 1):
            if i > 1:
                log(f"  [재시도 {i}/{attempts}] {RETRY_WAIT}초 대기 후 다시 실행...")
                time.sleep(RETRY_WAIT)
            code = run_script(script, args)
            if code == 0:
                break
        elapsed = time.time() - t0
        if code != 0:
            log(f"\n[실패] {label} (종료코드 {code}, {elapsed/60:.1f}분) — 여기서 중단")
            log("로그: clean_run_log.txt 확인 후, 문제 해결하고 clean_run.py 재실행")
            sys.exit(code)
        log(f"[완료] {label} ({elapsed/60:.1f}분)")

    log(f"\n{'='*60}")
    log(f"===== 전체 완료: {datetime.now():%Y-%m-%d %H:%M:%S} "
        f"(총 {(time.time()-t_total)/60:.1f}분) =====")
    log("다음: streamlit run 통합앱.py 로 세 페이지 확인")
    log("     B_2의 AUC, B_4의 lift 수치를 확인하고 앱 캡션 수치 갱신")


if __name__ == "__main__":
    main()