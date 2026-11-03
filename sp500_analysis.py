"""S&P 500 과거 데이터 클랜징 및 Pandas 다각도 분석 로직.

GUI(sp500_gui.py)에서 함수를 가져다 쓰며, 단독 실행 시 콘솔에 결과를 출력합니다.
실행: python sp500_analysis.py [CSV 경로]
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_CSV = Path("S&P 500 과거 데이터.csv")
WEEKDAYS = ["월", "화", "수", "목", "금"]


# ------------------------------------------------------------
# 1. 데이터 클랜징
# ------------------------------------------------------------
def load_and_clean(path):
    """CSV를 읽어 정제된 DataFrame(날짜 인덱스)과 정제 로그를 반환"""
    log = []
    raw = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    log.append(f"원본 행/열: {raw.shape[0]:,}행 × {raw.shape[1]}열")
    na = raw.isna().sum()
    log.append("원본 결측치: " + ", ".join(f"{c} {n}" for c, n in na.items() if n) if na.any() else "원본 결측치: 없음")

    df = raw.rename(columns={
        "날짜": "Date", "종가": "Close", "시가": "Open", "고가": "High",
        "저가": "Low", "거래량": "Volume", "변동 %": "ChangePct",
    })

    # 날짜: "2019- 11- 14" 처럼 공백이 섞여 있음 → 공백 제거 후 변환
    df["Date"] = pd.to_datetime(df["Date"].str.replace(" ", ""), format="%Y-%m-%d", errors="coerce")
    log.append("날짜 문자열의 공백 제거 후 datetime 변환")

    # 가격: 천 단위 콤마 제거 후 숫자 변환
    for col in ["Close", "Open", "High", "Low"]:
        df[col] = pd.to_numeric(df[col].str.replace(",", ""), errors="coerce")
    log.append("가격(종가/시가/고가/저가)의 천 단위 콤마 제거 후 숫자 변환")

    # 변동 %: "%" 제거 후 숫자 변환
    df["ChangePct"] = pd.to_numeric(df["ChangePct"].str.replace("%", ""), errors="coerce")
    log.append("변동 %의 '%' 기호 제거 후 숫자 변환")

    # 거래량: 값이 전부 비어 있으면 분석에 쓸 수 없으므로 제거
    if "Volume" in df and df["Volume"].isna().all():
        df = df.drop(columns="Volume")
        log.append("거래량 컬럼이 전부 비어 있어 제거")

    before = len(df)
    df = df.dropna(subset=["Date", "Close"]).drop_duplicates(subset="Date")
    log.append(f"날짜/종가 결측 및 중복 제거: {before - len(df)}행 삭제")

    # 가격 논리 검증: 고가 >= max(시가, 종가), 저가 <= min(시가, 종가)
    bad = (df["High"] < df[["Open", "Close"]].max(axis=1)) | (df["Low"] > df[["Open", "Close"]].min(axis=1))
    if bad.any():
        dates = ", ".join(f"{d:%Y-%m-%d}" for d in df.loc[bad, "Date"].head(5))
        # 원본 오류로 보고 고가/저가를 시가·종가 범위에 맞게 보정
        df["High"] = df[["High", "Open", "Close"]].max(axis=1)
        df["Low"] = df[["Low", "Open", "Close"]].min(axis=1)
        log.append(f"고가/저가가 시가·종가 범위를 벗어난 {bad.sum()}행 보정 ({dates})")
    else:
        log.append("고가/저가 범위 검증: 이상 없음")

    # 최신순 → 날짜 오름차순으로 정렬하고 인덱스로 지정
    df = df.sort_values("Date").set_index("Date")

    # 변동 %를 종가로 재계산해 원본 값과 비교
    diff = (df["Close"].pct_change() * 100 - df["ChangePct"]).abs()
    log.append(f"변동 % 재계산 검증: 0.05%p 이상 차이 {(diff > 0.05).sum()}행")

    log.append(f"정제 후: {len(df):,}행, 기간 {df.index.min():%Y-%m-%d} ~ {df.index.max():%Y-%m-%d}")
    return df, log


# ------------------------------------------------------------
# 2. 다각도 분석
# ------------------------------------------------------------
def analyze(df):
    """분석 결과를 dict로 반환"""
    close = df["Close"]
    ret = close.pct_change().dropna()
    r = {"ret": ret}

    # 기간 전체 성과
    years = (close.index[-1] - close.index[0]).days / 365.25
    total = close.iloc[-1] / close.iloc[0] - 1
    r["summary"] = {
        "시작 종가": f"{close.iloc[0]:,.2f} ({close.index[0]:%Y-%m-%d})",
        "마지막 종가": f"{close.iloc[-1]:,.2f} ({close.index[-1]:%Y-%m-%d})",
        "누적 수익률": f"{total:.2%}",
        "연평균 수익률(CAGR)": f"{(1 + total) ** (1 / years) - 1:.2%}",
        "연환산 변동성": f"{ret.std() * np.sqrt(252):.2%}",
        "최고 종가": f"{close.max():,.2f} ({close.idxmax():%Y-%m-%d})",
        "최저 종가": f"{close.min():,.2f} ({close.idxmin():%Y-%m-%d})",
        "일간 수익률 왜도 / 첨도": f"{ret.skew():.3f} / {ret.kurt():.3f}",
    }

    # 기초 통계량
    r["describe"] = df[["Open", "High", "Low", "Close", "ChangePct"]].describe().round(2)

    # 연도별
    year_end = close.resample("YE").last()
    yearly = pd.DataFrame({
        "연말종가": year_end,
        "수익률(%)": year_end.pct_change() * 100,
        "변동성(%)": ret.resample("YE").std() * np.sqrt(252) * 100,
        "최고": df["High"].resample("YE").max(),
        "최저": df["Low"].resample("YE").min(),
    })
    # 첫 해 수익률은 첫 거래일 종가 기준으로 계산
    yearly.iloc[0, 1] = (yearly.iloc[0, 0] / close.iloc[0] - 1) * 100
    yearly.index = yearly.index.year
    yearly.index.name = "연도"
    r["yearly"] = yearly.round(2)
    r["summary"]["상승 / 하락 연도"] = f"{(yearly['수익률(%)'] > 0).sum()}년 / {(yearly['수익률(%)'] <= 0).sum()}년"

    # 월별 계절성
    monthly = close.resample("ME").last().pct_change().dropna() * 100
    season = monthly.groupby(monthly.index.month).agg(["mean", "median", lambda s: (s > 0).mean() * 100])
    season.columns = ["평균(%)", "중앙값(%)", "상승확률(%)"]
    season.index = [f"{m}월" for m in season.index]
    r["season"] = season.round(2)

    # 요일별
    weekday = ret.groupby(ret.index.dayofweek).agg(["mean", "count"])
    weekday.index = [WEEKDAYS[i] for i in weekday.index]
    weekday["mean"] *= 100
    weekday.columns = ["평균(%)", "거래일수"]
    r["weekday"] = weekday.round(4)

    # 일간 변동 극단값
    r["top"] = (ret.nlargest(10) * 100).round(2)
    r["bottom"] = (ret.nsmallest(10) * 100).round(2)

    # 최대 낙폭 (MDD)
    drawdown = close / close.cummax() - 1
    trough = drawdown.idxmin()
    peak_date = close[:trough].idxmax()
    recovered = close[trough:][close[trough:] >= close[peak_date]]
    r["drawdown"] = drawdown
    r["summary"]["최대 낙폭(MDD)"] = f"{drawdown.min():.2%}"
    r["summary"]["MDD 고점 → 저점"] = (
        f"{peak_date:%Y-%m-%d} ({close[peak_date]:,.2f}) → {trough:%Y-%m-%d} ({close[trough]:,.2f})"
    )
    r["summary"]["MDD 고점 회복일"] = f"{recovered.index[0]:%Y-%m-%d}" if len(recovered) else "기간 내 미회복"

    # 이동평균 골든/데드 크로스 (50일 vs 200일)
    ma50, ma200 = close.rolling(50).mean(), close.rolling(200).mean()
    # 200일선이 생기기 전 구간은 제외해야 첫날이 가짜 크로스로 잡히지 않음
    valid = ma200.notna()
    signal = (ma50[valid] > ma200[valid]).astype(int).diff()
    crosses = signal[signal != 0].dropna()
    r["ma50"], r["ma200"] = ma50, ma200
    r["crosses"] = crosses.map({1: "골든크로스", -1: "데드크로스"})
    r["summary"]["골든 / 데드 크로스"] = f"{(crosses == 1).sum()}회 / {(crosses == -1).sum()}회"
    return r


# ------------------------------------------------------------
# 3. 그래프 (matplotlib Axes에 그림 → GUI/콘솔 공용)
# ------------------------------------------------------------
def plot_close(ax, df, start="2000-01-01", end="2019-12-31"):
    """종가 기준 라인그래프 (기본: 2000년 1월 ~ 2019년 12월)"""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    data = df.loc[start:end, "Close"]
    ax.plot(data.index, data.values, color="#1f77b4", linewidth=1.2, label="S&P 500 종가")
    ax.set_title(f"S&P 500 종가 추이 ({start:%Y년 %m월} ~ {end:%Y년 %m월})", fontsize=14)
    ax.set_xlabel("날짜")
    ax.set_ylabel("종가 (포인트)")
    ax.set_xlim(start, end)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
    ax.grid(alpha=0.3)
    ax.legend()


def plot_moving_average(ax, df, r):
    ax.plot(df["Close"], label="종가", linewidth=0.8, color="gray")
    ax.plot(r["ma50"], label="50일 이동평균", linewidth=1.2)
    ax.plot(r["ma200"], label="200일 이동평균", linewidth=1.2)
    ax.set_title("종가와 이동평균선")
    ax.grid(alpha=0.3)
    ax.legend()


def plot_yearly(ax, r):
    yearly = r["yearly"]
    colors = ["#d62728" if v > 0 else "#1f77b4" for v in yearly["수익률(%)"]]
    ax.bar(yearly.index.astype(str), yearly["수익률(%)"], color=colors)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("연도별 수익률 (%)")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.3)


def plot_drawdown(ax, r):
    dd = r["drawdown"] * 100
    ax.fill_between(dd.index, dd, 0, color="#d62728", alpha=0.4)
    ax.set_title("고점 대비 낙폭 (Drawdown, %)")
    ax.grid(alpha=0.3)


def plot_return_hist(ax, r):
    ax.hist(r["ret"] * 100, bins=100, color="#1f77b4", alpha=0.8)
    ax.set_title("일간 수익률 분포 (%)")
    ax.grid(alpha=0.3)


def plot_volatility(ax, r):
    vol = r["ret"].rolling(60).std() * np.sqrt(252) * 100
    ax.plot(vol, color="#ff7f0e")
    ax.set_title("60일 롤링 변동성 (연환산, %)")
    ax.grid(alpha=0.3)


def plot_season(ax, r):
    season = r["season"]
    ax.bar(season.index, season["평균(%)"], color="#2ca02c")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("월별 평균 수익률 (%)")
    ax.grid(axis="y", alpha=0.3)


def setup_korean_font():
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"  # 한글 폰트 (Windows)
    plt.rcParams["axes.unicode_minus"] = False


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    setup_korean_font()
    pd.set_option("display.width", 120)
    df, log = load_and_clean(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV)
    print("\n".join(f"[정제] {line}" for line in log))
    r = analyze(df)
    for k, v in r["summary"].items():
        print(f"{k}: {v}")
    for key in ["describe", "yearly", "season", "weekday"]:
        print(f"\n{r[key]}")
    fig, ax = plt.subplots(figsize=(14, 6))
    plot_close(ax, df)
    fig.tight_layout()
    plt.show()
