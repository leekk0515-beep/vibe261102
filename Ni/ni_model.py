"""
회분식 반응기 니켈 나노입자 AI 합성 — 핵심 로직

- 공정 변수 정의 / 시약 투입량 환산 / 실험 절차 생성
- 가상 반응기 시뮬레이터 (실제 데이터가 없을 때 데모·검증용)
- 가우시안 프로세스(Matérn 5/2 ARD) 대리모델 — numpy/scipy만 사용
- 베이지안 최적화 (목표 입경 40 nm에 대한 Monte-Carlo 기대 개선)
- 실험 데이터 CSV 저장소
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import qmc

TARGET_NM = 40.0
TOLERANCE_NM = 2.0

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_FILE = DATA_DIR / "experiments.csv"

# ---------------------------------------------------------------------------
# 1. 공정 변수
# ---------------------------------------------------------------------------

# (키, 한글 이름, 단위, 최소, 최대)
VARIABLES = [
    ("c_ni", "NiSO₄ 농도", "M", 0.05, 0.50),
    ("r_oh", "NaOH/Ni 몰비", "-", 2.0, 8.0),
    ("r_hz", "Hydrazine/Ni 몰비", "-", 0.5, 6.0),
    ("r_p", "NaH₂PO₂/Ni 몰비", "-", 0.0, 1.0),
]
VAR_KEYS = [v[0] for v in VARIABLES]
LOWER = np.array([v[3] for v in VARIABLES])
UPPER = np.array([v[4] for v in VARIABLES])


@dataclass
class ProcessConditions:
    """고정 공정 조건 (요구사항 기준)"""

    water_ml: float = 100.0
    rpm: float = 150.0
    mix_min: float = 30.0       # NaOH 투입 후 교반 시간
    reaction_min: float = 60.0  # 환원제 투입 후 교반 시간
    temp_c: float = 25.0        # 상온


# 시약 물성
MW_NISO4_6H2O = 262.85
MW_NAOH = 40.00
NAOH_WT = 0.50
NAOH_DENSITY = 1.525         # 50 wt% NaOH, g/mL
MW_N2H4_H2O = 50.06
N2H4_H2O_DENSITY = 1.032     # hydrazine monohydrate, g/mL
MW_NAH2PO2_H2O = 105.99


@dataclass
class Recipe:
    c_ni: float
    r_oh: float
    r_hz: float
    r_p: float
    proc: ProcessConditions = field(default_factory=ProcessConditions)

    @classmethod
    def from_array(cls, x, proc: ProcessConditions | None = None) -> "Recipe":
        return cls(*[float(v) for v in x], proc=proc or ProcessConditions())

    def to_array(self) -> np.ndarray:
        return np.array([self.c_ni, self.r_oh, self.r_hz, self.r_p])

    def amounts(self) -> dict:
        """실제 투입량 (g, mL)"""
        n_ni = self.c_ni * self.proc.water_ml / 1000.0
        return {
            "Ni (mmol)": n_ni * 1000,
            "NiSO₄·6H₂O (g)": n_ni * MW_NISO4_6H2O,
            "Water (mL)": self.proc.water_ml,
            "50% NaOH (mL)": n_ni * self.r_oh * MW_NAOH / NAOH_WT / NAOH_DENSITY,
            "NaH₂PO₂·H₂O (g)": n_ni * self.r_p * MW_NAH2PO2_H2O,
            "Hydrazine monohydrate (mL)": n_ni * self.r_hz * MW_N2H4_H2O / N2H4_H2O_DENSITY,
        }

    def procedure(self) -> str:
        a = self.amounts()
        p = self.proc
        return "\n".join([
            f"[레시피] c_Ni={self.c_ni:.3f} M, NaOH/Ni={self.r_oh:.2f}, "
            f"N₂H₄/Ni={self.r_hz:.2f}, NaH₂PO₂/Ni={self.r_p:.3f}",
            f"반응 온도: {p.temp_c:.0f} °C (상온)",
            "",
            f"1. 회분식 반응기에 Water {a['Water (mL)']:.1f} mL와 "
            f"NiSO₄·6H₂O {a['NiSO₄·6H₂O (g)']:.3f} g을 넣고 용해합니다.",
            f"2. 50% NaOH Solution {a['50% NaOH (mL)']:.2f} mL를 넣습니다.",
            f"3. {p.rpm:.0f} rpm으로 {p.mix_min:.0f}분 동안 교반하여 섞어줍니다.",
            f"4. Sodium hypophosphite(NaH₂PO₂·H₂O) {a['NaH₂PO₂·H₂O (g)']:.3f} g과 "
            f"Hydrazine monohydrate {a['Hydrazine monohydrate (mL)']:.2f} mL를 넣습니다.",
            f"5. {p.rpm:.0f} rpm으로 {p.reaction_min / 60:.0f}시간 동안 교반하여 반응시킵니다.",
            "6. 생성물을 세척·건조 후 TEM/SEM/DLS로 평균 입경을 측정해 프로그램에 입력합니다.",
        ])


def to_unit(x: np.ndarray) -> np.ndarray:
    return (np.asarray(x) - LOWER) / (UPPER - LOWER)


def from_unit(u: np.ndarray) -> np.ndarray:
    return LOWER + np.asarray(u) * (UPPER - LOWER)


# ---------------------------------------------------------------------------
# 2. 가상 반응기 (LaMer 핵생성·성장 경험식) — 실제 공정값으로 보정 필요
# ---------------------------------------------------------------------------

class VirtualReactor:
    K_SIZE = 30.8
    K0_RED = 0.01      # 1/min
    EA = 40_000.0      # J/mol

    def __init__(self, noise: float = 0.06, seed: int | None = None):
        self.noise = noise
        self.rng = np.random.default_rng(seed)

    def _kinetics(self, r: Recipe):
        p = r.proc
        arr = math.exp(-self.EA / 8.314 * (1 / (p.temp_c + 273.15) - 1 / 298.15))
        k = (self.K0_RED * r.r_hz ** 1.2 * (r.r_oh / 2) ** 0.8 * (1 + 3 * r.r_p)
             * (p.rpm / 150) ** 0.2 * arr)
        conv = min(1 - math.exp(-k * p.reaction_min), (r.r_hz + 0.5 * r.r_p) / 0.5, 1.0)
        nuclei = k ** 1.5 * (1 + 8 * r.r_p) * r.c_ni ** 0.5 * (p.rpm / 150) ** 0.3
        return k, conv, nuclei

    def true_size(self, r: Recipe) -> float:
        _, conv, nuclei = self._kinetics(r)
        d = self.K_SIZE * (r.c_ni * conv / nuclei) ** (1 / 3)
        d *= 1 + 0.8 * max(0.0, r.c_ni - 0.3)   # 고농도 응집
        return d

    def conversion(self, r: Recipe) -> float:
        return self._kinetics(r)[1]

    def run(self, r: Recipe) -> float:
        """측정 노이즈를 포함한 가상 실험 결과 (nm)"""
        return float(self.true_size(r) * math.exp(self.rng.normal(0, self.noise)))


# ---------------------------------------------------------------------------
# 3. 가우시안 프로세스
# ---------------------------------------------------------------------------

def _matern52(A, B, ls, var):
    d = np.sqrt(np.maximum(((A[:, None, :] - B[None, :, :]) / ls) ** 2, 0).sum(-1))
    s5 = math.sqrt(5) * d
    return var * (1 + s5 + 5 / 3 * d ** 2) * np.exp(-s5)


class GaussianProcess:
    """입력 X∈[0,1]^d, 출력 y(표준화) 에 대한 Matérn 5/2 ARD GP"""

    def __init__(self):
        self.fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray, restarts: int = 6, seed: int = 0):
        self.X = np.asarray(X, float)
        self.y_mean, self.y_std = y.mean(), y.std() or 1.0
        self.y = (y - self.y_mean) / self.y_std
        dim = self.X.shape[1]
        rng = np.random.default_rng(seed)

        def nll(theta):
            ls, var, noise = np.exp(theta[:dim]), np.exp(theta[dim]), np.exp(theta[dim + 1])
            K = _matern52(self.X, self.X, ls, var) + (noise + 1e-8) * np.eye(len(self.X))
            try:
                L = np.linalg.cholesky(K)
            except np.linalg.LinAlgError:
                return 1e10
            a = np.linalg.solve(L.T, np.linalg.solve(L, self.y))
            return 0.5 * self.y @ a + np.log(np.diag(L)).sum()

        bounds = [(math.log(0.05), math.log(5.0))] * dim + [
            (math.log(0.05), math.log(10.0)), (math.log(1e-4), math.log(0.5))]
        best = None
        for i in range(restarts):
            x0 = ([math.log(0.5)] * dim + [0.0, math.log(0.01)]) if i == 0 else \
                [rng.uniform(lo, hi) for lo, hi in bounds]
            res = minimize(nll, x0, method="L-BFGS-B", bounds=bounds)
            if best is None or res.fun < best.fun:
                best = res
        t = best.x
        self.ls, self.var, self.noise = np.exp(t[:dim]), np.exp(t[dim]), np.exp(t[dim + 1])
        K = _matern52(self.X, self.X, self.ls, self.var) + (self.noise + 1e-8) * np.eye(len(self.X))
        self.L = np.linalg.cholesky(K)
        self.alpha = np.linalg.solve(self.L.T, np.linalg.solve(self.L, self.y))
        self.fitted = True
        return self

    def predict(self, Xs: np.ndarray):
        """(평균, 표준편차) — 원래 y 스케일"""
        Ks = _matern52(np.asarray(Xs, float), self.X, self.ls, self.var)
        mu = Ks @ self.alpha
        v = np.linalg.solve(self.L, Ks.T)
        var = np.maximum(self.var - (v ** 2).sum(0), 1e-12)
        return mu * self.y_std + self.y_mean, np.sqrt(var) * self.y_std


# ---------------------------------------------------------------------------
# 4. 베이지안 최적화
# ---------------------------------------------------------------------------

@dataclass
class Suggestion:
    recipe: Recipe
    pred_nm: float
    low_nm: float
    high_nm: float
    score: float          # EI 또는 최종 추천 점수
    kind: str             # "초기설계" / "EI" / "최종"


class NiOptimizer:
    def __init__(self, target_nm: float = TARGET_NM, seed: int = 0):
        self.target = target_nm
        self.rng = np.random.default_rng(seed)
        self.gp: GaussianProcess | None = None
        self._z = self.rng.standard_normal(256)  # MC 표본 고정 → 결정적 결과

    # -- 학습 --
    def fit(self, df: pd.DataFrame) -> bool:
        if len(df) < 3:
            self.gp = None
            return False
        X = to_unit(df[VAR_KEYS].to_numpy(float))
        y = np.log(df["size_nm"].to_numpy(float))
        self.gp = GaussianProcess().fit(X, y)
        return True

    def predict(self, x_raw: np.ndarray):
        """입경 예측 (중앙값, 95% 하한, 95% 상한) nm"""
        mu, sd = self.gp.predict(to_unit(np.atleast_2d(x_raw)))
        return np.exp(mu), np.exp(mu - 1.96 * sd), np.exp(mu + 1.96 * sd)

    # -- 후보 --
    def _candidates(self, df: pd.DataFrame, n: int = 6000) -> np.ndarray:
        U = self.rng.random((n, len(VAR_KEYS)))
        if len(df):
            err = (df["size_nm"] - self.target).abs().to_numpy()
            top = to_unit(df[VAR_KEYS].to_numpy(float)[np.argsort(err)[:3]])
            local = np.concatenate([
                np.clip(t + self.rng.normal(0, s, (n // 6, len(VAR_KEYS))), 0, 1)
                for t in top for s in (0.03, 0.1)])
            U = np.vstack([U, local])
        return U

    def _ei(self, U: np.ndarray, best_err: float) -> np.ndarray:
        mu, sd = self.gp.predict(U)
        d = np.exp(mu[:, None] + sd[:, None] * self._z[None, :])
        err = np.abs(d - self.target)
        return np.maximum(best_err - err, 0).mean(1)

    def _pick_diverse(self, U, scores, k, min_dist=0.08):
        chosen = []
        for i in np.argsort(-scores):
            if all(np.linalg.norm(U[i] - U[j]) >= min_dist for j in chosen):
                chosen.append(i)
            if len(chosen) == k:
                break
        return chosen

    def _make(self, u, score, kind, proc):
        x = from_unit(u)
        if self.gp is not None:
            m, lo, hi = (float(v[0]) for v in self.predict(x))
        else:
            m = lo = hi = float("nan")
        return Suggestion(Recipe.from_array(x, proc), m, lo, hi, float(score), kind)

    def suggest(self, df: pd.DataFrame, k: int = 3, proc: ProcessConditions | None = None,
                n_initial: int = 5) -> list[Suggestion]:
        """다음 실험 조건 추천"""
        proc = proc or ProcessConditions()
        if len(df) < n_initial or not self.fit(df):
            m = max(k, n_initial - len(df))
            U = qmc.LatinHypercube(d=len(VAR_KEYS), seed=self.rng).random(m)
            self.fit(df)  # 데이터 3개 이상이면 예측값도 함께 표시
            return [self._make(u, 0.0, "초기설계", proc) for u in U[:m]]
        best_err = float((df["size_nm"] - self.target).abs().min())
        U = self._candidates(df)
        ei = self._ei(U, best_err)
        return [self._make(U[i], ei[i], "EI", proc) for i in self._pick_diverse(U, ei, k)]

    def best_recipe(self, df: pd.DataFrame, kappa: float = 1.0,
                    proc: ProcessConditions | None = None) -> Suggestion | None:
        """현재 모델 기준 40 nm에 가장 가깝고 확실한 레시피"""
        if not self.fit(df):
            return None
        U = self._candidates(df, 8000)
        mu, sd = self.gp.predict(U)
        med = np.exp(mu)
        score = np.abs(med - self.target) + kappa * med * sd  # 불확실성(nm 환산) 패널티
        i = int(np.argmin(score))
        return self._make(U[i], score[i], "최종", proc or ProcessConditions())


# ---------------------------------------------------------------------------
# 5. 실험 데이터 저장소
# ---------------------------------------------------------------------------

COLUMNS = ["id", "source", *VAR_KEYS, "rpm", "mix_min", "reaction_min", "temp_c",
           "size_nm", "note", "timestamp"]


class ExperimentStore:
    def __init__(self, path: Path = DATA_FILE):
        self.path = Path(path)

    def load(self) -> pd.DataFrame:
        if not self.path.exists():
            return pd.DataFrame(columns=COLUMNS)
        df = pd.read_csv(self.path, encoding="utf-8-sig")
        for c in COLUMNS:
            if c not in df:
                df[c] = np.nan
        return df[COLUMNS]

    def save(self, df: pd.DataFrame):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.path, index=False, encoding="utf-8-sig")

    def add(self, recipe: Recipe, size_nm: float, source: str = "real", note: str = "") -> pd.DataFrame:
        df = self.load()
        p = recipe.proc
        row = {
            "id": int(df["id"].max()) + 1 if len(df) else 1, "source": source,
            "c_ni": recipe.c_ni, "r_oh": recipe.r_oh, "r_hz": recipe.r_hz, "r_p": recipe.r_p,
            "rpm": p.rpm, "mix_min": p.mix_min, "reaction_min": p.reaction_min, "temp_c": p.temp_c,
            "size_nm": float(size_nm), "note": note,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True) if len(df) else pd.DataFrame([row])
        self.save(df)
        return df

    def delete(self, exp_id: int) -> pd.DataFrame:
        df = self.load()
        df = df[df["id"] != exp_id]
        self.save(df)
        return df

    def clear(self):
        if self.path.exists():
            self.path.unlink()


# ---------------------------------------------------------------------------
# 6. 자동 최적화 루프 (가상 반응기)
# ---------------------------------------------------------------------------

def run_closed_loop(rounds: int = 15, store: ExperimentStore | None = None,
                    seed: int = 0, callback=None) -> pd.DataFrame:
    """추천 → 가상 실험 → 기록을 rounds회 반복. 목표 ±허용오차 도달 시 조기 종료."""
    store = store or ExperimentStore()
    reactor = VirtualReactor(seed=seed)
    opt = NiOptimizer(seed=seed)
    df = store.load()
    for i in range(rounds):
        s = opt.suggest(df, k=1)[0]
        size = reactor.run(s.recipe)
        df = store.add(s.recipe, size, source="virtual", note=f"auto {s.kind}")
        if callback:
            callback(i + 1, s, size)
        if abs(size - TARGET_NM) <= TOLERANCE_NM and s.kind == "EI":
            break
    return df
