#!/usr/bin/env python3
"""Summarize a Morphorm optimizer diagnostics file (for example morphorm_oc_optimizer_diagnostics.txt) as JSON.

Usage:  python3 diag_summary.py DIAGNOSTICS.txt [--rows N] [--compare-first-to VALUE]

Reports the column header, the number of iteration rows, the first and last iteration numbers with their objective
values (column F(X) when present, else the 3rd column), and the last N rows (default 3). Lines that are not
numeric iteration rows (headers, messages) are listed separately so stop reasons are not missed.

--compare-first-to VALUE prints the relative difference between the first row's objective and VALUE. Use it after
a restart: the first objective of a continued run should equal the last objective of the run it continues.
Standard library only.
"""
import json
import re
import sys

ROW = re.compile(r"^\s*(\d+)\s+(\d+)\s+([-+0-9.eE]+)")


def summarize(path, nrows=3):
    header, rows, other = None, [], []
    for line in open(path, errors="replace"):
        s = line.rstrip("\n")
        if not s.strip():
            continue
        m = ROW.match(s)
        if m:
            rows.append((int(m.group(1)), s.split()))
        elif header is None and re.search(r"Iter", s):
            header = s.split()
        else:
            other.append(s.strip())
    col = header.index("F(X)") if header and "F(X)" in header else 2
    obj = lambda r: float(r[1][col]) if len(r[1]) > col else None
    rep = {"file": path, "header": header, "iteration_rows": len(rows)}
    if rows:
        rep.update({"first_iter": rows[0][0], "first_objective": obj(rows[0]), "last_iter": rows[-1][0],
                    "last_objective": obj(rows[-1]), "last_rows": [" ".join(r[1]) for r in rows[-nrows:]]})
    rep["non_row_lines"] = other[:20]
    return rep


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    args = sys.argv[1:]
    n = int(args[args.index("--rows") + 1]) if "--rows" in args else 3
    rep = summarize(args[0], n)
    if "--compare-first-to" in args and rep.get("first_objective") is not None:
        v = float(args[args.index("--compare-first-to") + 1])
        rep["first_vs_given_rel_diff"] = abs(rep["first_objective"] - v) / max(abs(v), 1e-300)
    print(json.dumps(rep, indent=1))
