#!/usr/bin/env python3
"""Interactive browser for the chemical-exposure label forest.

Loads ``taxonomy.json`` (produced by ``preprocess_taxonomy.py``) and shows each
top-level component as its own tab — one tree per page. Each tree is a proper
node-link diagram (nodes as circles/squares, edges as lines) laid out as a tidy
tree, rendered with Plotly so you can pan and box-zoom from the mode bar.

Run:
    source ~/.venv/bin/activate
    streamlit run code/taxonomy_viewer.py
"""
import json
import math
import os

import plotly.graph_objects as go
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "taxonomy.json")

# one color per depth, reused cyclically (only ~5 levels here)
PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
           "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]


def load(path):
    with open(path) as f:
        return json.load(f)


def layout_tree(root):
    """Compute a tidy left-to-right layout: x = depth, y = leaf order.

    Leaves are spread by an in-order traversal (so no edges cross); each
    internal node sits vertically centered over its children.
    """
    nodes = []
    edges = []
    leaf_index = [0]

    def walk(node, depth, parent_id):
        nid = (parent_id + "/" if parent_id else "") + node["name"]
        if not node["children"]:
            y = leaf_index[0]
            leaf_index[0] += 1
        else:
            child_ys = [walk(c, depth + 1, nid) for c in node["children"]]
            y = sum(child_ys) / len(child_ys)
        nodes.append({"id": nid, "label": node["name"], "x": depth, "y": y,
                      "depth": depth, "exact": node["count"],
                      "subtree": node["subtree"]})
        if parent_id:
            edges.append((parent_id, nid))
        return y

    walk(root, 0, "")
    return nodes, edges


def build_figure(root, shape="circle", size_by_count=True):
    nodes, edges = layout_tree(root)
    coord = {n["id"]: (n["x"], n["y"]) for n in nodes}
    max_subtree = max(n["subtree"] for n in nodes)

    # edges: straight lines between parent and child
    ex, ey = [], []
    for parent_id, child_id in edges:
        px, py = coord[parent_id]
        cx, cy = coord[child_id]
        ex += [px, cx, None]
        ey += [-py, -cy, None]          # negate y so the first leaf sits on top

    edge_trace = go.Scatter(
        x=ex, y=ey, mode="lines",
        line=dict(color="#999999", width=1.2),
        hoverinfo="skip", showlegend=False,
    )

    if size_by_count:
        size = [10 + 26 * (math.log1p(n["subtree"]) / math.log1p(max_subtree))
                for n in nodes]
    else:
        size = [14] * len(nodes)

    node_trace = go.Scatter(
        x=[n["x"] for n in nodes],
        y=[-n["y"] for n in nodes],
        mode="markers+text",
        text=[n["label"] for n in nodes],
        textposition="middle right",
        textfont=dict(size=11),
        marker=dict(
            symbol=shape,
            size=size,
            color=[PALETTE[n["depth"] % len(PALETTE)] for n in nodes],
            line=dict(color="white", width=1.5),
        ),
        customdata=[[n["exact"], n["subtree"], n["depth"]] for n in nodes],
        hovertemplate=(
            "<b>%{text}</b><br>"
            "exact: %{customdata[0]}<br>"
            "subtree: %{customdata[1]}<br>"
            "level: %{customdata[2]}<extra></extra>"
        ),
        showlegend=False,
    )

    max_depth = max(n["depth"] for n in nodes)
    fig = go.Figure([edge_trace, node_trace])
    fig.update_layout(
        title=dict(text=root["name"], x=0.01),
        margin=dict(l=20, r=160, t=40, b=20),
        height=760,
    )
    fig.update_xaxes(visible=False, range=[-0.2, max_depth + 1.8])
    fig.update_yaxes(visible=False)
    return fig


def level_counts(root):
    counts = {}

    def walk(node, depth):
        counts[depth] = counts.get(depth, 0) + 1
        for child in node["children"]:
            walk(child, depth + 1)

    walk(root, 1)
    return counts


def node_count(root):
    return 1 + sum(node_count(c) for c in root["children"])


def main():
    st.set_page_config(page_title="CEI taxonomy", layout="wide")
    st.title("Chemical-exposure label taxonomy")

    if not os.path.exists(DATA):
        st.error("Missing %s — run:  python code/preprocess_taxonomy.py" % DATA)
        return

    data = load(DATA)
    roots = data["forest"]

    st.caption(
        "%d abstracts · %d label occurrences · %d top-level components (a forest, no single root)"
        % (data["num_abstracts"], data["num_label_occurrences"],
           data["num_top_level_components"])
    )

    with st.sidebar:
        st.subheader("Display")
        shape = st.radio("Node shape", ["circle", "square"], horizontal=True)
        size_by_count = st.checkbox("Scale node size by subtree count", value=True)
        st.caption("color = level (depth)")

    tabs = st.tabs(["Overview"] + [r["name"] for r in roots])

    with tabs[0]:
        st.subheader("Components")
        rows = []
        for r in roots:
            lc = level_counts(r)
            rows.append({
                "component": r["name"],
                "nodes": node_count(r),
                "depth": max(lc),
                "labeled occurrences (subtree)": r["subtree"],
                "nodes per level": " · ".join("L%d:%d" % (k, lc[k]) for k in sorted(lc)),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption("exact = sentences tagged with this node only · "
                   "subtree = this node plus all descendants")

    for tab, root in zip(tabs[1:], roots):
        with tab:
            lc = level_counts(root)
            st.caption("nodes per level: " + "  ·  ".join(
                "level %d = %d" % (k, lc[k]) for k in sorted(lc)))
            st.plotly_chart(
                build_figure(root, shape=shape, size_by_count=size_by_count),
                use_container_width=True,
            )


if __name__ == "__main__":
    main()
