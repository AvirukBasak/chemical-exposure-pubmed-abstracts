#!/usr/bin/env python3
"""Consolidate the CEI corpus into a single CSV.

One row per article: an ``article`` column (abstract text) plus one binary
(0/1) column per distinct label, named ``top/child/leaf`` with spaces replaced
by ``_``.

Source label format::

    exposure routes--oral intake--food-- AND Biomonitoring--exposure biomarker--hair nail--

becomes the columns ``exposure_routes/oral_intake/food`` and
``biomonitoring/exposure_biomarker/hair_nail``.
"""
import os

import pandas as pd

TEXT_PATH = "./data/corpus/cei/txt"
LABEL_PATH = "./data/corpus/cei/class"

name_text_files = sorted(f for f in os.listdir(TEXT_PATH) if f.endswith(".txt"))
name_label_files = sorted(f for f in os.listdir(LABEL_PATH) if f.endswith(".txt"))

assert name_text_files == name_label_files

text_files = [f"{TEXT_PATH}/{f}" for f in name_text_files]
label_files = [f"{LABEL_PATH}/{f}" for f in name_label_files]


def parse_labels(content):
    """Return every label in one class file, plus all its ancestor paths.

    A source label ``x--y--z--`` becomes ``x``, ``x/y`` and ``x/y/z``, so a
    leaf present in an article also marks its parents as present.
    """
    labels = set()
    for slot in content.split("<"):              # one slot per sentence
        slot = slot.strip()
        if not slot:
            continue
        for lab in slot.split("AND"):            # co-occurring labels
            lab = lab.strip().lower().strip("-")  # drop trailing '--'
            if not lab:
                continue
            path = lab.replace("--", "/").replace(" ", "_")
            parts = path.split("/")
            for i in range(1, len(parts) + 1):    # full path + every ancestor
                labels.add("/".join(parts[:i]))
    return labels


labels_set = set()
texts = []
labels = []  # each entry is the set of labels for one article

for text_file, label_file in zip(text_files, label_files):
    with open(text_file) as f:
        texts.append(f.read().strip())

    with open(label_file) as f:
        article_labels = parse_labels(f.read())

    labels_set.update(article_labels)
    labels.append(article_labels)

all_labels = sorted(labels_set)

rows = []
for text, article_labels in zip(texts, labels):
    row = {"article": text}
    row.update({lab: (1 if lab in article_labels else 0) for lab in all_labels})
    rows.append(row)

df = pd.DataFrame(rows, columns=["article"] + all_labels)
df.to_csv("10.6084_m9.figshare.4668229.csv", index=False)

print("articles:", len(df))
print("label columns:", len(all_labels))
print("shape:", df.shape)
print(df.iloc[:, :6])

