"""
네이버 검색 결과에서 뉴스 기사를 찾아 본문까지 크롤링하는 스크립트

사용법:
    python naver_news_crawler.py                 # 기본 검색어(반도체)
    python naver_news_crawler.py "검색어" 3       # 검색어, 수집할 페이지 수

필요 패키지:
    pip install requests beautifulsoup4
"""

import csv
import re
import sys
import time
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

# 요청하신 URL (통합검색). 여기서 검색어(query)를 뽑아서 사용합니다.
SEARCH_URL = (
    "https://search.naver.com/search.naver?where=nexearch&sm=top_hty&fbm=0"
    "&ie=utf8&query=%EB%B0%98%EB%8F%84%EC%B2%B4&ackey=2r4qz48r"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Referer": "https://www.naver.com/",
}

# 네이버 뉴스(본문이 네이버에 있는 기사) 주소 패턴
ARTICLE_PATTERN = re.compile(r"^https://n\.news\.naver\.com/mnews/article/\d+/\d+")


def get_soup(url, params=None):
    res = requests.get(url, params=params, headers=HEADERS, timeout=10)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")


def collect_article_links(query, pages=1, sort="0"):
    """뉴스 탭 검색 결과에서 네이버뉴스 기사 링크를 모읍니다."""
    links = []
    for page in range(pages):
        params = {
            "where": "news",
            "query": query,
            "sort": sort,         # 0: 관련도순, 1: 최신순
            "start": page * 10 + 1,
        }
        soup = get_soup("https://search.naver.com/search.naver", params)

        # 검색결과의 클래스명은 자주 바뀌므로 href 패턴으로 기사 링크를 찾습니다.
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ARTICLE_PATTERN.match(href) and href not in links:
                links.append(href)
        time.sleep(0.5)
    return links


def text_of(soup, selector, attr=None):
    tag = soup.select_one(selector)
    if tag is None:
        return ""
    if attr:
        return tag.get(attr, "")
    return tag.get_text(" ", strip=True)


def parse_article(url):
    """네이버뉴스 기사 페이지에서 제목/언론사/날짜/기자/본문을 추출합니다."""
    soup = get_soup(url)

    body = soup.select_one("#dic_area") or soup.select_one("#newsct_article")
    if body:
        # 사진 설명, 기자 이메일 박스 등 본문이 아닌 요소 제거
        for tag in body.select("span.end_photo_org, em.img_desc, div.vod_player_wrap, script, style"):
            tag.decompose()
        content = body.get_text("\n", strip=True)
    else:
        content = ""

    return {
        "title": text_of(soup, "#title_area") or text_of(soup, "h2.media_end_head_headline"),
        "press": text_of(soup, ".media_end_head_top_logo img", "alt"),
        "date": text_of(soup, "span.media_end_head_info_datestamp_time", "data-date-time"),
        "reporter": text_of(soup, "em.media_end_head_journalist_name"),
        "url": url,
        "content": content,
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows 콘솔 한글 깨짐 방지

    query = parse_qs(urlparse(SEARCH_URL).query)["query"][0]
    if len(sys.argv) > 1:
        query = sys.argv[1]
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    print(f"검색어: {query} / 페이지 수: {pages}")
    links = collect_article_links(query, pages)
    print(f"기사 {len(links)}건 발견\n")

    articles = []
    for i, link in enumerate(links, 1):
        try:
            article = parse_article(link)
        except requests.RequestException as e:
            print(f"[{i}] 실패: {link} ({e})")
            continue
        articles.append(article)
        print(f"[{i}] {article['title']}")
        print(f"    {article['press']} | {article['date']} | {article['reporter']}")
        print(f"    {article['content'][:100]}...\n")
        time.sleep(0.5)  # 서버 부담을 줄이기 위한 대기

    filename = f"naver_news_{query}.csv"
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "press", "date", "reporter", "url", "content"])
        writer.writeheader()
        writer.writerows(articles)
    print(f"저장 완료: {filename} ({len(articles)}건)")


if __name__ == "__main__":
    main()
