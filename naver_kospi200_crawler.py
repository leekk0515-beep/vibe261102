"""
네이버 증권(https://stock.naver.com/market/stock/kr)의 코스피200 데이터를 수집하는 스크립트

이 페이지는 Next.js로 만들어져 있어서 처음 받은 HTML에는 코스피200 숫자가 없고,
브라우저가 아래 JSON API를 호출해서 화면을 채웁니다.
그래서 BeautifulSoup으로 HTML을 파싱해도 데이터가 나오지 않으므로,
페이지가 실제로 쓰는 JSON API를 직접 호출합니다.

수집 항목:
    1. 코스피200 지수 현재 시세 (현재가, 전일비, 등락률, 시가/고가/저가, 거래량/대금)
    2. 코스피200 일별 시세 (최근 N일)
    3. 코스피200 구성 종목 전체 (약 200개, 시가총액 순)

사용법:
    python naver_kospi200_crawler.py          # 일별 시세 20일
    python naver_kospi200_crawler.py 60       # 일별 시세 60일

필요 패키지:
    pip install requests
"""

import csv
import sys
import time

import requests

API_BASE = "https://m.stock.naver.com/api/index/KPI200"
POLLING_URL = "https://polling.finance.naver.com/api/realtime/domestic/index/KPI200"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Referer": "https://stock.naver.com/market/stock/kr",
}

# 구성 종목 API는 pageSize가 너무 크면 400 에러를 돌려줍니다. (60까지 확인, 100은 400)
PAGE_SIZE = 50
KOSPI200_COUNT = 200


def get_json(url, params=None):
    res = requests.get(url, params=params, headers=HEADERS, timeout=10)
    res.raise_for_status()
    return res.json()


def fetch_index_summary():
    """코스피200 지수 현재 시세"""
    data = get_json(POLLING_URL)["datas"][0]
    return {
        "지수명": data["stockName"],
        "현재가": data["closePrice"],
        "전일비": data["compareToPreviousClosePrice"],
        "등락률(%)": data["fluctuationsRatio"],
        "시가": data["openPrice"],
        "고가": data["highPrice"],
        "저가": data["lowPrice"],
        "거래량": data["accumulatedTradingVolume"],
        "거래대금": data["accumulatedTradingValue"],
        "장상태": data["marketStatus"],
        "기준시각": data["localTradedAt"],
    }


def fetch_daily_prices(days=20):
    """코스피200 일별 시세 (최신순)"""
    rows = []
    page = 1
    while len(rows) < days:
        items = get_json(f"{API_BASE}/price", {"page": page, "pageSize": PAGE_SIZE})
        if not items:
            break
        for it in items:
            rows.append({
                "날짜": it["localTradedAt"],
                "종가": it["closePrice"],
                "전일비": it["compareToPreviousClosePrice"],
                "등락률(%)": it["fluctuationsRatio"],
                "시가": it["openPrice"],
                "고가": it["highPrice"],
                "저가": it["lowPrice"],
            })
        page += 1
        time.sleep(0.3)
    return rows[:days]


def print_page(page, count):
    print(f"  {page}페이지: {count}건")


def fetch_constituents(max_items=KOSPI200_COUNT, on_page=print_page):
    """코스피200 구성 종목을 페이지 단위로 넘기며 max_items개까지 수집 (시가총액 순)

    on_page(page, count)는 페이지를 하나 받을 때마다 호출됩니다. (GUI 진행 표시용)
    """
    rows = []
    seen = set()
    page = 1
    while len(rows) < max_items:
        items = get_json(f"{API_BASE}/enrollStocks", {"page": page, "pageSize": PAGE_SIZE})
        on_page(page, len(items))
        if not items:
            break
        for it in items:
            # 페이지 경계에서 순위가 바뀌어 같은 종목이 두 번 나오는 경우 제외
            if it["itemCode"] in seen:
                continue
            seen.add(it["itemCode"])
            rows.append({
                "순위": len(rows) + 1,
                "종목코드": it["itemCode"],
                "종목명": it["stockName"],
                "현재가": it["closePrice"],
                "전일비": it["compareToPreviousClosePrice"],
                "등락률(%)": it["fluctuationsRatio"],
                "거래량": it["accumulatedTradingVolume"],
                "거래대금(백만)": it["accumulatedTradingValue"],
                "시가총액(억)": it["marketValue"],
            })
        if len(items) < PAGE_SIZE:
            break
        page += 1
        time.sleep(0.3)
    # 정기 변경 시기에는 편입 예정 종목까지 200개를 넘게 내려주는 경우가 있음
    return rows[:max_items]


def save_csv(path, rows):
    if not rows:
        return
    # utf-8-sig: 엑셀에서 열어도 한글이 깨지지 않도록
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"저장 완료: {path} ({len(rows)}건)")


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 20

    summary = fetch_index_summary()
    print("=== 코스피200 현재 시세 ===")
    for key, value in summary.items():
        print(f"{key:>8}: {value}")
    print()

    daily = fetch_daily_prices(days)
    print(f"=== 일별 시세 (최근 {len(daily)}일) ===")
    for row in daily[:5]:
        print(f"{row['날짜']}  종가 {row['종가']:>9}  {row['등락률(%)']:>6}%")
    print()

    print(f"=== 구성 종목 수집 (페이지당 {PAGE_SIZE}건) ===")
    stocks = fetch_constituents()
    print(f"=== 구성 종목 ({len(stocks)}개) 상위 10 ===")
    for row in stocks[:10]:
        print(f"{row['순위']:>3}. {row['종목명']:<12} {row['현재가']:>10}원  "
              f"{row['등락률(%)']:>6}%  시총 {row['시가총액(억)']}억")
    print()

    save_csv("kospi200_daily.csv", daily)
    save_csv("kospi200_stocks.csv", stocks)


if __name__ == "__main__":
    main()
