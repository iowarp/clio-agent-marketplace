#!/usr/bin/env python3
"""List the settings XMLGenerator actually wrote, so a deck can be checked against its generated configuration.

Usage:  python3 xml_params.py GENERATED_DIR_OR_XML [NAME_SUBSTRING ...]

Prints one line per <Parameter name=... value=...> (and per simple <Tag>value</Tag> element) found in each *.xml
file: file, path of enclosing ParameterList/elements, name, value. With NAME_SUBSTRING arguments only matching
names are printed (case-insensitive), and every requested substring that matched nothing is reported as MISSING
on stderr with exit code 1. Files that are not well-formed XML are reported as UNPARSABLE on
stderr and skipped. A setting that is in the deck but missing here was not applied.
Standard library only.
"""
import glob
import os
import sys
import xml.etree.ElementTree as ET


def walk(el, path, out, fname):
    tag = el.tag
    name = el.get("name")
    here = path + [name or tag]
    if tag == "Parameter" and name is not None:
        out.append((fname, "/".join(path[-3:]), name, el.get("value", "")))
    elif len(el) == 0 and (el.text or "").strip():
        out.append((fname, "/".join(path[-3:]), tag, el.text.strip()))
    for c in el:
        walk(c, here, out, fname)


def main(argv):
    if not argv:
        sys.exit(__doc__)
    target, wants = argv[0], [w.lower() for w in argv[1:]]
    files = sorted(glob.glob(os.path.join(target, "*.xml"))) if os.path.isdir(target) else [target]
    rows = []
    for f in files:
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            # XMLGenerator files can hold several top-level elements; wrap them
            try:
                root = ET.fromstring("<root>" + open(f, errors="replace").read().split("?>", 1)[-1] + "</root>")
            except ET.ParseError as e:
                print(f"UNPARSABLE\t{os.path.basename(f)}\t{e}", file=sys.stderr)
                continue
        walk(root, [], rows, os.path.basename(f))
    hit = set()
    for f, p, n, v in rows:
        if not wants or any(w in n.lower() for w in wants):
            hit |= {w for w in wants if w in n.lower()}
            print(f"{f}\t{p}\t{n}\t{v}")
    missing = [w for w in wants if w not in hit]
    for w in missing:
        print(f"MISSING\t{w}", file=sys.stderr)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
