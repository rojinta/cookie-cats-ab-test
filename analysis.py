"""Statistics for the Cookie Cats gate test. Reads the `players` table built by the SQL, writes results/*.csv and results/summary.json.
Plan written before looking at results. Primary metric is 7-day retention. Day-1 retention is secondary. Rounds played is a guardrail."""
import json, math, pathlib
import duckdb, numpy as np, pandas as pd
from scipy import stats

root = pathlib.Path(__file__).parent
out = root / "results"
out.mkdir(exist_ok=True)
rng = np.random.default_rng(2026)
Z = stats.norm.ppf(0.975)

con = duckdb.connect(str(root / "cookiecats.duckdb"), read_only=True)
df = con.execute("select user_id, version, rounds, ret_1, ret_7, rounds_band from players").df()
con.close()
a = df[df.version == "gate_30"]          # control, the gate at level 30
b = df[df.version == "gate_40"]          # treatment, the gate moved to level 40
na, nb = len(a), len(b)


def wilson(x, n):
    p = x / n
    d = 1 + Z**2 / n
    c = (p + Z**2 / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z**2 / (4 * n**2)) / d
    return c - h, c + h


def two_prop(xa, na_, xb, nb_):
    """Gate 40 minus gate 30. Pooled z test for the p value, unpooled interval for the difference."""
    pa, pb = xa / na_, xb / nb_
    pool = (xa + xb) / (na_ + nb_)
    se0 = math.sqrt(pool * (1 - pool) * (1 / na_ + 1 / nb_))
    z = (pb - pa) / se0
    p = 2 * stats.norm.sf(abs(z))
    se1 = math.sqrt(pa * (1 - pa) / na_ + pb * (1 - pb) / nb_)
    d = pb - pa
    return dict(p_a=pa, p_b=pb, diff=d, ci_lo=d - Z * se1, ci_hi=d + Z * se1, z=z, p_value=p, rel_change=d / pa)


def holm(ps):
    order = np.argsort(ps)
    m = len(ps)
    adj = np.empty(m)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (m - rank) * ps[i])
        adj[i] = min(1.0, run)
    return adj


summary = {"n_a": na, "n_b": nb}

# 1. Sample ratio check, were players split 50/50?
exp = (na + nb) / 2
chi2 = (na - exp) ** 2 / exp + (nb - exp) ** 2 / exp
summary["srm"] = dict(share_b=nb / (na + nb), chi2=chi2, p_value=float(stats.chi2.sf(chi2, 1)))

# 2. Retention tests
rows = []
for metric, label in (("ret_7", "7-day retention"), ("ret_1", "1-day retention")):
    xa, xb = int(a[metric].sum()), int(b[metric].sum())
    r = two_prop(xa, na, xb, nb)
    lo_a, hi_a = wilson(xa, na)
    lo_b, hi_b = wilson(xb, nb)
    # bootstrap: resampling n players with replacement gives a Binomial(n, p) count
    ba = rng.binomial(na, xa / na, 20000) / na
    bb = rng.binomial(nb, xb / nb, 20000) / nb
    bd = bb - ba
    r.update(metric=metric, label=label, x_a=xa, x_b=xb, wilson_a_lo=lo_a, wilson_a_hi=hi_a, wilson_b_lo=lo_b, wilson_b_hi=hi_b,
             boot_lo=float(np.percentile(bd, 2.5)), boot_hi=float(np.percentile(bd, 97.5)))
    rows.append(r)
adj = holm([r["p_value"] for r in rows])
for r, p in zip(rows, adj):
    r["p_holm"] = float(p)
tests = pd.DataFrame(rows)
tests.to_csv(out / "out_retention_tests.csv", index=False)
summary["tests"] = {r["metric"]: r for r in rows}

# 3. Per 100,000 new players, how many fewer come back by day 7
r7 = summary["tests"]["ret_7"]
summary["per_100k"] = dict(diff=r7["diff"] * 100000, lo=r7["ci_lo"] * 100000, hi=r7["ci_hi"] * 100000)

# 4. Guardrail, rounds played
ra, rb = a.rounds.to_numpy(), b.rounds.to_numpy()
mw = stats.mannwhitneyu(ra, rb, alternative="two-sided")
boots = []
for _ in range(5000):
    boots.append(rng.choice(rb, nb).mean() - rng.choice(ra, na).mean())
top = a.rounds.idxmax()
summary["rounds"] = dict(
    mean_a=float(ra.mean()), mean_b=float(rb.mean()), median_a=float(np.median(ra)), median_b=float(np.median(rb)),
    mean_diff=float(rb.mean() - ra.mean()), boot_lo=float(np.percentile(boots, 2.5)), boot_hi=float(np.percentile(boots, 97.5)),
    mean_a_without_top=float(a.drop(top).rounds.mean()), top_player_rounds=int(a.rounds.max()),
    mean_diff_without_top=float(rb.mean() - a.drop(top).rounds.mean()),
    mw_p=float(mw.pvalue), ratio_zero_a=float((ra == 0).mean()), ratio_zero_b=float((rb == 0).mean()))

# 5. Rounds bands (descriptive, because rounds are counted over 14 days and gate 40 can change them)
brow = []
for band, g in df.groupby("rounds_band"):
    ga, gb = g[g.version == "gate_30"], g[g.version == "gate_40"]
    for metric in ("ret_7", "ret_1"):
        r = two_prop(int(ga[metric].sum()), len(ga), int(gb[metric].sum()), len(gb))
        r.update(band=band, metric=metric, n_a=len(ga), n_b=len(gb))
        brow.append(r)
bt = pd.DataFrame(brow)
bt["p_holm"] = holm(bt.p_value.to_numpy())
bt.to_csv(out / "out_band_tests.csv", index=False)
summary["bands"] = bt.to_dict("records")

# 6. Power, how big a change could this test reliably see
p0 = summary["tests"]["ret_7"]["p_a"]
n_arm = (na + nb) / 2
zb = stats.norm.ppf(0.8)


def power_at(delta, n, p=p0):
    se = math.sqrt(p * (1 - p) / n + (p + delta) * (1 - p - delta) / n)
    pool = p + delta / 2
    se0 = math.sqrt(2 * pool * (1 - pool) / n)
    return float(stats.norm.sf((Z * se0 - abs(delta)) / se) + stats.norm.cdf((-Z * se0 - abs(delta)) / se))


mde = (Z + zb) * math.sqrt(2 * p0 * (1 - p0) / n_arm)
curve = pd.DataFrame({"true_diff_pp": np.round(np.arange(0, 1.61, 0.05), 2)})
curve["power"] = [power_at(d / 100, n_arm) for d in curve.true_diff_pp]
curve.to_csv(out / "out_power_curve.csv", index=False)


def need_n(delta):
    return math.ceil(2 * ((Z + zb) ** 2) * p0 * (1 - p0) / delta**2)


sim = {}
for d in (0.4, 0.82, 1.2):
    hits = 0
    for _ in range(4000):
        xa_ = rng.binomial(na, p0)
        xb_ = rng.binomial(nb, p0 - d / 100)
        hits += two_prop(xa_, na, xb_, nb)["p_value"] < 0.05
    sim[str(d)] = hits / 4000
summary["power"] = dict(baseline=p0, n_per_arm=n_arm, mde_pp=mde * 100, simulated=sim,
                        need_n={str(d): need_n(d / 100) for d in (0.3, 0.5, 0.75, 1.0)})

# 7. Rounds histogram for the page, share of players per bucket
con = duckdb.connect()
(root / "results" / "summary.json").write_text(json.dumps(summary, indent=1, default=float))
print(json.dumps({k: summary[k] for k in ("srm", "per_100k", "power")}, indent=1, default=float))
for k, v in summary["tests"].items():
    print(k, {x: (round(y, 5) if isinstance(y, float) else y) for x, y in v.items() if x in ("p_a", "p_b", "diff", "ci_lo", "ci_hi", "p_value", "p_holm", "boot_lo", "boot_hi", "rel_change")})
print(summary["rounds"])
print(bt[["band", "metric", "diff", "ci_lo", "ci_hi", "p_value", "p_holm"]].round(5).to_string())
