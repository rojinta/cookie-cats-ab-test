"""Independent check. Recomputes every reported figure with different code (plain pandas, scipy and statsmodels, a permutation test) and compares to results/.
Usage: python3 validate.py"""
import json, pathlib, numpy as np, pandas as pd
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest, confint_proportions_2indep, proportion_effectsize
from statsmodels.stats.power import NormalIndPower

root = pathlib.Path(__file__).parent
S = json.loads((root / "results" / "summary.json").read_text())
raw = pd.read_csv(root / "data" / "raw" / "cookie_cats.csv")           # straight from the source file, no SQL
raw["ret_1"] = raw.retention_1.astype(str).str.lower().eq("true")
raw["ret_7"] = raw.retention_7.astype(str).str.lower().eq("true")
A, B = raw[raw.version == "gate_30"], raw[raw.version == "gate_40"]
checks = []


def chk(name, mine, theirs, tol):
    ok = abs(mine - theirs) <= tol
    checks.append(ok)
    print(("OK  " if ok else "FAIL"), f"{name:55s} recomputed={mine:.6g} reported={theirs:.6g}")


chk("players, gate 30", len(A), S["n_a"], 0)
chk("players, gate 40", len(B), S["n_b"], 0)
chi = stats.chisquare([len(A), len(B)])
chk("split check p value", chi.pvalue, S["srm"]["p_value"], 1e-9)
for m in ("ret_7", "ret_1"):
    T = S["tests"][m]
    xs = [A[m].sum(), B[m].sum()]
    ns = [len(A), len(B)]
    chk(f"{m} rate gate 30", xs[0] / ns[0], T["p_a"], 1e-12)
    chk(f"{m} rate gate 40", xs[1] / ns[1], T["p_b"], 1e-12)
    z, p = proportions_ztest(xs[::-1], ns[::-1])                       # gate 40 versus gate 30
    chk(f"{m} z statistic", z, T["z"], 1e-6)
    chk(f"{m} p value", p, T["p_value"], 1e-9)
    lo, hi = confint_proportions_2indep(xs[1], ns[1], xs[0], ns[0], method="wald")
    chk(f"{m} interval low", lo, T["ci_lo"], 1e-9)
    chk(f"{m} interval high", hi, T["ci_hi"], 1e-9)
    # permutation test, shuffle the version labels and see how often chance beats the observed gap
    rng = np.random.default_rng(7)
    y = raw[m].to_numpy().astype(int)
    is_b = (raw.version == "gate_40").to_numpy()
    obs = y[is_b].mean() - y[~is_b].mean()
    cnt = 0
    for _ in range(20000):
        perm = rng.permutation(is_b)
        cnt += abs(y[perm].mean() - y[~perm].mean()) >= abs(obs)
    chk(f"{m} permutation p (20,000 shuffles)", (cnt + 1) / 20001, T["p_value"], 0.004)
adj = sorted([S["tests"]["ret_7"]["p_value"], S["tests"]["ret_1"]["p_value"]])
chk("Holm adjusted p, smaller", min(1, adj[0] * 2), S["tests"]["ret_7"]["p_holm"], 1e-9)
chk("Holm adjusted p, larger", min(1, max(adj[1], adj[0] * 2)), S["tests"]["ret_1"]["p_holm"], 1e-9)
chk("fewer returning players per 100,000, day 7", (B.ret_7.mean() - A.ret_7.mean()) * 100000, S["per_100k"]["diff"], 1e-6)

R = S["rounds"]
chk("mean rounds gate 30", A.sum_gamerounds.mean(), R["mean_a"], 1e-9)
chk("mean rounds gate 40", B.sum_gamerounds.mean(), R["mean_b"], 1e-9)
chk("median rounds gate 30", A.sum_gamerounds.median(), R["median_a"], 0)
chk("median rounds gate 40", B.sum_gamerounds.median(), R["median_b"], 0)
chk("Mann-Whitney p", stats.mannwhitneyu(A.sum_gamerounds, B.sum_gamerounds).pvalue, R["mw_p"], 1e-9)
top = A.sum_gamerounds.idxmax()
chk("mean rounds gate 30 without the top player", A.drop(top).sum_gamerounds.mean(), R["mean_a_without_top"], 1e-9)

bands = {"0 rounds": (0, 0), "1 to 29 rounds": (1, 29), "30 to 99 rounds": (30, 99), "100 or more rounds": (100, 10**9)}
for r in S["bands"]:
    lo_, hi_ = bands[r["band"]]
    ga = A[(A.sum_gamerounds >= lo_) & (A.sum_gamerounds <= hi_)]
    gb = B[(B.sum_gamerounds >= lo_) & (B.sum_gamerounds <= hi_)]
    z, p = proportions_ztest([gb[r["metric"]].sum(), ga[r["metric"]].sum()], [len(gb), len(ga)])
    chk(f'{r["band"]} {r["metric"]} difference', gb[r["metric"]].mean() - ga[r["metric"]].mean(), r["diff"], 1e-12)
    chk(f'{r["band"]} {r["metric"]} p value', p, r["p_value"], 1e-9)

P = S["power"]
n = (len(A) + len(B)) / 2
p0 = A.ret_7.mean()
pw = NormalIndPower()
for d in (0.5, 0.75):
    h = proportion_effectsize(p0, p0 - d / 100)
    nn = pw.solve_power(effect_size=h, alpha=0.05, power=0.8, ratio=1)
    chk(f"players needed per group to see {d} point change", nn, P["need_n"][str(d)], 0.02 * nn)
h = proportion_effectsize(p0, p0 - 0.0082)
chk("power at the observed change (simulated versus formula)", P["simulated"]["0.82"], pw.power(effect_size=h, nobs1=n, alpha=0.05, ratio=1), 0.02)
print()
print(f"{sum(checks)} of {len(checks)} comparisons match.", "ALL MATCH" if all(checks) else "SOME FAILED")
