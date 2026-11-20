"""
대한민국 출생아수·합계출산율 분석 GUI (PyQt6)

클렌징/분석/그래프 로직은 birth_analysis.py의 함수를 그대로 사용합니다.

사용법:
    python birth_gui.py

필요 패키지:
    pip install pandas openpyxl matplotlib PyQt6
"""

import sys
from pathlib import Path

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
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
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import birth_analysis as ba

UP_COLOR = QColor("#1f77b4")
DOWN_COLOR = QColor("#d62728")


class ChartWidget(QWidget):
    """matplotlib Figure + 툴바(확대/이동/저장)를 담은 위젯"""

    def __init__(self, rows=1, cols=1):
        super().__init__()
        self.figure = Figure(figsize=(10, 5), tight_layout=True)
        self.rows, self.cols = rows, cols
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self))
        layout.addWidget(self.canvas)

    def draw(self, *plotters):
        """plotters: 각 Axes에 그릴 함수(ax를 인자로 받음)"""
        # twinx·colorbar가 남긴 축까지 지우기 위해 Figure를 통째로 비우고 다시 만든다
        self.figure.clear()
        axes = self.figure.subplots(self.rows, self.cols, squeeze=False).ravel()
        for ax, plot in zip(axes, plotters):
            plot(ax)
        self.canvas.draw_idle()


def find_default_xlsx():
    """기본 엑셀 찾기: exe(또는 스크립트) 옆 → 현재 폴더 → exe에 포함된 data 폴더 순"""
    name = ba.DEFAULT_XLSX.name
    candidates = [
        Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent / name,
        Path.cwd() / name,
    ]
    if hasattr(sys, "_MEIPASS"):  # PyInstaller exe는 포함 파일을 임시 폴더에 풉니다
        candidates.append(Path(sys._MEIPASS) / "data" / name)
    return next((p for p in candidates if p.exists()), None)


def make_table(df, index_label="", color_cols=(), decimals=2):
    """DataFrame을 QTableWidget으로 변환. color_cols 컬럼은 양수 파랑/음수 빨강"""
    table = QTableWidget(len(df), len(df.columns) + 1)
    table.setHorizontalHeaderLabels([index_label] + [str(c) for c in df.columns])
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    for i, (idx, row) in enumerate(df.iterrows()):
        table.setItem(i, 0, QTableWidgetItem(str(idx)))
        for j, (col, val) in enumerate(row.items(), start=1):
            if pd.isna(val):
                text = ""
            elif pd.api.types.is_integer_dtype(df[col]):
                text = f"{int(val):,}"  # iterrows가 float로 바꾼 정수 컬럼 복원
            elif isinstance(val, float):
                text = f"{val:,.{decimals}f}"
            else:
                text = str(val)
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if col in color_cols and isinstance(val, (int, float)) and not pd.isna(val):
                item.setForeground(UP_COLOR if val > 0 else DOWN_COLOR)
            table.setItem(i, j, item)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    return table


def make_form(items):
    """{항목: 값} dict를 굵은 글씨 값의 폼으로 변환"""
    form = QFormLayout()
    for key, value in items.items():
        val = QLabel(value)
        val.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
        val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        val.setWordWrap(True)
        form.addRow(QLabel(key), val)
    widget = QWidget()
    widget.setLayout(form)
    return widget


def titled(title, widget):
    box = QGroupBox(title)
    QVBoxLayout(box).addWidget(widget)
    return box


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("대한민국 출생아수 분석")
        self.resize(1300, 820)
        self.path = None
        self.df = None
        self.result = None

        # 상단: 파일 선택 + 출생아수 그래프 기간 설정 + 결과 저장
        self.path_label = QLabel("엑셀 파일을 열어 주세요")
        open_btn = QPushButton("엑셀 열기")
        open_btn.clicked.connect(self.open_file)

        self.start_spin = QSpinBox()
        self.end_spin = QSpinBox()
        for spin, value in ((self.start_spin, 1970), (self.end_spin, 2025)):
            spin.setRange(1900, 2100)
            spin.setValue(value)
            spin.setSuffix("년")
        apply_btn = QPushButton("기간 적용")
        apply_btn.clicked.connect(self.draw_births_chart)

        save_btn = QPushButton("결과 저장")
        save_btn.clicked.connect(self.save_results)

        top = QHBoxLayout()
        top.addWidget(open_btn)
        top.addWidget(self.path_label, 1)
        top.addWidget(QLabel("출생아수 그래프 기간"))
        top.addWidget(self.start_spin)
        top.addWidget(QLabel("~"))
        top.addWidget(self.end_spin)
        top.addWidget(apply_btn)
        top.addWidget(save_btn)

        self.tabs = QTabWidget()
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(top)
        layout.addWidget(self.tabs)
        self.setCentralWidget(central)
        self.statusBar().showMessage("준비")

        # 고정 탭: 출생아수 라인 그래프
        self.births_chart = ChartWidget()
        self.tabs.addTab(self.births_chart, "출생아수 추이")

        default_xlsx = find_default_xlsx()
        if default_xlsx:
            self.load(default_xlsx)

    # ---------------- 데이터 로드 ----------------
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "출생아수 엑셀 열기", "", "엑셀 파일 (*.xlsx *.xls)")
        if path:
            self.load(Path(path))

    def load(self, path):
        try:
            df, log = ba.load_and_clean(path)
            result = ba.analyze(df)
        except Exception as e:
            QMessageBox.critical(self, "오류", f"파일을 분석하지 못했습니다.\n\n{e}")
            return
        self.path, self.df, self.result = path, df, result
        self.path_label.setText(str(path))
        first, last = int(df.index.min()), int(df.index.max())
        self.statusBar().showMessage(f"{len(df)}개 연도 로드 · 기간 {first} ~ {last}년")
        for spin in (self.start_spin, self.end_spin):
            spin.setRange(first, last)
        self.start_spin.setValue(first)
        self.end_spin.setValue(last)
        self.build_tabs(log)

    # ---------------- 탭 구성 ----------------
    def build_tabs(self, log):
        # 출생아수 추이 탭만 남기고 다시 생성
        while self.tabs.count() > 1:
            self.tabs.removeTab(1)
        self.draw_births_chart()

        self.tabs.addTab(self.summary_tab(log), "요약")
        self.tabs.addTab(self.decade_tab(), "연대별")
        self.tabs.addTab(self.trend_tab(), "출산율·자연증가")
        self.tabs.addTab(self.change_tab(), "증감률")
        self.tabs.addTab(self.corr_tab(), "상관관계")
        data = self.df.drop(columns="연대").iloc[::-1]
        self.tabs.addTab(make_table(data, "연도", color_cols=("자연증가건수", "출생아수_증감률(%)")), "정제 데이터")

    def summary_tab(self, log):
        r = self.result
        log_list = QListWidget()
        log_list.addItems(log)

        left = QSplitter(Qt.Orientation.Vertical)
        left.addWidget(titled("핵심 요약", make_form(r["summary"])))
        left.addWidget(titled("주요 이정표 (최초 도달 연도)", make_form(r["milestones"])))
        left.addWidget(titled("데이터 클렌징 내역", log_list))

        right = QSplitter(Qt.Orientation.Vertical)
        right.addWidget(titled("기술통계", make_table(r["describe"], "통계")))
        right.addWidget(titled("최고·최저 기록", make_table(r["extremes"], "지표")))

        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([550, 750])
        return split

    def decade_tab(self):
        chart = ChartWidget()
        chart.draw(lambda ax: ba.plot_decade(ax, self.result["decade"]))
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(chart)
        split.addWidget(make_table(self.result["decade"], "연대", ("자연증가건수_평균",)))
        split.setSizes([550, 250])
        return split

    def trend_tab(self):
        chart = ChartWidget(2, 1)
        chart.draw(lambda ax: ba.plot_tfr(ax, self.df), lambda ax: ba.plot_birth_death(ax, self.df))
        return chart

    def change_tab(self):
        r = self.result
        chart = ChartWidget()
        chart.draw(lambda ax: ba.plot_change(ax, self.df))
        tables = QSplitter(Qt.Orientation.Vertical)
        tables.addWidget(titled("감소폭 상위 10개 연도", make_table(r["top_drop"].to_frame("증감률(%)"), "연도", ("증감률(%)",))))
        tables.addWidget(titled("증가폭 상위 10개 연도", make_table(r["top_rise"].to_frame("증감률(%)"), "연도", ("증감률(%)",))))
        split = QSplitter()
        split.addWidget(chart)
        split.addWidget(tables)
        split.setSizes([950, 350])
        return split

    def corr_tab(self):
        chart = ChartWidget()
        chart.draw(lambda ax: ba.plot_corr(ax, self.result["corr"]))
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(chart)
        split.addWidget(make_table(self.result["corr"], "지표", decimals=3))
        split.setSizes([550, 250])
        return split

    def draw_births_chart(self):
        if self.df is None:
            return
        start, end = self.start_spin.value(), self.end_spin.value()
        if start >= end:
            QMessageBox.warning(self, "기간 오류", "시작 연도가 종료 연도보다 빨라야 합니다.")
            return
        self.births_chart.draw(lambda ax: ba.plot_births(ax, self.df, start, end))
        self.tabs.setCurrentIndex(0)

    # ---------------- 결과 저장 ----------------
    def save_results(self):
        if self.df is None:
            return
        start_dir = Path(self.path).parent  # exe에서는 스크립트 경로가 임시 폴더라 열어 둔 엑셀 위치 사용
        folder = QFileDialog.getExistingDirectory(self, "결과를 저장할 폴더 선택", str(start_dir))
        if not folder:
            return
        out = Path(folder)
        r = self.result
        try:
            self.df.to_csv(out / "출생통계_정제.csv", encoding="utf-8-sig")
            r["decade"].to_csv(out / "연대별_평균.csv", encoding="utf-8-sig")
            r["corr"].to_csv(out / "상관관계.csv", encoding="utf-8-sig")
            self.births_chart.figure.savefig(out / "출생아수_라인그래프.png", dpi=150)
        except OSError as e:
            QMessageBox.critical(self, "저장 실패", str(e))
            return
        self.statusBar().showMessage(f"저장 완료: {out}")


def main():
    ba.setup_korean_font()
    app = QApplication(sys.argv)
    app.setFont(QFont("Malgun Gothic", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
