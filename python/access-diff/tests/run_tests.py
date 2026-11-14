#!/usr/bin/env python3
"""
run_tests.py - regression tests for access_diff.py

    python3 tests/run_tests.py SOURCE.json

SOURCE.json is one real collector output. Fixtures are generated from it into
tests/fixtures/ (they contain real names and SIDs - never share that folder).
Exit code 0 when every check passes, 1 otherwise.
"""
import csv
import json
import os
import subprocess
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "access_diff.py")
FX = os.path.join(HERE, "fixtures")

failures = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "   <- " + detail))
    if not cond:
        failures.append(name)


def run(*args):
    p = subprocess.run([sys.executable, "-I", TOOL, *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout, p.stderr


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def fx(name):
    return os.path.join(FX, name)


def outputs_for(after_name):
    stem = after_name[:-5] if after_name.lower().endswith(".json") else after_name
    return fx(stem + ".access-diff.csv"), fx(stem + ".access-diff.txt")


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    source = sys.argv[1]
    os.makedirs(FX, exist_ok=True)
    for f in os.listdir(FX):
        os.remove(os.path.join(FX, f))

    print("building fixtures from", source)
    p = subprocess.run([sys.executable, "-I", os.path.join(HERE, "make_fixtures.py"), source, FX],
                       capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        print(p.stdout, p.stderr)
        return 1
    with open(fx("expected.json"), encoding="utf-8") as fh:
        expected = json.load(fh)

    # ---- A. the main edited pair -------------------------------------------
    rc, out, err = run(fx("clean_before.json"), fx("clean_after.json"))
    csv_path, rpt_path = outputs_for("clean_after.json")
    check("A: exit code 2 (one expected warning)", rc == 2, "rc=%d" % rc)
    check("A: csv written next to AFTER", os.path.exists(csv_path))
    check("A: report written next to AFTER", os.path.exists(rpt_path))
    report = read(rpt_path) if os.path.exists(rpt_path) else ""

    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    got = Counter((r["Section"], r["Change"]) for r in rows)
    want = Counter()
    for sec, d in expected["counts"].items():
        for chg, n in d.items():
            want[(sec, chg)] = n
    check("A: csv row counts per section/change", got == want,
          "want=%s got=%s" % (dict(want), dict(got)))
    check("A: csv has exactly the expected total rows", len(rows) == sum(want.values()),
          "%d rows" % len(rows))
    check("A: csv header starts with Section,Change,Summary",
          read(csv_path).lstrip("\ufeff").startswith("Section,Change,Summary,"))
    with open(csv_path, "rb") as fh:
        raw_csv = fh.read()
    check("A: csv starts with UTF-8 BOM", raw_csv[:3] == b"\xef\xbb\xbf")
    check("A: csv uses CRLF line endings", b"\r\n" in raw_csv and b"\n" not in raw_csv.replace(b"\r\n", b""))

    for needle in expected["must_contain"]:
        check("A: report mentions %r" % needle, needle in report)
    for needle in expected["must_not_contain"]:
        check("A: report does not mention %r" % needle, needle not in report)

    changed = [r for r in rows if r["Change"] == "Changed"]
    check("A: every Changed row has Field/Before/After filled",
          all(r["Field"] and r["Before"] and r["After"] for r in changed))
    check("A: every row has an ObjectGuid", all(r["ObjectGuid"] for r in rows))
    check("A: Removed rows say FoundIn=before, Added say after",
          all(r["FoundIn"] == {"Removed": "before", "Added": "after"}.get(r["Change"], "both") for r in rows))
    dropped = expected["dropped_user_guid"]
    check("A: every row for the dropped user carries its UserGuid",
          sum(1 for r in rows if r["PrincipalGuid"] == dropped) == expected["dropped_user_rows"])
    check("A: console shows RESULT line with exit code", "Returning exit code 2" in out)
    check("A: console flags the addition as out of scope", "additions are out of scope" in out)

    # ---- B. identical content, only timestamp differs -----------------------
    rc, out, err = run(fx("clean_before.json"), fx("same_after.json"))
    check("B: exit code 0", rc == 0, "rc=%d err=%s" % (rc, err[-200:]))
    check("B: zero changes reported", "0 access removal(s), 0 addition(s), 0 change(s)" in out)
    check("B: no warnings", "No integrity warnings" in out and "WARNINGS (0)" in out)
    csv_path, _ = outputs_for("same_after.json")
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        check("B: csv has header only", len(list(csv.DictReader(fh))) == 0)

    # ---- C. different instance -> refuse -------------------------------------
    rc, out, err = run(fx("clean_before.json"), fx("other_instance.json"))
    check("C: exit code 1", rc == 1, "rc=%d" % rc)
    check("C: explains the mismatch", "Instance.InstanceGuid differs" in err and "ServerName" in err)
    check("C: tells user about --allow-mismatch", "--allow-mismatch" in err)
    check("C: nothing written", not os.path.exists(outputs_for("other_instance.json")[0]))

    # ---- D. same, but forced --------------------------------------------------
    rc, out, err = run(fx("clean_before.json"), fx("other_instance.json"), "--allow-mismatch")
    check("D: exit code 2", rc == 2, "rc=%d" % rc)
    check("D: mismatch surfaced as warning", "MISMATCH ACCEPTED" in out)

    # ---- E/F. bad input -------------------------------------------------------
    rc, out, err = run(fx("clean_before.json"), fx("broken.json"))
    check("E: broken JSON -> exit 1", rc == 1 and "not valid UTF-8 JSON" in err, "rc=%d err=%s" % (rc, err[:120]))
    rc, out, err = run(fx("clean_before.json"), fx("nope.json"))
    check("F: missing file -> exit 1", rc == 1 and "cannot read" in err, "rc=%d err=%s" % (rc, err[:120]))
    rc, out, err = run()
    check("G: no arguments -> usage, exit 2", rc == 2 and "usage:" in err)

    # ---- H. explicit output paths --------------------------------------------
    c = fx("custom.csv")
    r = fx("custom.txt")
    rc, out, err = run(fx("clean_before.json"), fx("same_after.json"), "--csv", c, "--report", r)
    check("H: --csv/--report honored", rc == 0 and os.path.exists(c) and os.path.exists(r))

    # ---- I. swapped order is detected via timestamps -------------------------
    rc, out, err = run(fx("same_after.json"), fx("clean_before.json"))
    check("I: AFTER older than BEFORE -> warning, exit 2",
          rc == 2 and "collected earlier" in out, "rc=%d" % rc)

    print()
    if failures:
        print("%d check(s) FAILED:" % len(failures))
        for f in failures:
            print("  -", f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
