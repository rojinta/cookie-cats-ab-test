"""Run the SQL, then the statistics. Usage: python3 build.py"""
import pathlib, subprocess, sys, duckdb

root = pathlib.Path(__file__).parent
con = duckdb.connect(str(root / "cookiecats.duckdb"))
for f in sorted((root / "sql").glob("*.sql")):
    con.execute(f.read_text())
    print("ran", f.name)
out = root / "results"
out.mkdir(exist_ok=True)
for (t,) in con.execute("select table_name from information_schema.tables where table_name like 'out_%' order by 1").fetchall():
    con.execute(f"copy {t} to '{out / (t + '.csv')}' (header)")
con.close()
subprocess.run([sys.executable, str(root / "analysis.py")], check=True)
