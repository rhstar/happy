"""
clean_run.py — 클린 런 전체 파이프라인 무인 실행

A_1 → A_2 → A_3(재시도 포함) → B_1(3년) → B_2 → B_3
→ C_1 → C_3 → C_4 → C_5 → B_4 → check_coverage
순서로 실행한다. 중간에 하나라도 실패하면 거기서 멈춘다.

- A_4, C_2(임원 수집)는 실행하지 않는다. 대신 시작 전에
  data/network_executives_all.csv, data/current_executives.csv 존재를 확인한다.
- A_3(raw 수집)는 API 오류로 끊길 수 있어 최대 3회 재시도한다.
  (resume 기능이 있어 재실행하면 이어서 수집한다)
- 전체 출력은 화면과 run_all_log.txt 에 동시에 기록된다.

실행: python RUN_ALL.py   (happy 루트에서)
"""
import os
import sys
import time
import subprocess
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "run_all_log.txt")

# (스크립트, 추가 인자, A_3 재시도 여부)
STEPS = [
    ("A_1_build_dataset.py",          [],    False),
    ("A_2_build_predict_targets.py",  [],    False),
    ("A_3_collect_raw_disclosures.py",[],    True),   # 오래 걸림, 재시도 허용
    ("B_1_aggregate_features.py",     ["3"], False),  # 3년 창
    ("B_2_train_model.py",            [],    False),
    ("B_3_predict.py",                [],    False),
    ("C_1_build_risky_set.py",        [],    False),
    ("C_3_build_groups.py",           [],    False),
    ("C_4_match.py",                  [],    False),
    ("C_5_analyze_persons.py",        [],    False),
    ("B_4_validate_signals.py",       [],    False),
    ("check_coverage.py",             [],    False),
]

MAX_RETRY = 3          # A_3 재시도 횟수
RETRY_WAIT = 60        # 재시도 전 대기(초)


def log(msg):
    line = msg if msg.endswith("\n") else msg + "\n"
    sys.stdout.write(line)
    sys.stdout.flush()
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line)


def run_script(script, args):
    """스크립트 하나 실행. 출력을 화면+로그로 스트리밍. 반환: 종료코드"""
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
    # 필수 입력 파일
    for rel in ["input_files/실질심사법인_전체.xls",
                "input_files/코스닥_상장.xls",
                "input_files/매매거래정지종목.xls"]:
        if not os.path.exists(os.path.join(ROOT, rel)):
            problems.append(f"입력 파일 없음: {rel}")
    # 보존해야 하는 임원 데이터 (A_4·C_2를 안 돌리므로 필수)
    for rel in ["data/network_executives_all.csv",
                "data/current_executives.csv"]:
        if not os.path.exists(os.path.join(ROOT, rel)):
            problems.append(f"임원 데이터 없음(백업 복원 필요): {rel}")
    # .env
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
    open(LOG, "w", encoding="utf-8").close()  # 로그 초기화
    log(f"===== 클린 런 시작: {datetime.now():%Y-%m-%d %H:%M:%S} =====")

    problems = precheck()
    if problems:
        log("\n[중단] 사전 확인 실패:")
        for pb in problems:
            log(f"  - {pb}")
        sys.exit(1)
    log("[사전 확인] 입력 파일·임원 데이터·.env 모두 확인됨\n")

    t_total = time.time()
    for script, args, retryable in STEPS:
        label = f"{script} {' '.join(args)}".strip()
        log(f"\n{'='*60}\n▶ {label}   ({datetime.now():%H:%M:%S})\n{'='*60}")
        t0 = time.time()

        attempts = MAX_RETRY if retryable else 1
        code = 1
        for i in range(1, attempts + 1):
            if i > 1:
                log(f"  [재시도 {i}/{attempts}] {RETRY_WAIT}초 대기 후 이어서 수집...")
                time.sleep(RETRY_WAIT)
            code = run_script(script, args)
            if code == 0:
                break
        elapsed = time.time() - t0
        if code != 0:
            log(f"\n[실패] {label} (종료코드 {code}, {elapsed/60:.1f}분) — 여기서 중단")
            log("로그: run_all_log.txt 확인 후, 문제 해결하고 RUN_ALL.py 재실행")
            log("(A_3는 resume 기능이 있어 재실행 시 이어서 수집됩니다)")
            sys.exit(code)
        log(f"[완료] {label} ({elapsed/60:.1f}분)")

    log(f"\n{'='*60}")
    log(f"===== 전체 완료: {datetime.now():%Y-%m-%d %H:%M:%S} "
        f"(총 {(time.time()-t_total)/60:.1f}분) =====")
    log("다음: streamlit run 통합앱.py 로 세 페이지 확인")
    log("     B_2의 AUC, B_4의 lift 수치를 확인하고 앱 캡션 수치 갱신")


if __name__ == "__main__":
    main()