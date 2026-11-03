"""
네이버 뉴스 크롤러 GUI (PyQt6)

크롤링 로직은 naver_news_crawler.py의 함수를 그대로 사용합니다.

사용법:
    python naver_news_gui.py

필요 패키지:
    pip install requests beautifulsoup4 PyQt6 openpyxl
"""

import csv
import os
import sys
import time
import webbrowser
from urllib.parse import parse_qs, urlparse

import requests
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from naver_news_crawler import SEARCH_URL, collect_article_links, parse_article

COLUMNS = [("title", "제목"), ("press", "언론사"), ("date", "날짜"), ("reporter", "기자")]

# 엑셀 저장용 컬럼: (키, 헤더, 열 너비)
EXCEL_COLUMNS = [
    ("title", "제목", 50),
    ("press", "언론사", 14),
    ("date", "날짜", 20),
    ("reporter", "기자", 14),
    ("url", "URL", 45),
    ("content", "본문", 100),
]
EXCEL_CELL_LIMIT = 32767  # 엑셀 셀 하나에 들어갈 수 있는 최대 글자 수

ACCENT = "#03C75A"  # 네이버 그린


def resource_path(relative):
    """PyInstaller로 만든 exe에서는 리소스가 임시 폴더(sys._MEIPASS)에 풀립니다."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)

EMPTY_DETAIL_HTML = (
    "<div style='color:#6b7599; text-align:center; margin-top:80px; font-size:15px;'>"
    "<p style='font-size:42px;'>🗞️</p>"
    "<p>왼쪽 목록에서 기사를 선택하면<br>본문이 여기에 표시됩니다</p></div>"
)

# 다크 테마 + 그라데이션 스타일시트
STYLE = """
QWidget#root {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0b1020, stop:1 #151b34);
}
QWidget { color: #e6e9f5; }

QFrame#banner {
    border-radius: 18px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #03C75A, stop:0.5 #00a3c4, stop:1 #6c5ce7);
}
QLabel#bannerTitle {
    color: white; font-size: 24px; font-weight: 800; letter-spacing: 2px; background: transparent;
}
QLabel#bannerSubtitle {
    color: rgba(255, 255, 255, 0.85); font-size: 13px; background: transparent;
}
QLabel#countBadge {
    background: rgba(255, 255, 255, 0.22); color: white;
    border: 1px solid rgba(255, 255, 255, 0.45); border-radius: 22px;
    padding: 8px 22px; font-size: 18px; font-weight: 800; min-width: 70px;
}

QFrame#card {
    background: #1a2140; border: 1px solid #2a3360; border-radius: 16px;
}
QLabel#sectionTitle {
    color: #b9c2e8; font-size: 14px; font-weight: 700; padding: 2px 2px 8px 2px; background: transparent;
}
QLabel#status { color: #9aa4c7; font-size: 12px; background: transparent; }

QLineEdit, QSpinBox, QComboBox {
    background: #0f1530; border: 2px solid #2c3561; border-radius: 10px;
    padding: 8px 12px; font-size: 14px; color: #ffffff;
    selection-background-color: #03C75A;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 2px solid #03C75A; }
QComboBox::drop-down { border: none; width: 24px; }
QSpinBox { padding-right: 26px; }
QSpinBox::up-button, QSpinBox::down-button {
    background: #222b55; border: none; width: 22px; subcontrol-origin: border;
}
QSpinBox::up-button { subcontrol-position: top right; border-top-right-radius: 8px; }
QSpinBox::down-button { subcontrol-position: bottom right; border-bottom-right-radius: 8px; }
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #03C75A; }
QSpinBox::up-arrow {
    width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-bottom: 5px solid #e6e9f5;
}
QSpinBox::down-arrow {
    width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 5px solid #e6e9f5;
}
QComboBox QAbstractItemView {
    background: #1a2140; border: 1px solid #2c3561; selection-background-color: #03C75A;
}

QPushButton {
    border: none; border-radius: 10px; padding: 10px 18px;
    font-size: 14px; font-weight: 700; color: white;
}
QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #03C75A, stop:1 #00b4d8);
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1fe07a, stop:1 #2ccdf0);
}
QPushButton#danger {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff5f6d, stop:1 #ff9a5a);
}
QPushButton#danger:hover { background: #ff7a85; }
QPushButton#secondary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6c5ce7, stop:1 #a66cff);
}
QPushButton#secondary:hover { background: #8a7bff; }
QPushButton#excel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d6f42, stop:1 #21a366);
}
QPushButton#excel:hover { background: #27b874; }
QPushButton:pressed { padding-top: 12px; padding-bottom: 8px; }
QPushButton#primary:disabled, QPushButton#danger:disabled,
QPushButton#secondary:disabled, QPushButton#excel:disabled {
    background: #262d4d; color: #5d6688;
}

QTableWidget {
    background: #141a35; alternate-background-color: #182042;
    border: none; border-radius: 10px; font-size: 13px;
    selection-background-color: transparent;
}
QTableWidget::item { padding: 6px 8px; border-bottom: 1px solid #1f2850; }
QTableWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #03C75A, stop:1 #00a3c4);
    color: white;
}
QTableWidget::item:hover { background: #222c58; }
QHeaderView::section {
    background: #222b55; color: #b9c2e8; border: none;
    padding: 10px 8px; font-weight: 700; font-size: 13px;
}
QHeaderView::section:first { border-top-left-radius: 10px; }
QHeaderView::section:last { border-top-right-radius: 10px; }
QTableCornerButton::section { background: #222b55; border: none; }

QTextBrowser {
    background: #141a35; border: none; border-radius: 10px; padding: 14px; font-size: 14px;
}

QProgressBar { background: #1f2748; border: none; border-radius: 4px; }
QProgressBar::chunk {
    border-radius: 4px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #03C75A, stop:0.5 #00b4d8, stop:1 #a66cff);
}

QSplitter::handle { background: transparent; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #34407a; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #03C75A; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #34407a; border-radius: 4px; min-width: 30px; }

QMessageBox { background: #1a2140; }
"""


class CrawlWorker(QThread):
    """크롤링은 시간이 걸리므로 화면이 멈추지 않도록 별도 스레드에서 실행합니다."""

    links_found = pyqtSignal(int)
    article_ready = pyqtSignal(dict)
    progress = pyqtSignal(int)
    failed = pyqtSignal(str)
    finished_ok = pyqtSignal(int)

    def __init__(self, query, pages, sort):
        super().__init__()
        self.query = query
        self.pages = pages
        self.sort = sort
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            links = collect_article_links(self.query, self.pages, self.sort)
        except requests.RequestException as e:
            self.failed.emit(f"검색 실패: {e}")
            return

        self.links_found.emit(len(links))
        count = 0
        for i, link in enumerate(links, 1):
            if self._stop:
                break
            try:
                self.article_ready.emit(parse_article(link))
                count += 1
            except requests.RequestException:
                pass  # 실패한 기사는 건너뜁니다
            self.progress.emit(i)
            time.sleep(0.5)  # 서버 부담을 줄이기 위한 대기
        self.finished_ok.emit(count)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("네이버 뉴스 크롤러")
        self.resize(1280, 820)
        self.articles = []
        self.worker = None

        # 맨 위: 그라데이션 배너
        title = QLabel("📰  NAVER NEWS CRAWLER")
        title.setObjectName("bannerTitle")
        subtitle = QLabel("키워드로 네이버 뉴스를 검색하고 기사 본문까지 한 번에 수집합니다")
        subtitle.setObjectName("bannerSubtitle")
        self.count_badge = QLabel("0 건")
        self.count_badge.setObjectName("countBadge")
        self.count_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        banner_text = QVBoxLayout()
        banner_text.setSpacing(2)
        banner_text.addWidget(title)
        banner_text.addWidget(subtitle)
        banner_layout = QHBoxLayout()
        banner_layout.setContentsMargins(28, 18, 28, 18)
        banner_layout.addLayout(banner_text, 1)
        banner_layout.addWidget(self.count_badge)
        banner = QFrame()
        banner.setObjectName("banner")
        banner.setLayout(banner_layout)

        # 상단: 검색 조건
        self.query_edit = QLineEdit(parse_qs(urlparse(SEARCH_URL).query)["query"][0])
        self.query_edit.setPlaceholderText("🔍  검색어를 입력하세요")
        self.query_edit.returnPressed.connect(self.start_crawl)

        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(1, 20)
        self.pages_spin.setSuffix(" 페이지")

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("관련도순", "0")
        self.sort_combo.addItem("최신순", "1")

        self.search_btn = QPushButton("🚀  크롤링 시작")
        self.search_btn.setObjectName("primary")
        self.search_btn.clicked.connect(self.start_crawl)
        self.stop_btn = QPushButton("⏹  중지")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_crawl)
        self.save_btn = QPushButton("📄  CSV 저장")
        self.save_btn.setObjectName("secondary")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_csv)
        self.excel_btn = QPushButton("📊  엑셀 저장")
        self.excel_btn.setObjectName("excel")
        self.excel_btn.setEnabled(False)
        self.excel_btn.clicked.connect(self.save_excel)
        for btn in (self.search_btn, self.stop_btn, self.save_btn, self.excel_btn):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        top = QHBoxLayout()
        top.setContentsMargins(18, 14, 18, 14)
        top.setSpacing(10)
        top.addWidget(self.query_edit, 1)
        top.addWidget(self.pages_spin)
        top.addWidget(self.sort_combo)
        top.addWidget(self.search_btn)
        top.addWidget(self.stop_btn)
        top.addSpacing(8)
        top.addWidget(self.save_btn)
        top.addWidget(self.excel_btn)
        search_card = self.make_card(top)

        # 가운데: 기사 목록 + 본문
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels([label for _, label in COLUMNS])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(COLUMNS)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.show_article)
        self.table.cellDoubleClicked.connect(self.open_in_browser)

        self.detail = QTextBrowser()
        self.detail.setOpenExternalLinks(True)
        self.detail.setHtml(EMPTY_DETAIL_HTML)

        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(14, 12, 14, 14)
        list_layout.addWidget(self.section_label("🗂  기사 목록"))
        list_layout.addWidget(self.table)
        detail_layout = QVBoxLayout()
        detail_layout.setContentsMargins(14, 12, 14, 14)
        detail_layout.addWidget(self.section_label("📖  기사 본문"))
        detail_layout.addWidget(self.detail)

        # 가로 배치: 왼쪽 목록, 오른쪽 본문
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.make_card(list_layout))
        splitter.addWidget(self.make_card(detail_layout))
        splitter.setSizes([640, 520])
        splitter.setHandleWidth(14)

        # 하단: 진행 상황
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.status_label = QLabel("✨  검색어를 입력하고 '크롤링 시작'을 누르세요. 기사를 더블클릭하면 브라우저로 열립니다.")
        self.status_label.setObjectName("status")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(14)
        layout.addWidget(banner)
        layout.addWidget(search_card)
        layout.addWidget(splitter, 1)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)

        central = QWidget()
        central.setObjectName("root")
        central.setLayout(layout)
        self.setCentralWidget(central)

    def make_card(self, layout):
        """둥근 모서리 + 그림자가 있는 카드 패널을 만듭니다."""
        card = QFrame()
        card.setObjectName("card")
        card.setLayout(layout)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 110))
        card.setGraphicsEffect(shadow)
        return card

    def section_label(self, text):
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    def start_crawl(self):
        query = self.query_edit.text().strip()
        if not query or (self.worker and self.worker.isRunning()):
            return

        self.articles.clear()
        self.table.setRowCount(0)
        self.detail.setHtml(EMPTY_DETAIL_HTML)
        self.count_badge.setText("0 건")
        self.progress_bar.setValue(0)
        self.set_running(True)
        self.status_label.setText(f"🔎  '{query}' 검색 중...")

        self.worker = CrawlWorker(query, self.pages_spin.value(), self.sort_combo.currentData())
        self.worker.links_found.connect(self.on_links_found)
        self.worker.article_ready.connect(self.add_article)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished_ok.connect(self.on_finished)
        self.worker.start()

    def stop_crawl(self):
        if self.worker:
            self.worker.stop()
            self.status_label.setText("⏳  중지하는 중...")

    def set_running(self, running):
        self.search_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.save_btn.setEnabled(not running and bool(self.articles))
        self.excel_btn.setEnabled(not running and bool(self.articles))

    def on_links_found(self, total):
        self.progress_bar.setMaximum(max(total, 1))
        self.status_label.setText(f"📥  기사 {total}건 발견, 본문 수집 중...")

    def add_article(self, article):
        self.articles.append(article)
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, (key, _) in enumerate(COLUMNS):
            item = QTableWidgetItem(article[key])
            if key == "press":
                item.setForeground(QColor(ACCENT))
            self.table.setItem(row, col, item)
        self.count_badge.setText(f"{len(self.articles)} 건")

    def on_failed(self, message):
        self.set_running(False)
        self.status_label.setText(f"⚠️  {message}")
        QMessageBox.warning(self, "오류", message)

    def on_finished(self, count):
        self.set_running(False)
        self.status_label.setText(f"✅  완료: {count}건 수집")

    def show_article(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        a = self.articles[rows[0].row()]
        escaped = a["content"].replace("&", "&amp;").replace("<", "&lt;")
        body = "".join(f"<p style='margin:0 0 12px 0;'>{line}</p>" for line in escaped.split("\n"))
        self.detail.setHtml(
            f"<div style='font-size:19px; font-weight:700; color:#ffffff;'>{a['title']}</div>"
            f"<p style='margin-top:10px;'>"
            f"<span style='background:{ACCENT}; color:#0b1020; font-weight:700;'>&nbsp;{a['press']}&nbsp;</span>"
            f"&nbsp;&nbsp;<span style='color:#9aa4c7;'>🕒 {a['date']}&nbsp;&nbsp;✍️ {a['reporter']}</span></p>"
            f"<p><a style='color:#8ab4ff;' href='{a['url']}'>🔗 원문 보기</a></p>"
            f"<hr style='background:#2c3557;'>"
            f"<div style='color:#d5dbf0; line-height:160%;'>{body}</div>"
        )

    def open_in_browser(self, row, _col):
        webbrowser.open(self.articles[row]["url"])

    def save_csv(self):
        default = f"naver_news_{self.query_edit.text().strip()}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "CSV 저장", default, "CSV 파일 (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["title", "press", "date", "reporter", "url", "content"])
            writer.writeheader()
            writer.writerows(self.articles)
        self.status_label.setText(f"💾  저장 완료: {path} ({len(self.articles)}건)")

    def save_excel(self):
        default = f"naver_news_{self.query_edit.text().strip()}.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "엑셀 저장", default, "엑셀 파일 (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        wb = Workbook()
        ws = wb.active
        ws.title = "뉴스"

        # 헤더: 굵은 글씨 + 배경색, 첫 행 고정
        ws.append([header for _, header, _ in EXCEL_COLUMNS])
        for col, (_, _, width) in enumerate(EXCEL_COLUMNS, 1):
            cell = ws.cell(row=1, column=col)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="03C75A")
            cell.alignment = Alignment(horizontal="center")
            ws.column_dimensions[cell.column_letter].width = width
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

        url_col = [key for key, _, _ in EXCEL_COLUMNS].index("url") + 1
        for a in self.articles:
            ws.append([a[key][:EXCEL_CELL_LIMIT] for key, _, _ in EXCEL_COLUMNS])
            row = ws.max_row
            link = ws.cell(row=row, column=url_col)
            link.hyperlink = a["url"]
            link.font = Font(color="0563C1", underline="single")
            for cell in ws[row]:
                cell.alignment = Alignment(vertical="top", wrap_text=cell.column == len(EXCEL_COLUMNS))
            ws.row_dimensions[row].height = 60

        try:
            wb.save(path)
        except PermissionError:
            QMessageBox.warning(self, "오류", "파일을 저장할 수 없습니다. 엑셀에서 열려 있다면 닫고 다시 시도하세요.")
            return
        self.status_label.setText(f"💾  저장 완료: {path} ({len(self.articles)}건)")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Malgun Gothic", 10))
    app.setStyleSheet(STYLE)
    app.setWindowIcon(QIcon(resource_path("assets/app.ico")))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
