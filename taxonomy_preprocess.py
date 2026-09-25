#!/usr/bin/env python3
"""Build a single taxonomy data file from the gold-standard labels.

This release ships no ``labels.txt``, so the label tree has to be rebuilt from
the annotations themselves. Every ``corpus/cei/class/*.txt`` holds the
sentence-aligned gold labels for one abstract, encoded as ``<``-delimited slots
with ``--`` as the hierarchy separator and ``AND`` joining co-occurring labels.

This script reconstructs the label forest (there is no single root — the
top-level concepts form a forest of independent components) and writes one
JSON file that the interactive viewer can load instantly.

Usage:
    python preprocess_taxonomy.py [out.json]

Defaults to writing ``taxonomy.json`` next to this script.
"""
import glob
import json
import os

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "corpus", "cei", "class")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "taxonomy.json")


def clean_segments(label):
    """'Biomonitoring--exposure biomarker--blood--' -> ['biomonitoring', ...]."""
    s = label.strip().lower().strip("-")          # drop whitespace + trailing '--'
    if not s:
        return None
    segs = [p.strip() for p in s.split("--")]
    segs = [p for p in segs if p]                  # drop any empty segment
    return segs or None


def add_path(forest, segs):
    """Add one label path to the nested forest dict, bumping counts."""
    node = forest
    for i, name in enumerate(segs):
        child = node.get(name)
        if child is None:
            child = {"name": name, "count": 0, "subtree": 0, "children": {}}
            node[name] = child
        child["subtree"] += 1                       # this path *or any descendant*
        if i == len(segs) - 1:
            child["count"] += 1                     # this exact label (leaf)
        node = child["children"]


def finalize(d):
    """Sort children alphabetically and convert nested dicts -> lists."""
    return {
        "name": d["name"],
        "count": d["count"],
        "subtree": d["subtree"],
        "children": [finalize(d["children"][k]) for k in sorted(d["children"])],
    }


def node_count(node):
    return 1 + sum(node_count(c) for c in node["children"])


def max_depth(node, d=1):
    if not node["children"]:
        return d
    return max(max_depth(c, d + 1) for c in node["children"])


def main():
    out = sys_argv_out()
    forest = {}
    n_abs = 0
    n_labels = 0

    for path in sorted(glob.glob(os.path.join(CORPUS, "*.txt"))):
        n_abs += 1
        text = open(path).read().strip()
        for slot in text.split("<"):                # one slot per sentence
            slot = slot.strip()
            if not slot:
                continue
            for part in slot.split("AND"):          # multi-label sentence
                segs = clean_segments(part)
                if segs is None:
                    continue
                add_path(forest, segs)
                n_labels += 1

    roots = [finalize(forest[k]) for k in sorted(forest)]

    data = {
        "generated_from": os.path.relpath(CORPUS, os.path.dirname(os.path.abspath(__file__))),
        "num_abstracts": n_abs,
        "num_label_occurrences": n_labels,
        "num_top_level_components": len(roots),
        "forest": roots,
    }

    with open(out, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("wrote %s" % out)
    print("abstracts: %d   label occurrences: %d   top-level components: %d"
          % (n_abs, n_labels, len(roots)))
    for r in roots:
        print("  - %-22s nodes=%3d  depth=%d  subtree=%d"
              % (r["name"], node_count(r), max_depth(r), r["subtree"]))


def sys_argv_out():
    import sys
    if len(sys.argv) > 1:
        return os.path.abspath(sys.argv[1])
    return OUT


if __name__ == "__main__":
    main()
