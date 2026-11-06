"""Fill the numbers into page/template.html and write index.html (standalone page). Usage: python3 page/assemble.py
Also writes page/artifact.html, the same page without the html and head wrapper."""
import json, pathlib, re
import pandas as pd

root = pathlib.Path(__file__).parent.parent
S = json.loads((root / "results" / "summary.json").read_text())
hist = pd.read_csv(root / "results" / "out_rounds_hist.csv")
curve = pd.read_csv(root / "results" / "out_power_curve.csv")
band_pct = pd.read_csv(root / "results" / "out_by_band.csv")
val = (root / "results" / "validation.txt").read_text() if (root / "results" / "validation.txt").exists() else ""
m = re.search(r"(\d+) of (\d+) comparisons match", val)
checks = m.group(1) if m and m.group(1) == m.group(2) else "all"

T7, T1, R, P = S["tests"]["ret_7"], S["tests"]["ret_1"], S["rounds"], S["power"]


def sg(x, d=2):
    return ("−" if x < 0 else "+") + f"{abs(x):.{d}f}"


def pf(p):
    if p < 0.001:
        return "<0.001"
    if p < 0.01:
        return f"{p:.4f}"
    return f"{p:.3f}"


def r100(x):
    return f"{int(round(x, -2)):,}"


def r10(x):
    return f"{int(round(abs(x), -1)):,}"


band = next(b for b in S["bands"] if b["band"] == "30 to 99 rounds" and b["metric"] == "ret_7")
bp = band_pct[band_pct.rounds_band == "30 to 99 rounds"].set_index("version")
K = dict(
    n_total=f"{S['n_a'] + S['n_b']:,}", na=f"{S['n_a']:,}", nb=f"{S['n_b']:,}", n_arm=r100(P["n_per_arm"]),
    ret7a=f"{T7['p_a'] * 100:.1f}%", ret7b=f"{T7['p_b'] * 100:.1f}%", ret1a=f"{T1['p_a'] * 100:.1f}%", ret1b=f"{T1['p_b'] * 100:.1f}%",
    d7=sg(T7["diff"] * 100), lo7=sg(T7["ci_lo"] * 100), hi7=sg(T7["ci_hi"] * 100), d7abs=f"{abs(T7['diff']) * 100:.2f}",
    rel7=f"{abs(T7['rel_change']) * 100:.1f}%",
    per100k=r10(S["per_100k"]["diff"]), per100k_lo=r10(S["per_100k"]["hi"]), per100k_hi=r10(S["per_100k"]["lo"]),
    p7=pf(T7["p_value"]), p7h=pf(T7["p_holm"]), p7_once=f"{int(round(1 / T7['p_value'], -1)):,}",
    d1=sg(T1["diff"] * 100), lo1=sg(T1["ci_lo"] * 100), hi1=sg(T1["ci_hi"] * 100), p1=pf(T1["p_value"]), p1h=pf(T1["p_holm"]),
    boot_n="20,000",
    b_d_abs=f"{abs(band['diff']) * 100:.2f}", b_a=f"{bp.loc['gate_30', 'ret_7_pct']:.1f}%", b_b=f"{bp.loc['gate_40', 'ret_7_pct']:.1f}%", b_p=pf(band["p_holm"]),
    med_a=f"{R['median_a']:.0f}", med_b=f"{R['median_b']:.0f}", mean_a=f"{R['mean_a']:.1f}", mean_b=f"{R['mean_b']:.1f}",
    top_player=f"{R['top_player_rounds']:,}", mean_gap_wo=f"{abs(R['mean_diff_without_top']):.2f}", mw_p=pf(R["mw_p"]),
    mean_gap=sg(R["mean_diff"]), mean_lo=sg(R["boot_lo"]), mean_hi=sg(R["boot_hi"]),
    mde=f"{P['mde_pp']:.2f}", need05=r100(P["need_n"]["0.5"]), need03=r100(P["need_n"]["0.3"]),
    share_b=f"{S['srm']['share_b'] * 100:.1f}%", srm_p=pf(S["srm"]["p_value"]), checks=checks,
)
data = dict(n_a=S["n_a"], n_b=S["n_b"], tests=S["tests"], bands=S["bands"], power=S["power"],
            curve=curve.to_dict("records"), hist=hist.to_dict("records"))

html = (root / "page" / "template.html").read_text()
html = html.replace("__DATA__", json.dumps(data, default=float))
for k, v in K.items():
    html = html.replace("{{" + k + "}}", v)
left = re.findall(r"\{\{(\w+)\}\}", html)
assert not left, left
(root / "page" / "artifact.html").write_text(html)
head, body = html.split('<div class="wrap">', 1)
page = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        + head + '</head><body>\n<div class="wrap">' + body + "</body></html>\n")
(root / "index.html").write_text(page)
print("wrote index.html", len(page), "bytes", K["p7"], K["p7h"], K["per100k"], K["b_p"])
