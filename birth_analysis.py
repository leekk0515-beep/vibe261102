"""
대한민국 출생아수·합계출산율·자연증가 데이터 클렌징 및 다각도 분석
원본: KOSIS 「인구동향조사」 (통계표 INH_1B8000F_01), 1970~2025

GUI(birth_gui.py)와 콘솔 실행에서 함께 쓰는 클렌징/분석/그래프 함수 모음입니다.

실행: python birth_analysis.py [엑셀경로]
출력: birth_output/ 폴더 (정제 데이터 CSV, 분석 결과 CSV, 차트 PNG)
"""
import sys
import warnings
from pathlib import Path

import matplotlib.ticker as mticker
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

DEFAULT_XLSX = Path(__file__).parent / "출생아수__합계출산율__자연증가_등.xlsx"
OUT_DIR = Path(__file__).parent / "birth_output"

# 원본 항목명 -> 분석용 컬럼명
COLUMN_MAP = {
    "출생아수(명)": "출생아수",
    "자연증가건수(명)": "자연증가건수",
    "조출생률(천명당)": "조출생률",
    "자연증가율(천명당)": "자연증가율",
    "합계출산율(명)": "합계출산율",
    "출생성비(명)": "출생성비",
}
INDICATORS = list(COLUMN_MAP.values())

BLUE, RED, GRAY = "#2a6fdb", "#d9534f", "gray"


def setup_korean_font():
    import matplotlib.pyplot as plt

    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False


# ──────────────────────────────────────────────
# 1. 데이터 클렌징
# ──────────────────────────────────────────────
def load_and_clean(path):
    """엑셀을 읽어 '연도 x 지표' DataFrame과 클렌징 내역(log 리스트)을 반환"""
    log = []
    raw = pd.read_excel(path, sheet_name=0, header=None)
    log.append(f"원본: {raw.shape[0]}행 x {raw.shape[1]}열 (행=지표, 열=연도인 가로형 구조)")

    # (1) 첫 행은 연도 헤더, 첫 열은 지표명 → 전치해서 세로형으로 변환
    raw = raw.set_index(0)
    raw.index = raw.index.astype(str).str.strip()
    df = raw.T.rename(columns={"기본항목별": "연도_원본"})
    if "연도_원본" not in df or not set(COLUMN_MAP) <= set(df.columns):
        raise ValueError("출생아수/합계출산율 통계표 형식이 아닙니다.")
    log.append("전치(Transpose): 연도를 행, 지표를 열로 변환")

    # (2) 연도 정리: '2025 p)' 같은 잠정치 표기를 분리
    year_str = df["연도_원본"].astype(str).str.strip()
    df["잠정치"] = year_str.str.contains("p", case=False)
    df["연도"] = pd.to_numeric(year_str.str.extract(r"(\d{4})")[0], errors="coerce").astype("Int64")

    # (3) 지표명 정리 및 숫자형 변환 (쉼표·공백·'-' 등 비숫자 → NaN)
    df = df.rename(columns=COLUMN_MAP)
    for col in INDICATORS:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "").str.strip(), errors="coerce")
    log.append("지표명 단순화 및 숫자형 변환: " + ", ".join(INDICATORS))

    df = df.drop(columns="연도_원본").dropna(subset=["연도"])

    # (4) 중복 연도 제거 및 정렬
    dup = df["연도"].duplicated().sum()
    df = df.drop_duplicates(subset="연도", keep="last").sort_values("연도")

    # (5) 정수형이어야 하는 컬럼 정리
    for col in ["출생아수", "자연증가건수"]:
        df[col] = df[col].round().astype("Int64")

    df = df.set_index("연도")[INDICATORS + ["잠정치"]]
    df.index = df.index.astype(int)
    df.columns.name = None

    # (6) 품질 점검
    missing_years = sorted(set(range(df.index.min(), df.index.max() + 1)) - set(df.index))
    invalid = df[(df["출생아수"] <= 0) | (df["합계출산율"] <= 0) | ~df["출생성비"].between(90, 130)]
    log += [
        f"정제 결과: {len(df)}개 연도 ({df.index.min()}~{df.index.max()})",
        f"중복 연도 제거: {dup}건",
        f"결측치: {int(df[INDICATORS].isna().sum().sum())}건",
        f"누락 연도: {', '.join(map(str, missing_years)) or '없음'}",
        f"잠정치 연도: {', '.join(map(str, df.index[df['잠정치']])) or '없음'} (연도의 'p)' 표기 분리)",
        f"범위 이상치(출생아수/출산율 ≤0, 성비 90~130 벗어남): {len(invalid)}건",
    ]
    return add_features(df), log


# ──────────────────────────────────────────────
# 2. 파생 변수
# ──────────────────────────────────────────────
def add_features(df):
    df = df.copy()
    births = df["출생아수"].astype(float)
    df["사망자수(추정)"] = df["출생아수"] - df["자연증가건수"]  # 자연증가 = 출생 - 사망
    df["출생아수_전년대비"] = df["출생아수"].diff()
    df["출생아수_증감률(%)"] = births.pct_change() * 100
    df["출생아수_5년이동평균"] = births.rolling(5).mean()
    df["합계출산율_전년대비"] = df["합계출산율"].diff()
    df["1970년대비(%)"] = births / births.iloc[0] * 100
    # 조출생률(천명당) = 출생아수 / 총인구 * 1000 → 총인구 역산
    df["총인구(추정,만명)"] = births / df["조출생률"] * 1000 / 10_000
    df["연대"] = (df.index // 10 * 10).astype(str) + "년대"
    return df


# ──────────────────────────────────────────────
# 3. 다각도 분석
# ──────────────────────────────────────────────
def analyze(df):
    """분석 결과를 dict로 반환 (표는 DataFrame, 요약은 문자열)"""
    first, last = int(df.index.min()), int(df.index.max())
    b0, b1 = int(df.loc[first, "출생아수"]), int(df.loc[last, "출생아수"])
    cagr = ((b1 / b0) ** (1 / (last - first)) - 1) * 100

    decade = df.groupby("연대").agg(
        출생아수_평균=("출생아수", "mean"),
        합계출산율_평균=("합계출산율", "mean"),
        자연증가건수_평균=("자연증가건수", "mean"),
        출생성비_평균=("출생성비", "mean"),
    )
    decade[["출생아수_평균", "자연증가건수_평균"]] = decade[["출생아수_평균", "자연증가건수_평균"]].round(0)
    decade = decade.round(2)

    extremes = pd.DataFrame(
        {
            col: {
                "최고": df[col].astype(float).max(),
                "최고 연도": str(df[col].astype(float).idxmax()),
                "최저": df[col].astype(float).min(),
                "최저 연도": str(df[col].astype(float).idxmin()),
            }
            for col in ["출생아수", "합계출산율", "자연증가건수", "출생성비"]
        }
    ).T

    conditions = {
        "합계출산율 2.1 미만 (인구대체수준 붕괴)": df["합계출산율"] < 2.1,
        "합계출산율 1.3 미만 (초저출산)": df["합계출산율"] < 1.3,
        "합계출산율 1.0 미만": df["합계출산율"] < 1.0,
        "출생아수 50만 명 미만": df["출생아수"] < 500_000,
        "출생아수 30만 명 미만": df["출생아수"] < 300_000,
        "자연증가 마이너스 (인구 자연감소)": df["자연증가건수"] < 0,
    }
    milestones = {
        name: (f"{df.index[cond].min()}년" if cond.any() else "해당 없음") for name, cond in conditions.items()
    }

    chg = df["출생아수_증감률(%)"].dropna()
    rebound = df.loc[df.index >= 2015, "출생아수_전년대비"]
    rebound = rebound[rebound > 0]
    high_ratio = df[df["출생성비"] > 107]

    summary = {
        "분석 기간": f"{first}~{last}년 ({len(df)}개 연도)",
        "출생아수 변화": f"{b0:,}명 → {b1:,}명 ({b1 / b0 * 100:.1f}% 수준)",
        "연평균 증감률(CAGR)": f"{cagr:.2f}%",
        "합계출산율 변화": f"{df.loc[first, '합계출산율']}명 → {df.loc[last, '합계출산율']}명",
        "최대 감소 연도": ", ".join(f"{y}({v:.1f}%)" for y, v in chg.nsmallest(3).items()),
        "최대 증가 연도": ", ".join(f"{y}(+{v:.1f}%)" for y, v in chg.nlargest(3).items()),
        "2015년 이후 반등": ", ".join(f"{y}(+{int(v):,}명)" for y, v in rebound.items()) or "없음",
        "출생성비 107 초과": (
            f"{len(high_ratio)}개 연도 ({high_ratio.index.min()}~{high_ratio.index.max()}년), "
            f"최고 {df['출생성비'].max()} ({df['출생성비'].idxmax()}년)"
            if len(high_ratio) else "없음"
        ),
    }

    corr = df[["출생아수", "합계출산율", "조출생률", "자연증가건수", "출생성비"]].astype(float).corr().round(3)

    return {
        "summary": summary,
        "milestones": milestones,
        "describe": df[INDICATORS].astype(float).describe().round(2),
        "decade": decade,
        "extremes": extremes,
        "top_drop": chg.nsmallest(10),
        "top_rise": chg.nlargest(10),
        "corr": corr,
    }


# ──────────────────────────────────────────────
# 4. 그래프 (각 함수는 matplotlib Axes에 그림)
# ──────────────────────────────────────────────
def plot_births(ax, df, start=1970, end=2025):
    """출생아수 라인 그래프 (최고·최저·마지막 연도 주석)"""
    births = df.loc[start:end, "출생아수"].astype(int)
    years = births.index

    ax.plot(years, births, color=BLUE, lw=2.2, marker="o", ms=3.5)
    ax.fill_between(years, births, color=BLUE, alpha=0.08)

    peak, low, last = births.idxmax(), births.idxmin(), years[-1]
    points = {last: ("", (-55, 30)), peak: ("최고", (10, 15)), low: ("최저", (-60, -35))}
    for y, (label, offset) in points.items():
        if y == last and df.loc[y, "잠정치"]:
            label = f"{label} 잠정".strip()
        ax.annotate(
            f"{y}년 {label}".strip() + f"\n{births[y]:,}명",
            xy=(y, births[y]), xytext=offset, textcoords="offset points",
            fontsize=9, arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.8),
        )
    ax.scatter(list(points), births[list(points)], color=RED, zorder=3, s=30)

    ax.set_title(f"대한민국 연도별 출생아수 ({start}~{end})", fontsize=14, pad=10)
    ax.set_xlabel("연도")
    ax.set_ylabel("출생아수 (명)")
    ax.set_xlim(years.min() - 1, years.max() + 1)
    ax.set_ylim(0, births.max() * 1.15)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=12))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v / 10_000:,.0f}만"))
    ax.grid(alpha=0.3)
    ax.text(0.99, 0.01, "출처: 국가데이터처 「인구동향조사」",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color=GRAY)


def plot_tfr(ax, df):
    ax.plot(df.index, df["합계출산율"], marker="o", ms=3, color=BLUE)
    for level, label, ls in [(2.1, "인구대체수준 2.1", "--"), (1.3, "초저출산 1.3", ":")]:
        ax.axhline(level, ls=ls, color=GRAY, lw=1)
        ax.text(df.index[-1], level + 0.05, label, color=GRAY, ha="right")
    ax.set(title="합계출산율 추이", xlabel="연도", ylabel="명")
    ax.grid(alpha=0.3)


def plot_birth_death(ax, df):
    births, deaths = df["출생아수"] / 10_000, df["사망자수(추정)"] / 10_000
    ax.plot(df.index, births, label="출생아수", color=BLUE)
    ax.plot(df.index, deaths, label="사망자수(추정)", color=RED)
    ax.fill_between(df.index, births.astype(float), deaths.astype(float), alpha=0.1)
    ax.set(title="출생아수 vs 사망자수(추정)", xlabel="연도", ylabel="만 명")
    ax.legend()
    ax.grid(alpha=0.3)


def plot_change(ax, df):
    chg = df["출생아수_증감률(%)"]
    ax.bar(df.index, chg, color=[RED if v < 0 else BLUE for v in chg.fillna(0)])
    ax.axhline(0, color="black", lw=0.8)
    ax.set(title="출생아수 전년 대비 증감률", xlabel="연도", ylabel="%")
    ax.grid(axis="y", alpha=0.3)


def plot_decade(ax, decade):
    values = decade["출생아수_평균"] / 10_000
    bars = ax.bar(decade.index, values, color=BLUE)
    ax.bar_label(bars, labels=[f"{v:.1f}만" for v in values], padding=3)
    ax2 = ax.twinx()
    ax2.plot(decade.index, decade["합계출산율_평균"], color=RED, marker="o")
    ax2.set_ylabel("합계출산율 평균 (명)", color=RED)
    ax2.set_ylim(0, decade["합계출산율_평균"].max() * 1.2)
    ax.set(title="연대별 평균 출생아수와 합계출산율", ylabel="출생아수 평균 (만 명)")
    ax.set_ylim(0, values.max() * 1.15)


def plot_corr(ax, corr):
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr)), corr.columns, rotation=30, ha="right")
    ax.set_yticks(range(len(corr)), corr.index)
    for i in range(len(corr)):
        for j in range(len(corr)):
            v = corr.iat[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", color="white" if abs(v) > 0.6 else "black")
    ax.figure.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title("지표 간 상관관계 (피어슨)")


# ──────────────────────────────────────────────
# 콘솔 실행
# ──────────────────────────────────────────────
def main():
    import matplotlib.pyplot as plt

    setup_korean_font()
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_XLSX
    OUT_DIR.mkdir(exist_ok=True)

    df, log = load_and_clean(path)
    r = analyze(df)
    df.to_csv(OUT_DIR / "출생통계_정제.csv", encoding="utf-8-sig")
    r["decade"].to_csv(OUT_DIR / "연대별_평균.csv", encoding="utf-8-sig")
    r["corr"].to_csv(OUT_DIR / "상관관계.csv", encoding="utf-8-sig")

    sep = "\n" + "─" * 60
    print("[데이터 클렌징]", *log, sep="\n  - ")
    print(sep, "\n[요약]", *(f"{k}: {v}" for k, v in r["summary"].items()), sep="\n  ")
    print(sep, "\n[주요 이정표]", *(f"{k}: {v}" for k, v in r["milestones"].items()), sep="\n  ")
    for title, table in [("기술통계", r["describe"]), ("연대별 평균", r["decade"]),
                         ("최고·최저 기록", r["extremes"]), ("상관관계", r["corr"])]:
        print(sep, f"\n[{title}]\n{table.to_string()}")

    charts = {
        "출생아수_라인그래프_1970_2025.png": lambda ax: plot_births(ax, df),
        "합계출산율_추이.png": lambda ax: plot_tfr(ax, df),
        "출생_사망_비교.png": lambda ax: plot_birth_death(ax, df),
        "출생아수_증감률.png": lambda ax: plot_change(ax, df),
        "연대별_평균.png": lambda ax: plot_decade(ax, r["decade"]),
        "상관관계.png": lambda ax: plot_corr(ax, r["corr"]),
    }
    for name, draw in charts.items():
        fig, ax = plt.subplots(figsize=(12, 5.5))
        draw(ax)
        fig.tight_layout()
        fig.savefig(OUT_DIR / name, dpi=150)
        plt.close(fig)
    print(f"\n결과 저장 위치: {OUT_DIR}")


if __name__ == "__main__":
    main()
