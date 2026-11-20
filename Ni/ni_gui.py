"""
회분식 반응기 니켈 나노입자 AI 합성 프로그램 — GUI (PyQt6)

사용법:
    python ni_gui.py

필요 패키지:
    pip install numpy scipy pandas matplotlib PyQt6
"""

import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QSpinBox,
    QSplitter, QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

import ni_model as m

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
GOOD = QColor("#d8f3dc")


def var_spinboxes():
    boxes = {}
    for key, name, unit, lo, hi in m.VARIABLES:
        sb = QDoubleSpinBox()
        sb.setDecimals(3); sb.setRange(lo, hi); sb.setSingleStep((hi - lo) / 50)
        sb.setValue((lo + hi) / 2)
        boxes[key] = sb
    return boxes


def fill_table(table: QTableWidget, headers, rows, highlight=None):
    table.clear(); table.setColumnCount(len(headers)); table.setRowCount(len(rows))
    table.setHorizontalHeaderLabels(headers)
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            text = f"{v:.3f}" if isinstance(v, float) else str(v)
            it = QTableWidgetItem(text)
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if highlight and highlight(r):
                it.setBackground(GOOD)
            table.setItem(r, c, it)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)


class Chart(QWidget):
    def __init__(self):
        super().__init__()
        self.figure = Figure(figsize=(8, 4), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(NavigationToolbar2QT(self.canvas, self)); lay.addWidget(self.canvas)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("회분식 반응기 니켈 나노입자 AI 합성 프로그램 — 목표 40 nm")
        self.resize(1250, 800)
        self.store = m.ExperimentStore()
        self.opt = m.NiOptimizer()
        self.reactor = m.VirtualReactor(seed=42)
        self.suggestions: list[m.Suggestion] = []

        tabs = QTabWidget()
        tabs.addTab(self._tab_suggest(), "① AI 레시피 추천")
        tabs.addTab(self._tab_data(), "② 실험 데이터")
        tabs.addTab(self._tab_predict(), "③ 입경 예측")
        tabs.addTab(self._tab_history(), "④ 최적화 이력")
        self.setCentralWidget(tabs)
        self.statusBar()
        self.refresh()

    # ---------------- ① 추천 ----------------
    def _tab_suggest(self):
        w = QWidget(); lay = QVBoxLayout(w)

        proc = QGroupBox("고정 공정 조건"); f = QHBoxLayout(proc)
        self.water = QDoubleSpinBox(); self.water.setRange(10, 5000); self.water.setValue(100)
        self.water.setSuffix(" mL")
        f.addWidget(QLabel("Water")); f.addWidget(self.water)
        f.addWidget(QLabel("교반 150 rpm · NaOH 후 30분 · 환원제 후 1시간 · 상온 25 °C"))
        f.addStretch(); lay.addWidget(proc)

        bar = QHBoxLayout()
        self.k_spin = QSpinBox(); self.k_spin.setRange(1, 10); self.k_spin.setValue(3)
        b1 = QPushButton("다음 실험 추천 (베이지안 최적화)"); b1.clicked.connect(self.on_suggest)
        b2 = QPushButton("최종 40 nm 레시피"); b2.clicked.connect(self.on_best)
        b3 = QPushButton("선택 레시피 가상 실험"); b3.clicked.connect(self.on_virtual)
        b4 = QPushButton("자동 최적화 데모"); b4.clicked.connect(self.on_demo)
        self.demo_n = QSpinBox(); self.demo_n.setRange(1, 50); self.demo_n.setValue(15)
        bar.addWidget(QLabel("추천 개수")); bar.addWidget(self.k_spin)
        for b in (b1, b2, b3):
            bar.addWidget(b)
        bar.addStretch(); bar.addWidget(QLabel("데모 횟수")); bar.addWidget(self.demo_n); bar.addWidget(b4)
        lay.addLayout(bar)

        sp = QSplitter(Qt.Orientation.Vertical)
        self.sug_table = QTableWidget()
        self.sug_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.sug_table.itemSelectionChanged.connect(self.on_select_suggestion)
        sp.addWidget(self.sug_table)

        bottom = QWidget(); bl = QHBoxLayout(bottom)
        self.proc_text = QTextEdit(); self.proc_text.setReadOnly(True)
        self.proc_text.setFont(QFont("Malgun Gothic", 10))
        bl.addWidget(self.proc_text, 3)
        res = QGroupBox("실측 결과 입력"); rf = QFormLayout(res)
        self.meas = QDoubleSpinBox(); self.meas.setRange(0.1, 10000); self.meas.setValue(40)
        self.meas.setSuffix(" nm")
        self.meas_note = QLineEdit()
        bsave = QPushButton("선택 레시피 결과 저장"); bsave.clicked.connect(self.on_save_measured)
        rf.addRow("측정 평균 입경", self.meas); rf.addRow("메모", self.meas_note); rf.addRow(bsave)
        bl.addWidget(res, 1)
        sp.addWidget(bottom); sp.setSizes([300, 400])
        lay.addWidget(sp)
        return w

    def proc(self):
        return m.ProcessConditions(water_ml=self.water.value())

    def show_suggestions(self, sugs):
        self.suggestions = sugs
        headers = ["구분", "예측(nm)", "95%하한", "95%상한", *[v[1] for v in m.VARIABLES],
                   *list(sugs[0].recipe.amounts().keys())[1:]]
        rows = [[s.kind, s.pred_nm, s.low_nm, s.high_nm, *s.recipe.to_array().tolist(),
                 *list(s.recipe.amounts().values())[1:]] for s in sugs]
        fill_table(self.sug_table, headers, rows)
        self.sug_table.selectRow(0)

    def on_suggest(self):
        df = self.store.load()
        sugs = self.opt.suggest(df, k=self.k_spin.value(), proc=self.proc())
        self.show_suggestions(sugs)
        msg = "데이터가 부족하여 라틴 하이퍼큐브 초기 실험을 추천합니다." if sugs[0].kind == "초기설계" \
            else "기대 개선(EI)이 큰 순서로 추천했습니다."
        self.statusBar().showMessage(msg)

    def on_best(self):
        s = self.opt.best_recipe(self.store.load(), proc=self.proc())
        if s is None:
            QMessageBox.information(self, "안내", "실험 데이터가 3건 이상 필요합니다."); return
        self.show_suggestions([s])

    def selected(self):
        r = self.sug_table.currentRow()
        return self.suggestions[r] if 0 <= r < len(self.suggestions) else None

    def on_select_suggestion(self):
        s = self.selected()
        if s:
            pred = "" if np.isnan(s.pred_nm) else \
                f"\n\nAI 예측 입경: {s.pred_nm:.1f} nm (95% {s.low_nm:.1f}–{s.high_nm:.1f} nm)"
            self.proc_text.setPlainText(s.recipe.procedure() + pred)

    def on_save_measured(self):
        s = self.selected()
        if not s:
            QMessageBox.information(self, "안내", "추천 레시피를 먼저 선택하세요."); return
        self.store.add(s.recipe, self.meas.value(), "real", self.meas_note.text())
        self.statusBar().showMessage(f"저장: {self.meas.value():.1f} nm"); self.refresh()

    def on_virtual(self):
        s = self.selected()
        if not s:
            QMessageBox.information(self, "안내", "추천 레시피를 먼저 선택하세요."); return
        size = self.reactor.run(s.recipe)
        self.store.add(s.recipe, size, "virtual", f"가상 {s.kind}")
        self.statusBar().showMessage(f"가상 실험 결과: {size:.1f} nm"); self.refresh()

    def on_demo(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            df = m.run_closed_loop(self.demo_n.value(), self.store, seed=len(self.store.load()))
        finally:
            QApplication.restoreOverrideCursor()
        err = (df["size_nm"] - m.TARGET_NM).abs()
        self.refresh()
        QMessageBox.information(self, "자동 최적화 완료",
                                f"총 {len(df)}건, 최소 오차 {err.min():.2f} nm "
                                f"(실험 {int(df.loc[err.idxmin(), 'id'])}번)")
        self.on_best()

    # ---------------- ② 데이터 ----------------
    def _tab_data(self):
        w = QWidget(); lay = QVBoxLayout(w)
        add = QGroupBox("실험 결과 직접 입력"); h = QHBoxLayout(add)
        self.add_boxes = var_spinboxes()
        for (key, name, *_), sb in zip(m.VARIABLES, self.add_boxes.values()):
            h.addWidget(QLabel(name)); h.addWidget(sb)
        self.add_size = QDoubleSpinBox(); self.add_size.setRange(0.1, 10000); self.add_size.setSuffix(" nm")
        h.addWidget(QLabel("입경")); h.addWidget(self.add_size)
        b = QPushButton("추가"); b.clicked.connect(self.on_add_row); h.addWidget(b)
        lay.addWidget(add)

        bar = QHBoxLayout()
        for text, fn in (("선택 행 삭제", self.on_delete), ("CSV 가져오기", self.on_import),
                         ("CSV 내보내기", self.on_export), ("전체 삭제", self.on_clear)):
            bt = QPushButton(text); bt.clicked.connect(fn); bar.addWidget(bt)
        bar.addStretch(); lay.addLayout(bar)
        self.data_table = QTableWidget()
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        lay.addWidget(self.data_table)
        return w

    def on_add_row(self):
        r = m.Recipe(*[sb.value() for sb in self.add_boxes.values()], proc=self.proc())
        self.store.add(r, self.add_size.value(), "real"); self.refresh()

    def on_delete(self):
        r = self.data_table.currentRow()
        if r >= 0:
            self.store.delete(int(self.data_table.item(r, 0).text())); self.refresh()

    def on_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "CSV 가져오기", "", "CSV (*.csv)")
        if not path:
            return
        import pandas as pd
        new = pd.read_csv(path, encoding="utf-8-sig")
        missing = [c for c in [*m.VAR_KEYS, "size_nm"] if c not in new]
        if missing:
            QMessageBox.warning(self, "오류", f"필수 열 누락: {missing}"); return
        for _, row in new.iterrows():
            self.store.add(m.Recipe(*[row[k] for k in m.VAR_KEYS]), row["size_nm"],
                           str(row.get("source", "real")), str(row.get("note", "")))
        self.refresh()

    def on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "CSV 내보내기", "experiments.csv", "CSV (*.csv)")
        if path:
            self.store.load().to_csv(path, index=False, encoding="utf-8-sig")

    def on_clear(self):
        if QMessageBox.question(self, "확인", "모든 실험 데이터를 삭제할까요?") == \
                QMessageBox.StandardButton.Yes:
            self.store.clear(); self.refresh()

    # ---------------- ③ 예측 ----------------
    def _tab_predict(self):
        w = QWidget(); lay = QHBoxLayout(w)
        left = QGroupBox("조건 입력"); f = QFormLayout(left)
        self.pred_boxes = var_spinboxes()
        for (key, name, unit, *_), sb in zip(m.VARIABLES, self.pred_boxes.values()):
            f.addRow(f"{name} ({unit})", sb)
            sb.valueChanged.connect(self.update_prediction)
        self.pred_label = QLabel("—"); self.pred_label.setFont(QFont("Malgun Gothic", 14, QFont.Weight.Bold))
        self.pred_label.setWordWrap(True)
        f.addRow(self.pred_label)
        left.setMaximumWidth(380); lay.addWidget(left)
        self.pred_chart = Chart(); lay.addWidget(self.pred_chart)
        return w

    def update_prediction(self):
        fig = self.pred_chart.figure; fig.clear()
        if self.opt.gp is None:
            self.pred_label.setText("실험 데이터 3건 이상 필요"); self.pred_chart.canvas.draw(); return
        x = np.array([sb.value() for sb in self.pred_boxes.values()])
        med, lo, hi = (float(v[0]) for v in self.opt.predict(x))
        self.pred_label.setText(f"예측 입경 {med:.1f} nm\n95% 구간 {lo:.1f} – {hi:.1f} nm")
        for i, (key, name, unit, a, b) in enumerate(m.VARIABLES):
            ax = fig.add_subplot(2, 2, i + 1)
            grid = np.linspace(a, b, 60)
            X = np.tile(x, (60, 1)); X[:, i] = grid
            gm, gl, gh = self.opt.predict(X)
            ax.fill_between(grid, gl, gh, alpha=0.2, color="#1f77b4")
            ax.plot(grid, gm, color="#1f77b4")
            ax.axhline(m.TARGET_NM, color="#d62728", ls="--", lw=1)
            ax.axvline(x[i], color="gray", lw=0.8)
            ax.set_xlabel(f"{name} ({unit})"); ax.set_ylabel("입경 (nm)")
            ax.set_ylim(0, min(300, max(gh.max(), 60) * 1.05))
        self.pred_chart.canvas.draw()

    # ---------------- ④ 이력 ----------------
    def _tab_history(self):
        self.hist_chart = Chart(); return self.hist_chart

    def update_history(self, df):
        fig = self.hist_chart.figure; fig.clear()
        ax1, ax2 = fig.add_subplot(1, 2, 1), fig.add_subplot(1, 2, 2)
        if len(df):
            n = np.arange(1, len(df) + 1)
            colors = ["#2a9d8f" if s == "real" else "#8d99ae" for s in df["source"]]
            ax1.scatter(n, df["size_nm"], c=colors, zorder=3)
            ax1.plot(n, df["size_nm"], color="#ccc", zorder=2)
            ax1.axhspan(m.TARGET_NM - m.TOLERANCE_NM, m.TARGET_NM + m.TOLERANCE_NM, color="#d62728", alpha=0.15)
            ax1.axhline(m.TARGET_NM, color="#d62728", ls="--", lw=1)
            ax1.set_yscale("log")
            err = (df["size_nm"] - m.TARGET_NM).abs().cummin()
            ax2.step(n, err, where="post", color="#264653")
            ax2.axhline(m.TOLERANCE_NM, color="#d62728", ls="--", lw=1)
            ax2.set_yscale("log")
        ax1.set_title("실험 회차별 입경 (초록=실측, 회색=가상)"); ax1.set_xlabel("실험 회차"); ax1.set_ylabel("입경 (nm)")
        ax2.set_title("최소 오차 |d - 40 nm| 추이"); ax2.set_xlabel("실험 회차"); ax2.set_ylabel("오차 (nm)")
        self.hist_chart.canvas.draw()

    # ---------------- 공통 ----------------
    def refresh(self):
        df = self.store.load()
        headers = ["id", "구분", *[v[1] for v in m.VARIABLES], "rpm", "온도(°C)", "입경(nm)", "메모", "시각"]
        rows = [[int(r.id), r.source, r.c_ni, r.r_oh, r.r_hz, r.r_p, f"{r.rpm:.0f}", f"{r.temp_c:.0f}",
                 r.size_nm, "" if str(r.note) == "nan" else r.note, r.timestamp] for r in df.itertuples()]
        fill_table(self.data_table, headers, rows,
                   highlight=lambda i: abs(df["size_nm"].iloc[i] - m.TARGET_NM) <= m.TOLERANCE_NM)
        self.opt.fit(df)
        self.update_prediction()
        self.update_history(df)
        best = "" if not len(df) else f" · 최소 오차 {(df['size_nm'] - m.TARGET_NM).abs().min():.2f} nm"
        self.statusBar().showMessage(f"실험 데이터 {len(df)}건{best}")


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Malgun Gothic", 9))
    win = MainWindow(); win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
