"""
S&P 500 과거 데이터 분석 GUI (PyQt6)

클랜징/분석/그래프 로직은 sp500_analysis.py의 함수를 그대로 사용합니다.

사용법:
    python sp500_gui.py
    (실행파일 빌드: build_sp500_exe.bat → dist\\SP500Analyzer.exe)

필요 패키지:
    pip install pandas numpy matplotlib PyQt6
"""

import sys
from pathlib import Path

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import sp500_analysis as sa

UP_COLOR = QColor("#d62728")
DOWN_COLOR = QColor("#1f77b4")


class ChartWidget(QWidget):
    """matplotlib Figure + 툴바(확대/이동/저장)를 담은 위젯"""

    def __init__(self, rows=1, cols=1):
        super().__init__()
        self.figure = Figure(figsize=(10, 5), tight_layout=True)
        self.axes = self.figure.subplots(rows, cols, squeeze=False).ravel()
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self))
        layout.addWidget(self.canvas)

    def draw(self, *plotters):
        """plotters: 각 Axes에 그릴 함수(ax를 인자로 받음)"""
        for ax, plot in zip(self.axes, plotters):
            ax.clear()
            plot(ax)
        self.canvas.draw_idle()


def find_default_csv():
    """기본 CSV 찾기: exe(또는 스크립트) 옆 → 현재 폴더 → exe에 포함된 data 폴더 순"""
    name = sa.DEFAULT_CSV.name
    candidates = [
        Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent / name,
        Path.cwd() / name,
    ]
    if hasattr(sys, "_MEIPASS"):  # PyInstaller exe는 포함 파일을 임시 폴더에 풉니다
        candidates.append(Path(sys._MEIPASS) / "data" / name)
    return next((p for p in candidates if p.exists()), None)


def make_table(df, index_label="", color_cols=(), decimals=2):
    """DataFrame을 QTableWidget으로 변환. color_cols 컬럼은 양수 빨강/음수 파랑"""
    table = QTableWidget(len(df), len(df.columns) + 1)
    table.setHorizontalHeaderLabels([index_label] + [str(c) for c in df.columns])
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    for i, (idx, row) in enumerate(df.iterrows()):
        label = f"{idx:%Y-%m-%d}" if isinstance(idx, pd.Timestamp) else str(idx)
        table.setItem(i, 0, QTableWidgetItem(label))
        for j, (col, val) in enumerate(row.items(), start=1):
            if pd.api.types.is_integer_dtype(df[col]):
                text = f"{int(val):,}"  # iterrows가 float로 바꾼 정수 컬럼 복원
            elif isinstance(val, float):
                text = "" if pd.isna(val) else f"{val:,.{decimals}f}"
            else:
                text = str(val)
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if col in color_cols and isinstance(val, (int, float)) and not pd.isna(val):
                item.setForeground(UP_COLOR if val > 0 else DOWN_COLOR)
            table.setItem(i, j, item)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    return table


def titled(title, widget):
    box = QGroupBox(title)
    QVBoxLayout(box).addWidget(widget)
    return box


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("S&P 500 과거 데이터 분석")
        self.resize(1300, 820)
        self.df = None
        self.result = None

        # 상단: 파일 선택 + 종가 그래프 기간 설정
        self.path_label = QLabel("CSV 파일을 열어 주세요")
        open_btn = QPushButton("CSV 열기")
        open_btn.clicked.connect(self.open_file)

        self.start_edit = QDateEdit(QDate(2000, 1, 1))
        self.end_edit = QDateEdit(QDate(2019, 12, 31))
        for edit in (self.start_edit, self.end_edit):
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("yyyy-MM-dd")
        apply_btn = QPushButton("기간 적용")
        apply_btn.clicked.connect(self.draw_close_chart)

        top = QHBoxLayout()
        top.addWidget(open_btn)
        top.addWidget(self.path_label, 1)
        top.addWidget(QLabel("종가 그래프 기간"))
        top.addWidget(self.start_edit)
        top.addWidget(QLabel("~"))
        top.addWidget(self.end_edit)
        top.addWidget(apply_btn)

        self.tabs = QTabWidget()
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(top)
        layout.addWidget(self.tabs)
        self.setCentralWidget(central)
        self.statusBar().showMessage("준비")

        # 고정 탭: 종가 추이 그래프
        self.close_chart = ChartWidget()
        self.tabs.addTab(self.close_chart, "종가 추이")

        default_csv = find_default_csv()
        if default_csv:
            self.load(default_csv)

    # ---------------- 데이터 로드 ----------------
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "S&P 500 CSV 열기", "", "CSV 파일 (*.csv)")
        if path:
            self.load(Path(path))

    def load(self, path):
        try:
            df, log = sa.load_and_clean(path)
            result = sa.analyze(df)
        except Exception as e:
            QMessageBox.critical(self, "오류", f"파일을 분석하지 못했습니다.\n\n{e}")
            return
        self.df, self.result = df, result
        self.path_label.setText(str(path))
        self.statusBar().showMessage(
            f"{len(df):,}행 로드 · 기간 {df.index.min():%Y-%m-%d} ~ {df.index.max():%Y-%m-%d}"
        )
        self.start_edit.setMinimumDate(QDate(df.index.min().year, 1, 1))
        self.end_edit.setMaximumDate(QDate(df.index.max().year, 12, 31))
        self.build_tabs(log)

    # ---------------- 탭 구성 ----------------
    def build_tabs(self, log):
        # 종가 추이 탭만 남기고 다시 생성
        while self.tabs.count() > 1:
            self.tabs.removeTab(1)
        df, r = self.df, self.result
        self.draw_close_chart()

        self.tabs.addTab(self.summary_tab(log), "요약")
        self.tabs.addTab(self.yearly_tab(), "연도별")
        self.tabs.addTab(self.season_tab(), "월별·요일별")
        self.tabs.addTab(self.risk_tab(), "낙폭·변동성")
        self.tabs.addTab(self.ma_tab(), "이동평균")
        self.tabs.addTab(make_table(df.iloc[::-1], "날짜", color_cols=("ChangePct",)), "정제 데이터")

    def summary_tab(self, log):
        r = self.result
        form = QFormLayout()
        for key, value in r["summary"].items():
            val = QLabel(value)
            val.setFont(QFont("Malgun Gothic", 11, QFont.Weight.Bold))
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            form.addRow(QLabel(key), val)
        perf = QWidget()
        perf.setLayout(form)

        log_list = QListWidget()
        log_list.addItems(log)

        left = QVBoxLayout()
        left.addWidget(titled("기간 전체 성과", perf))
        left.addWidget(titled("데이터 클랜징 내역", log_list))
        left_w = QWidget()
        left_w.setLayout(left)

        extremes = QSplitter(Qt.Orientation.Vertical)
        extremes.addWidget(titled("일간 상승률 상위 10일", make_table(r["top"].to_frame("수익률(%)"), "날짜", ("수익률(%)",))))
        extremes.addWidget(titled("일간 하락률 상위 10일", make_table(r["bottom"].to_frame("수익률(%)"), "날짜", ("수익률(%)",))))

        right = QSplitter(Qt.Orientation.Vertical)
        right.addWidget(titled("기초 통계량", make_table(r["describe"], "통계")))
        right.addWidget(extremes)

        split = QSplitter()
        split.addWidget(left_w)
        split.addWidget(right)
        split.setSizes([550, 750])
        return split

    def yearly_tab(self):
        chart = ChartWidget()
        chart.draw(lambda ax: sa.plot_yearly(ax, self.result))
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(chart)
        split.addWidget(make_table(self.result["yearly"], "연도", ("수익률(%)",)))
        return split

    def season_tab(self):
        r = self.result
        chart = ChartWidget()
        chart.draw(lambda ax: sa.plot_season(ax, r))
        tables = QSplitter()
        tables.addWidget(titled("월별 월간 수익률", make_table(r["season"], "월", ("평균(%)", "중앙값(%)"))))
        tables.addWidget(titled("요일별 일간 수익률", make_table(r["weekday"], "요일", ("평균(%)",), decimals=4)))
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(chart)
        split.addWidget(tables)
        return split

    def risk_tab(self):
        r = self.result
        chart = ChartWidget(3, 1)
        chart.draw(
            lambda ax: sa.plot_drawdown(ax, r),
            lambda ax: sa.plot_volatility(ax, r),
            lambda ax: sa.plot_return_hist(ax, r),
        )
        return chart

    def ma_tab(self):
        chart = ChartWidget()
        chart.draw(lambda ax: sa.plot_moving_average(ax, self.df, self.result))
        crosses = self.result["crosses"].iloc[::-1].to_frame("신호")
        split = QSplitter()
        split.addWidget(chart)
        split.addWidget(titled("50일/200일 크로스 발생일", make_table(crosses, "날짜")))
        split.setSizes([1000, 300])
        return split

    def draw_close_chart(self):
        if self.df is None:
            return
        start = self.start_edit.date().toString("yyyy-MM-dd")
        end = self.end_edit.date().toString("yyyy-MM-dd")
        if start >= end:
            QMessageBox.warning(self, "기간 오류", "시작일이 종료일보다 빨라야 합니다.")
            return
        self.close_chart.draw(lambda ax: sa.plot_close(ax, self.df, start, end))
        self.tabs.setCurrentIndex(0)


def main():
    sa.setup_korean_font()
    app = QApplication(sys.argv)
    app.setFont(QFont("Malgun Gothic", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
