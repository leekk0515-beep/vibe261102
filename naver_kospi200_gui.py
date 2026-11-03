"""
코스피200 크롤러 GUI (PyQt6)

수집 로직은 naver_kospi200_crawler.py의 함수를 그대로 사용합니다.

사용법:
    python naver_kospi200_gui.py

필요 패키지:
    pip install requests PyQt6
"""

import csv
import os
import sys
import webbrowser

import requests
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
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
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from naver_kospi200_crawler import (
    KOSPI200_COUNT,
    PAGE_SIZE,
    fetch_constituents,
    fetch_daily_prices,
    fetch_index_summary,
)

STOCK_COLUMNS = ["순위", "종목코드", "종목명", "현재가", "전일비", "등락률(%)",
                 "거래량", "거래대금(백만)", "시가총액(억)"]
DAILY_COLUMNS = ["날짜", "종가", "전일비", "등락률(%)", "시가", "고가", "저가"]
# 숫자로 정렬해야 하는 컬럼 (문자열 "219,250"은 그대로 정렬하면 순서가 틀어짐)
TEXT_COLUMNS = {"종목코드", "종목명", "날짜"}

STOCK_URL = "https://stock.naver.com/domestic/stock/{code}/price"
REFRESH_MS = 30_000  # 자동 새로고침 간격

# 한국 증시 관례: 상승 빨강, 하락 파랑
UP_COLOR = "#ff5f6d"
DOWN_COLOR = "#4d9fff"
FLAT_COLOR = "#b9c2e8"


def resource_path(relative):
    """PyInstaller로 만든 exe에서는 리소스가 임시 폴더(sys._MEIPASS)에 풀립니다."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def to_number(text):
    try:
        return float(str(text).replace(",", ""))
    except ValueError:
        return 0.0


def change_color(value):
    number = to_number(value)
    if number > 0:
        return UP_COLOR
    if number < 0:
        return DOWN_COLOR
    return FLAT_COLOR


# 다크 테마 스타일시트 (naver_news_gui.py와 같은 톤)
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
    color: white; font-size: 22px; font-weight: 800; letter-spacing: 2px; background: transparent;
}
QLabel#bannerSubtitle {
    color: rgba(255, 255, 255, 0.85); font-size: 12px; background: transparent;
}
QLabel#indexPrice {
    color: white; font-size: 34px; font-weight: 800; background: transparent;
}
QLabel#indexChange {
    background: rgba(11, 16, 32, 0.55); border-radius: 14px;
    padding: 6px 16px; font-size: 16px; font-weight: 800;
}

QFrame#card {
    background: #1a2140; border: 1px solid #2a3360; border-radius: 16px;
}
QLabel#statName { color: #9aa4c7; font-size: 12px; background: transparent; }
QLabel#statValue { color: #ffffff; font-size: 15px; font-weight: 700; background: transparent; }
QLabel#status { color: #9aa4c7; font-size: 12px; background: transparent; }

QLineEdit, QSpinBox {
    background: #0f1530; border: 2px solid #2c3561; border-radius: 10px;
    padding: 8px 12px; font-size: 14px; color: #ffffff;
    selection-background-color: #03C75A;
}
QLineEdit:focus, QSpinBox:focus { border: 2px solid #03C75A; }
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
QCheckBox { font-size: 13px; color: #b9c2e8; spacing: 6px; }

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
QPushButton#secondary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6c5ce7, stop:1 #a66cff);
}
QPushButton#secondary:hover { background: #8a7bff; }
QPushButton:pressed { padding-top: 12px; padding-bottom: 8px; }
QPushButton#primary:disabled, QPushButton#secondary:disabled {
    background: #262d4d; color: #5d6688;
}

QTabWidget::pane { border: none; }
QTabBar::tab {
    background: #1a2140; color: #9aa4c7; border: 1px solid #2a3360; border-bottom: none;
    border-top-left-radius: 10px; border-top-right-radius: 10px;
    padding: 9px 22px; margin-right: 4px; font-size: 13px; font-weight: 700;
}
QTabBar::tab:selected { background: #222b55; color: #ffffff; border-color: #03C75A; }

QTableWidget {
    background: #141a35; alternate-background-color: #182042;
    border: none; border-radius: 10px; font-size: 13px;
    selection-background-color: transparent;
}
QTableWidget::item { padding: 4px 8px; border-bottom: 1px solid #1f2850; }
QTableWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #03C75A, stop:1 #00a3c4);
    color: white;
}
QTableWidget::item:hover { background: #222c58; }
QHeaderView::section {
    background: #222b55; color: #b9c2e8; border: none;
    padding: 10px 8px; font-weight: 700; font-size: 13px;
}
QTableCornerButton::section { background: #222b55; border: none; }

QProgressBar { background: #1f2748; border: none; border-radius: 4px; }
QProgressBar::chunk {
    border-radius: 4px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #03C75A, stop:0.5 #00b4d8, stop:1 #a66cff);
}

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #34407a; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #03C75A; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #34407a; border-radius: 4px; min-width: 30px; }

QMessageBox { background: #1a2140; }
"""


class NumericItem(QTableWidgetItem):
    """'219,250' 같은 문자열을 숫자 기준으로 정렬하는 셀"""

    def __lt__(self, other):
        return to_number(self.text()) < to_number(other.text())


class FetchWorker(QThread):
    """네트워크 요청 동안 화면이 멈추지 않도록 별도 스레드에서 수집합니다."""

    summary_ready = pyqtSignal(dict)
    daily_ready = pyqtSignal(list)
    page_done = pyqtSignal(int, int)
    stocks_ready = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, days):
        super().__init__()
        self.days = days

    def run(self):
        try:
            self.summary_ready.emit(fetch_index_summary())
            self.daily_ready.emit(fetch_daily_prices(self.days))
            stocks = fetch_constituents(on_page=lambda page, count: self.page_done.emit(page, count))
            self.stocks_ready.emit(stocks)
        except (requests.RequestException, KeyError, ValueError) as e:
            self.failed.emit(f"데이터를 가져오지 못했습니다: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("코스피200 크롤러")
        self.resize(1280, 840)
        self.stocks = []
        self.daily = []
        self.worker = None

        # 맨 위: 배너 + 지수 현재가
        title = QLabel("📈  KOSPI 200")
        title.setObjectName("bannerTitle")
        self.time_label = QLabel("네이버 증권 코스피200 지수와 구성 종목을 수집합니다")
        self.time_label.setObjectName("bannerSubtitle")
        banner_text = QVBoxLayout()
        banner_text.setSpacing(2)
        banner_text.addWidget(title)
        banner_text.addWidget(self.time_label)

        self.price_label = QLabel("-")
        self.price_label.setObjectName("indexPrice")
        self.change_label = QLabel("-")
        self.change_label.setObjectName("indexChange")

        banner_layout = QHBoxLayout()
        banner_layout.setContentsMargins(28, 18, 28, 18)
        banner_layout.addLayout(banner_text, 1)
        banner_layout.addWidget(self.price_label)
        banner_layout.addSpacing(14)
        banner_layout.addWidget(self.change_label)
        banner = QFrame()
        banner.setObjectName("banner")
        banner.setLayout(banner_layout)

        # 지수 세부 정보 (시가/고가/저가/거래량/거래대금/장상태)
        self.stat_labels = {}
        stats = QHBoxLayout()
        stats.setContentsMargins(22, 12, 22, 12)
        for key in ("시가", "고가", "저가", "거래량", "거래대금", "장상태"):
            name = QLabel(key)
            name.setObjectName("statName")
            value = QLabel("-")
            value.setObjectName("statValue")
            self.stat_labels[key] = value
            box = QVBoxLayout()
            box.setSpacing(2)
            box.addWidget(name)
            box.addWidget(value)
            stats.addLayout(box, 1)
        stats_card = self.make_card(stats)

        # 조회 조건 + 버튼
        self.days_spin = QSpinBox()
        self.days_spin.setRange(5, 500)
        self.days_spin.setValue(20)
        self.days_spin.setPrefix("일별 시세 ")
        self.days_spin.setSuffix(" 일")

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("🔍  종목명 또는 종목코드로 필터")
        self.filter_edit.textChanged.connect(self.apply_filter)

        self.auto_check = QCheckBox(f"{REFRESH_MS // 1000}초마다 자동 새로고침")
        self.auto_check.toggled.connect(self.toggle_auto_refresh)
        self.timer = QTimer(self)
        self.timer.setInterval(REFRESH_MS)
        self.timer.timeout.connect(self.start_fetch)

        self.fetch_btn = QPushButton("🚀  데이터 수집")
        self.fetch_btn.setObjectName("primary")
        self.fetch_btn.clicked.connect(self.start_fetch)
        self.save_btn = QPushButton("💾  CSV 저장")
        self.save_btn.setObjectName("secondary")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_csv)
        for btn in (self.fetch_btn, self.save_btn):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        top = QHBoxLayout()
        top.setContentsMargins(18, 14, 18, 14)
        top.setSpacing(10)
        top.addWidget(self.filter_edit, 1)
        top.addWidget(self.days_spin)
        top.addWidget(self.auto_check)
        top.addWidget(self.fetch_btn)
        top.addWidget(self.save_btn)
        control_card = self.make_card(top)

        # 가운데: 탭 (구성 종목 / 일별 시세)
        self.stock_table = self.make_table(STOCK_COLUMNS, stretch_col=2)
        self.stock_table.cellDoubleClicked.connect(self.open_stock)
        self.daily_table = self.make_table(DAILY_COLUMNS, stretch_col=0)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.stock_table, "🏢  구성 종목")
        self.tabs.addTab(self.daily_table, "📅  일별 시세")
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # 하단: 진행 상황
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        # 구성 종목 200개 / 페이지당 50개 = 4페이지
        self.progress_bar.setMaximum(-(-KOSPI200_COUNT // PAGE_SIZE))
        self.status_label = QLabel("✨  '데이터 수집'을 누르세요. 종목을 더블클릭하면 네이버 증권 페이지가 열립니다.")
        self.status_label.setObjectName("status")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(14)
        layout.addWidget(banner)
        layout.addWidget(stats_card)
        layout.addWidget(control_card)
        layout.addWidget(self.tabs, 1)
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

    def make_table(self, columns, stretch_col):
        table = QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setSortingEnabled(True)
        table.verticalHeader().setDefaultSectionSize(34)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        for col in range(len(columns)):
            mode = QHeaderView.ResizeMode.Stretch if col == stretch_col else QHeaderView.ResizeMode.ResizeToContents
            header.setSectionResizeMode(col, mode)
        return table

    def fill_table(self, table, columns, rows):
        # 행을 채우는 동안 정렬이 켜져 있으면 행이 계속 움직이므로 잠시 끕니다.
        table.setSortingEnabled(False)
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            color = change_color(row["전일비"])
            for c, key in enumerate(columns):
                text = str(row[key])
                if key in TEXT_COLUMNS:
                    item = QTableWidgetItem(text)
                else:
                    item = NumericItem(text)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if key in ("현재가", "종가", "전일비", "등락률(%)"):
                    item.setForeground(QColor(color))
                if key == "종목명":
                    item.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
                table.setItem(r, c, item)
        table.setSortingEnabled(True)

    def start_fetch(self):
        if self.worker and self.worker.isRunning():
            return
        self.fetch_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("📡  코스피200 데이터를 가져오는 중...")

        self.worker = FetchWorker(self.days_spin.value())
        self.worker.summary_ready.connect(self.show_summary)
        self.worker.daily_ready.connect(self.show_daily)
        self.worker.page_done.connect(self.on_page_done)
        self.worker.stocks_ready.connect(self.show_stocks)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def show_summary(self, s):
        color = change_color(s["전일비"])
        arrow = "▲" if to_number(s["전일비"]) > 0 else "▼" if to_number(s["전일비"]) < 0 else "-"
        self.price_label.setText(s["현재가"])
        self.change_label.setText(f"{arrow} {s['전일비'].lstrip('-')}  ({s['등락률(%)']}%)")
        self.change_label.setStyleSheet(f"color: {color};")
        for key, label in self.stat_labels.items():
            label.setText(s[key])
        self.time_label.setText(f"기준 시각 {s['기준시각'][:16].replace('T', ' ')}")

    def show_daily(self, rows):
        self.daily = rows
        self.fill_table(self.daily_table, DAILY_COLUMNS, rows)

    def on_page_done(self, page, count):
        self.progress_bar.setValue(min(page, self.progress_bar.maximum()))
        self.status_label.setText(f"📥  구성 종목 {page}페이지 수집 ({count}건)...")

    def show_stocks(self, rows):
        self.stocks = rows
        self.fill_table(self.stock_table, STOCK_COLUMNS, rows)
        self.apply_filter()
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.fetch_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.on_tab_changed()

    def on_failed(self, message):
        self.fetch_btn.setEnabled(True)
        self.save_btn.setEnabled(bool(self.stocks))
        self.status_label.setText(f"⚠️  {message}")
        # 자동 새로고침 중에는 팝업을 반복해서 띄우지 않습니다.
        if not self.timer.isActive():
            QMessageBox.warning(self, "오류", message)

    def on_tab_changed(self, _index=None):
        if not self.stocks:
            return
        if self.tabs.currentIndex() == 0:
            self.status_label.setText(f"✅  구성 종목 {len(self.stocks)}개 · 헤더를 누르면 정렬, 더블클릭하면 종목 페이지가 열립니다.")
        else:
            self.status_label.setText(f"✅  일별 시세 {len(self.daily)}일")

    def apply_filter(self):
        keyword = self.filter_edit.text().strip().lower()
        for r in range(self.stock_table.rowCount()):
            code = self.stock_table.item(r, STOCK_COLUMNS.index("종목코드")).text()
            name = self.stock_table.item(r, STOCK_COLUMNS.index("종목명")).text().lower()
            self.stock_table.setRowHidden(r, bool(keyword) and keyword not in name and keyword not in code)

    def toggle_auto_refresh(self, on):
        if on:
            self.timer.start()
            self.start_fetch()
        else:
            self.timer.stop()

    def open_stock(self, row, _col):
        code = self.stock_table.item(row, STOCK_COLUMNS.index("종목코드")).text()
        webbrowser.open(STOCK_URL.format(code=code))

    def save_csv(self):
        # 현재 보고 있는 탭의 데이터를 저장합니다.
        if self.tabs.currentIndex() == 0:
            rows, default = self.stocks, "kospi200_stocks.csv"
        else:
            rows, default = self.daily, "kospi200_daily.csv"
        if not rows:
            return
        path, _ = QFileDialog.getSaveFileName(self, "CSV 저장", default, "CSV 파일 (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
        except PermissionError:
            QMessageBox.warning(self, "오류", "파일을 저장할 수 없습니다. 엑셀에서 열려 있다면 닫고 다시 시도하세요.")
            return
        self.status_label.setText(f"💾  저장 완료: {path} ({len(rows)}건)")

    def closeEvent(self, event):
        self.timer.stop()
        if self.worker and self.worker.isRunning():
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
