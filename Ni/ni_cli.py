"""
니켈 나노입자 AI 합성 — 명령줄 도구

    python ni_cli.py suggest [-k 3]                 다음 실험 추천
    python ni_cli.py add C_NI R_OH R_HZ R_P SIZE    실측 결과 입력 (SIZE: nm)
    python ni_cli.py predict C_NI R_OH R_HZ R_P     입경 예측
    python ni_cli.py best                           최종 레시피 (40 nm)
    python ni_cli.py list                           실험 데이터 보기
    python ni_cli.py demo [-n 15] [--reset]         가상 반응기로 자동 최적화
    python ni_cli.py reset                          실험 데이터 삭제
"""

import argparse
import sys

import numpy as np

import ni_model as m

sys.stdout.reconfigure(encoding="utf-8")


def show(s: m.Suggestion, idx: int | None = None):
    head = f"[{s.kind}{' #' + str(idx) if idx else ''}]"
    pred = "예측 불가(데이터 부족)" if np.isnan(s.pred_nm) else \
        f"예측 {s.pred_nm:.1f} nm (95% {s.low_nm:.1f}–{s.high_nm:.1f})"
    print(f"\n{head} {pred}")
    print(s.recipe.procedure())


def main():
    ap = argparse.ArgumentParser(description="회분식 반응기 니켈 나노입자 AI 합성 (목표 40 nm)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("suggest"); p.add_argument("-k", type=int, default=3)
    p = sub.add_parser("add")
    for k in m.VAR_KEYS:
        p.add_argument(k, type=float)
    p.add_argument("size", type=float); p.add_argument("--note", default="")
    p = sub.add_parser("predict")
    for k in m.VAR_KEYS:
        p.add_argument(k, type=float)
    sub.add_parser("best"); sub.add_parser("list"); sub.add_parser("reset")
    p = sub.add_parser("demo"); p.add_argument("-n", type=int, default=15)
    p.add_argument("--reset", action="store_true")
    a = ap.parse_args()

    store, opt = m.ExperimentStore(), m.NiOptimizer()
    df = store.load()

    if a.cmd == "suggest":
        for i, s in enumerate(opt.suggest(df, k=a.k), 1):
            show(s, i)
    elif a.cmd == "add":
        r = m.Recipe(a.c_ni, a.r_oh, a.r_hz, a.r_p)
        df = store.add(r, a.size, source="real", note=a.note)
        print(f"저장 완료 (총 {len(df)}건): {m.DATA_FILE}")
    elif a.cmd == "predict":
        if not opt.fit(df):
            sys.exit("데이터가 3건 이상 필요합니다.")
        med, lo, hi = (float(v[0]) for v in opt.predict(np.array([a.c_ni, a.r_oh, a.r_hz, a.r_p])))
        print(f"예측 입경 {med:.1f} nm (95% {lo:.1f}–{hi:.1f} nm)")
    elif a.cmd == "best":
        s = opt.best_recipe(df)
        if s is None:
            sys.exit("데이터가 3건 이상 필요합니다.")
        show(s); print("\n" + "\n".join(f"  {k}: {v:.3f}" for k, v in s.recipe.amounts().items()))
    elif a.cmd == "list":
        print(df.to_string(index=False) if len(df) else "데이터 없음")
    elif a.cmd == "reset":
        store.clear(); print("실험 데이터를 삭제했습니다.")
    elif a.cmd == "demo":
        if a.reset:
            store.clear()

        def cb(i, s, size):
            print(f"{i:2d}회 [{s.kind}] c_Ni={s.recipe.c_ni:.3f} NaOH={s.recipe.r_oh:.2f} "
                  f"N2H4={s.recipe.r_hz:.2f} P={s.recipe.r_p:.3f} → {size:.1f} nm")
        df = m.run_closed_loop(a.n, store, callback=cb)
        err = (df["size_nm"] - m.TARGET_NM).abs()
        print(f"\n최소 오차 {err.min():.2f} nm (실험 {int(df.loc[err.idxmin(), 'id'])}번)")
        s = m.NiOptimizer().best_recipe(df)
        show(s)


if __name__ == "__main__":
    main()
