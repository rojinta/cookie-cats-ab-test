# Cookie Cats A/B test analysis

**Question.** In the mobile game Cookie Cats, players reach a gate that makes them wait or pay before continuing. The studio tested moving the first gate from level 30 to level 40. Did that change how many players come back?

**Answer.** Yes. Moving the gate to level 40 lowered 7-day retention from 19.0% to 18.2%, a drop of 0.82 percentage points (95% interval 0.31 to 1.33), or about 820 fewer returning players for every 100,000 installs. Keep the gate at level 30. Day-1 retention leaned lower too, but its interval includes zero.

Dashboard: [Cookie Cats Gate Test](https://rojinta.github.io/cookie-cats-ab-test/)

## What is in this repo

| Path | What it does |
|---|---|
| `sql/01_clean.sql` | Types the raw file into one row per player and runs data quality checks |
| `sql/02_results.sql` | Per-version summaries, rounds bands, rounds histogram |
| `analysis.py` | Split check, two-proportion tests, resampled intervals, rank test for rounds, Holm adjustment, power analysis by formula and simulation |
| `build.py` | Runs the SQL, then `analysis.py`, and writes `results/` |
| `validate.py` | Recomputes every reported figure with different code (pandas, statsmodels, a permutation test). 45 of 45 comparisons match |
| `page/` | Source for the write-up page. `python3 page/assemble.py` rebuilds `index.html` |
| `results/` | Output tables and `summary.json` |
| `data/` | Where the raw file goes (see `data/README.md`) |

## How the test was read

The plan was fixed before looking at results.

- **Main measure:** 7-day retention, the share of players who open the game again 7 days after install.
- **Secondary measure:** 1-day retention.
- **Check:** rounds played in the first 14 days, to see whether the later gate changed how much people play.
- **Tests:** a two-proportion z-test for retention, intervals from resampling 20,000 times, Holm adjustment across the two retention measures, a rank test for rounds.
- **Power:** the test can reliably detect a change of about 0.73 points. Detecting 0.5 points takes about 96,700 players per group.

## Things that limit the conclusion

- Gate 40 received 50.4% of players instead of 50% (p = 0.0086). That is mild, but the dataset has no assignment log to explain it.
- The only outcome is retention. There is no revenue or ad data, so the trade-off a later gate might buy is not measured.
- Retention is measured at day 1 and day 7 only.
- The rounds-played groups are formed after the gate can change behavior, so they show where the drop appears but do not prove why.
- One player in gate 30 logged 49,854 rounds. Retention is unaffected, and the rounds comparison uses a rank test and a version without that player.
- This is an analysis of a past experiment, not a test run by the author.

## Run it

```
pip install -r requirements.txt
# put cookie_cats.csv in data/raw/ (see data/README.md)
python3 build.py
python3 validate.py
python3 page/assemble.py
```

## Data

Cookie Cats A/B test data, published on Kaggle as "Mobile Games A/B Testing". The raw file is not included here. Check the dataset page for its licence.
