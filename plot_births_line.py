"""
대한민국 출생아수 라인 그래프 (1970~2025)

그래프 로직은 birth_analysis.plot_births를 사용합니다. (GUI: birth_gui.py)

실행: python plot_births_line.py [엑셀경로]
출력: birth_output/출생아수_라인그래프_1970_2025.png
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt

import birth_analysis as ba

if __name__ == "__main__":
    ba.setup_korean_font()
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ba.DEFAULT_XLSX
    df, _ = ba.load_and_clean(path)

    fig, ax = plt.subplots(figsize=(13, 6))
    ba.plot_births(ax, df, 1970, 2025)
    fig.tight_layout()

    out_path = ba.OUT_DIR / "출생아수_라인그래프_1970_2025.png"
    out_path.parent.mkdir(exist_ok=True)
    fig.savefig(out_path, dpi=150)
    print(f"저장 완료: {out_path}")
    plt.show()
