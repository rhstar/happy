"""
package_install.py - 통합 앱 실행에 필요한 코드+데이터만 모아 배포 폴더로 정리

프로젝트 루트(happy/)에서 실행하면, 통합 앱(통합앱.py + pages/) 실행에 꼭 필요한
파일만 '실행패키지/' 폴더로 복사한다. 파이프라인 중간 산출물은 제외.

생성된 폴더는 USB 등으로 통째로 복사해 독립 실행할 수 있다.
(대상 컴퓨터에 파이썬만 있으면 0_최초설치 한 번 실행 후 1번으로 앱 사용 가능.)

조회 대시보드·네트워크 분석·감시 리스트가 하나의 통합 앱(한 포트)으로 합쳐져 있으므로,
링크/포트 하나(http://localhost:8501)로 모든 기능을 사용한다.

실행: python package_install.py   (happy 루트에서)
결과: happy/실행패키지/
"""
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "실행패키지")

# 반드시 필요한 파일
REQUIRED = [
    # 통합 앱 코드
    "통합앱.py",
    "pages/1_조회_대시보드.py",
    "pages/2_네트워크_분석.py",
    "pages/3_감시_리스트.py",
    # 대시보드용 데이터
    "data/dataset.csv",
    "data/risk_ranking_no_embezzle.csv",   # 통합 랭킹 없을 때의 폴백 + 네트워크용
    # 네트워크 앱 데이터 (위험경영진 2013~ 기준)
    "data/network_executives_all.csv",
    "data/network_groups.csv",
    "data/network_risky_set.csv",
    "data/network_matches.csv",
    "data/key_persons.csv",
    "data/key_persons_by_ybe.csv",   # 핵심 인물 분석 재직시점 필터
    # 입력 파일
    "input_files/코스닥_상장.xls",
    "input_files/매매거래정지종목.xls",   # 거래정지 표시·감시 리스트 제외용 (스냅샷)
]

# 있으면 포함(없어도 앱은 폴백 동작). B_3_predict.py 실행 시 생성됨.
OPTIONAL = [
    "data/risk_ranking_all.csv",   # 교차검증 기반 전체 상장사 통합 랭킹
]


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    ok, missing = [], []
    for rel in REQUIRED:
        if _copy(rel):
            ok.append(rel)
        else:
            missing.append(rel)

    opt_ok = [rel for rel in OPTIONAL if _copy(rel)]

    _write_batch(OUT)
    _write_readme(OUT)

    print(f"필수 복사 완료: {len(ok)}개")
    for f in ok:
        print(f"  OK  {f}")
    if opt_ok:
        print(f"\n선택 포함: {len(opt_ok)}개")
        for f in opt_ok:
            print(f"  OK  {f}")
    if "data/risk_ranking_all.csv" not in opt_ok:
        print("\n[안내] data/risk_ranking_all.csv 가 없어 폴백(예측대상만 점수) 상태로 패키징됩니다.")
        print("       전체 상장사(대조군 포함) 점수를 넣으려면 먼저 'python B_3_predict.py'를 실행하세요.")
    if missing:
        print(f"\n누락(필수): {len(missing)}개")
        for f in missing:
            print(f"  --  {f}")
        print("누락 파일은 해당 파이프라인을 먼저 실행해 생성하세요.")

    print(f"\n결과 폴더: {OUT}")
    print("이 폴더를 USB 등으로 복사해 독립 실행할 수 있습니다. (앱: http://localhost:8501)")


def _copy(rel):
    src = os.path.join(ROOT, rel)
    if not os.path.exists(src):
        return False
    dst = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _write_batch(out):
    # python -m streamlit 방식: PATH 문제를 우회해 확실히 실행
    setup = (
        "@echo off\n"
        "chcp 65001 >nul\n"
        'cd /d "%~dp0"\n'
        "echo ============================================\n"
        "echo   최초 설치 (처음 한 번만)\n"
        "echo ============================================\n"
        "echo.\n"
        "echo 필요한 패키지를 설치합니다. 몇 분 걸릴 수 있습니다.\n"
        "echo.\n"
        "python -m pip install --upgrade pip\n"
        "python -m pip install streamlit pyvis pandas openpyxl networkx lxml\n"
        "echo.\n"
        "echo 설치 완료! 이제 1_앱_실행.bat 으로 실행하세요.\n"
        "pause\n"
    )
    run = (
        "@echo off\n"
        "chcp 65001 >nul\n"
        'cd /d "%~dp0"\n'
        "echo 통합 앱을 실행합니다 (포트 8501)...\n"
        "echo 브라우저에서 http://localhost:8501 이 열립니다.\n"
        "echo 왼쪽 사이드바에서 '조회 대시보드', '네트워크 분석', '감시 리스트'를 전환하세요.\n"
        "python -m streamlit run 통합앱.py --server.port 8501\n"
        "pause\n"
    )
    with open(os.path.join(out, "0_최초설치_한번만.bat"), "w", encoding="utf-8") as f:
        f.write(setup)
    with open(os.path.join(out, "1_앱_실행.bat"), "w", encoding="utf-8") as f:
        f.write(run)


def _write_readme(out):
    txt = (
        "========================================\n"
        "  코스닥 무자본 M&A 위험 분석 - 실행 패키지 (통합 앱)\n"
        "========================================\n\n"
        "이 폴더는 독립 실행 패키지입니다.\n"
        "USB 등으로 통째로 복사해 다른 컴퓨터에서도 실행할 수 있습니다.\n"
        "조회 대시보드 / 네트워크 분석 / 감시 리스트가 하나의 앱으로 통합되어 있습니다.\n\n"
        "----------------------------------------\n"
        "[전제 조건]\n"
        "----------------------------------------\n"
        "대상 컴퓨터에 파이썬(Python 3.9 이상)이 설치돼 있어야 합니다.\n"
        "없다면 https://www.python.org 에서 설치하세요.\n"
        "  ※ 설치 시 'Add Python to PATH' 체크 권장\n\n"
        "----------------------------------------\n"
        "[사용 순서]\n"
        "----------------------------------------\n"
        "1) 0_최초설치_한번만.bat  더블클릭\n"
        "   - 처음 한 번만. 필요한 패키지를 설치합니다.\n\n"
        "2) 1_앱_실행.bat  더블클릭  (포트 8501)\n"
        "   - 브라우저에서 http://localhost:8501 이 열립니다.\n"
        "   - 왼쪽 사이드바에서 기능을 전환합니다:\n"
        "       · 조회 대시보드 : 종목 검색 -> 위험도, 거래정지, 위험 경영진\n"
        "       · 네트워크 분석 : 위험기업 경영진 네트워크 탐색\n"
        "       · 감시 리스트   : 위험도 상위 + 위험 경영진 동시 발생 기업\n\n"
        "----------------------------------------\n"
        "[종료]\n"
        "----------------------------------------\n"
        "실행 시 뜨는 검은 창을 닫으면 앱이 종료됩니다.\n\n"
        "----------------------------------------\n"
        "[문제 해결]\n"
        "----------------------------------------\n"
        "- 'python을 찾을 수 없음':\n"
        "  파이썬이 설치 안 됨 또는 PATH 미등록.\n"
        "  python.org에서 재설치('Add to PATH' 체크).\n"
        "- 창이 깜빡하고 사라짐:\n"
        "  0_최초설치를 먼저 실행했는지 확인.\n"
        "- 포트 충돌 에러:\n"
        "  이미 8501 포트로 실행 중인 창을 닫고 다시 실행.\n\n"
        "========================================\n"
        "※ 실명 데이터가 표시됩니다. 로컬에서만\n"
        "  사용하고 화면을 외부에 공유하지 마세요.\n"
        "※ 매매거래정지 목록은 다운로드 시점의\n"
        "  스냅샷이므로 주기적 갱신이 필요합니다.\n"
        "========================================\n"
    )
    with open(os.path.join(out, "사용법.txt"), "w", encoding="utf-8") as f:
        f.write(txt)


if __name__ == "__main__":
    main()