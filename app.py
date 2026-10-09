import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

import routeopt as ro

st.set_page_config(page_title="RouteOpt", page_icon="🧭", layout="wide")
st.title("RouteOpt")
st.caption("Graph-based route optimization: Dijkstra, A*, Bellman-Ford and BFS on a weighted map. "
           "PES University, Data Structures & Algorithms.")

# ------------------------------------------------------------------ sidebar
sb = st.sidebar
sb.header("Map")
rows = sb.slider("Rows", 3, 12, 6)
cols = sb.slider("Columns", 3, 12, 6)
seed = sb.number_input("Random seed", 0, 9999, 11)
drop = sb.slider("Roads removed", 0.0, 0.6, 0.25, 0.05, help="Share of horizontal roads that are missing.")


@st.cache_resource
def get_graph(r, c, s, d):
    g = ro.make_grid_graph(r, c, s, d)
    return g, ro.Trie(g.labels)


g, trie = get_graph(rows, cols, int(seed), drop)
labels = g.labels

sb.header("Search")
algo = sb.selectbox("Algorithm", list(ro.ALGORITHMS))
start = sb.selectbox("Start", range(g.n), index=0, format_func=lambda i: labels[i])
prefix = sb.text_input("Find a destination", placeholder="Type a prefix, e.g. Ca",
                       help="Autocomplete runs on a Trie.")
dest_options = trie.complete(prefix, limit=g.n) if prefix else list(range(g.n))
if not dest_options:
    sb.warning("No location starts with that prefix.")
    dest_options = list(range(g.n))
end = sb.selectbox("Destination", dest_options, index=len(dest_options) - 1, format_func=lambda i: labels[i])

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Route explorer", "Compare algorithms", "Scaling benchmark", "Traversal & DAGs", "Map analytics"])

# ------------------------------------------------------------------ route explorer
with tab1:
    res = ro.ALGORITHMS[algo](g, start, end)
    a, b, c, d = st.columns(4)
    a.metric("Nodes visited", len(res.visited))
    b.metric("Edges checked", res.edges_checked)
    c.metric("Route cost", f"{res.cost:.2f}" if res.found else "No route")
    d.metric("Stops on route", len(res.path) if res.found else 0)
    step = st.slider("Search step", 0, len(res.visited), len(res.visited),
                     help="Drag to replay the order in which the search visited nodes.")
    finished = step == len(res.visited)
    st.plotly_chart(ro.plot_graph(g, start, end, res.visited[:step], res.path if finished else (),
                                  title=f"{algo}: {labels[start]} to {labels[end]}"),
                    width="stretch")
    if res.found:
        st.write("Route: " + " → ".join(labels[i] for i in res.path))
    if algo == "BFS":
        st.info("BFS minimises the number of hops, not the weighted cost, so its route can cost more.")

# ------------------------------------------------------------------ compare
with tab2:
    st.subheader("Same start and destination, all four algorithms")
    rs = [fn(g, start, end) for fn in ro.ALGORITHMS.values()]
    df = pd.DataFrame([dict(algorithm=r.name, visited=len(r.visited), edges_checked=r.edges_checked,
                            cost=round(r.cost, 2), ms=round(r.seconds * 1000, 3), hops=len(r.path) - 1) for r in rs])
    st.dataframe(df, hide_index=True, width="stretch")
    cols4 = st.columns(3)
    for col, metric in zip(cols4, ["visited", "edges_checked", "ms"]):
        col.plotly_chart(px.bar(df, x="algorithm", y=metric, title=metric.replace("_", " "),
                                color_discrete_sequence=[ro.TEAL]), width="stretch")

    st.subheader("Averaged over random pairs")
    n_pairs = st.slider("Random start/destination pairs", 10, 300, 100, 10)

    @st.cache_data
    def effort(r, c, s, d, n):
        return pd.DataFrame(ro.pair_effort(get_graph(r, c, s, d)[0], n))

    ef = effort(rows, cols, int(seed), drop, n_pairs)
    m = st.selectbox("Metric", ["visited", "edges_checked", "ms", "cost"])
    st.plotly_chart(px.box(ef, x="algorithm", y=m, points="all", color_discrete_sequence=[ro.TEAL],
                           title=f"Distribution of {m.replace('_', ' ')} over {n_pairs} pairs"),
                    width="stretch")
    st.dataframe(ef.groupby("algorithm").mean().round(3), width="stretch")

# ------------------------------------------------------------------ scaling
with tab3:
    st.subheader("How the algorithms scale")
    st.write("Builds k × k grid graphs and runs each algorithm corner to corner. Runtime depends on your machine.")
    sides = st.multiselect("Grid side length k (nodes = k²)", [5, 10, 15, 20, 30, 40, 50, 60], default=[10, 20, 30, 40])
    reps = st.slider("Repeats (median is reported)", 1, 7, 3)
    if st.button("Run benchmark", type="primary", disabled=len(sides) < 2):
        with st.spinner("Benchmarking…"):
            st.session_state["bench"] = pd.DataFrame(ro.benchmark(sorted(sides), reps))
    if "bench" in st.session_state:
        bd = st.session_state["bench"]
        x, y = st.columns(2)
        x.plotly_chart(px.line(bd, x="nodes", y="ms", color="algorithm", markers=True, log_x=True, log_y=True,
                               title="Runtime (ms, log-log)"), width="stretch")
        y.plotly_chart(px.line(bd, x="nodes", y="visited", color="algorithm", markers=True, log_x=True, log_y=True,
                               title="Nodes visited (log-log)"), width="stretch")
        x2, y2 = st.columns(2)
        x2.plotly_chart(px.line(bd, x="nodes", y="peak_kb", color="algorithm", markers=True, log_x=True,
                                title="Peak memory (KiB)"), width="stretch")
        slopes = {a: np.polyfit(np.log(s.nodes), np.log(s.ms), 1)[0] for a, s in bd.groupby("algorithm")}
        y2.markdown("**Empirical growth exponent** (slope of runtime on a log-log plot)")
        y2.dataframe(pd.DataFrame({"algorithm": list(slopes), "exponent": [round(v, 2) for v in slopes.values()]}),
                     hide_index=True)
        st.dataframe(bd.round(3), hide_index=True, width="stretch")

# ------------------------------------------------------------------ traversal + DAG
with tab4:
    st.subheader("BFS vs DFS from the chosen start")
    l, r = st.columns(2)
    l.plotly_chart(ro.plot_order(g, ro.bfs_order(g, start), "BFS: ring by ring"), width="stretch")
    r.plotly_chart(ro.plot_order(g, ro.dfs_order(g, start), "DFS: deep first"), width="stretch")
    st.write(f"Connected components: **{len(ro.components(g))}**")

    st.subheader("Dependency ordering (topological sort and cycle detection)")
    st.caption("One task per line, written as `task: prerequisite, prerequisite`.")
    text = st.text_area("Tasks", "deploy: test, build\ntest: build\nbuild: fetch, configure\nconfigure:\nfetch:", height=150)
    deps = {}
    for line in text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            deps[k.strip()] = [p.strip() for p in v.split(",") if p.strip()]
    try:
        st.success("Order: " + " → ".join(ro.topological_sort(deps)))
    except ValueError as e:
        st.error(f"Dependency cycle: {e}")

# ------------------------------------------------------------------ map analytics
with tab5:
    st.subheader("Which locations get searched most")
    ha = st.selectbox("Algorithm", list(ro.ALGORITHMS), key="heat_algo")

    @st.cache_data
    def heat(r, c, s, d, algo):
        return ro.visit_counts(get_graph(r, c, s, d)[0], algo)

    counts, npairs = heat(rows, cols, int(seed), drop, ha)
    st.plotly_chart(ro.plot_heat(g, counts, f"Visits per location across {npairs} searches ({ha})"), width="stretch")

    st.subheader("Route quality")
    st.caption("Average % by which each algorithm's route costs more than the cheapest route, over 200 random pairs.")

    @st.cache_data
    def gaps(r, c, s, d):
        return ro.optimality_gap(get_graph(r, c, s, d)[0])

    gp = gaps(rows, cols, int(seed), drop)
    st.plotly_chart(px.bar(x=list(gp), y=list(gp.values()), labels=dict(x="algorithm", y="% over cheapest"),
                           color_discrete_sequence=[ro.TEAL]), width="stretch")

    st.subheader("The map in numbers")
    ed = g.edges
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Locations", g.n)
    m2.metric("Roads", len(ed))
    m3.metric("Roads per location", round(2 * len(ed) / g.n, 1))
    m4.metric("Components", len(ro.components(g)))
    h1, h2 = st.columns(2)
    h1.plotly_chart(px.histogram(x=[len(a) for a in g.adj], labels=dict(x="roads at a location"),
                                 color_discrete_sequence=[ro.TEAL], title="Roads per location"), width="stretch")
    h2.plotly_chart(px.histogram(x=[w for _, _, w in ed], nbins=12, labels=dict(x="road weight"),
                                 color_discrete_sequence=[ro.TEAL], title="Road weight"), width="stretch")

    st.subheader("Effort by distance")
    st.caption("Average nodes visited, grouped by hops between start and destination.")

    @st.cache_data
    def by_hops(r, c, s, d):
        return pd.DataFrame(ro.effort_by_hops(get_graph(r, c, s, d)[0]))

    bh = by_hops(rows, cols, int(seed), drop)
    st.plotly_chart(px.line(bh, x="hops", y="visited", color="algorithm", markers=True), width="stretch")

    st.subheader("A* versus Dijkstra")

    @st.cache_data
    def savings(r, c, s, d):
        return ro.astar_savings(get_graph(r, c, s, d)[0])

    sv = savings(rows, cols, int(seed), drop)
    st.write(f"On average A* visits **{np.mean(sv):.0f}%** fewer nodes than Dijkstra.")
    st.plotly_chart(px.histogram(x=sv, nbins=10, labels=dict(x="% fewer nodes visited than Dijkstra"),
                                 color_discrete_sequence=[ro.TEAL]), width="stretch")

    st.subheader("Priority queue activity")
    hs = pd.DataFrame(ro.heap_stats(g))
    q1, q2 = st.columns(2)
    q1.plotly_chart(px.bar(hs, x="algorithm", y="avg_pushes", title="Average heap pushes",
                           color_discrete_sequence=[ro.TEAL]), width="stretch")
    q2.plotly_chart(px.bar(hs, x="algorithm", y="avg_peak_heap", title="Average peak heap size",
                           color_discrete_sequence=[ro.TEAL]), width="stretch")

    st.subheader("How far is everything from the chosen start")
    cf = ro.cost_from(g, start)
    st.plotly_chart(ro.plot_heat(g, [round(v, 1) for v in cf], f"Cheapest route cost from {labels[start]}"),
                    width="stretch")

    st.subheader("Which roads carry the most routes")

    @st.cache_data
    def stats(r, c, s, d):
        return ro.route_stats(get_graph(r, c, s, d)[0])

    usage, rs_rows = stats(rows, cols, int(seed), drop)
    st.plotly_chart(ro.plot_edge_usage(g, usage, f"Roads used by {len(rs_rows)} cheapest routes"), width="stretch")
    st.caption(f"{len(g.edges) - len(usage)} roads are on no cheapest route.")

    st.subheader("Route costs")
    rdf = pd.DataFrame(rs_rows)
    k1, k2 = st.columns(2)
    k1.plotly_chart(px.histogram(rdf, x="cost", nbins=12, color_discrete_sequence=[ro.TEAL],
                                 title="Cheapest route cost, all pairs"), width="stretch")
    k2.plotly_chart(px.histogram(rdf, x="detour", nbins=12, color_discrete_sequence=[ro.TEAL],
                                 title="Route cost / straight-line distance"), width="stretch")
    st.plotly_chart(px.scatter(rdf, x="hops", y="cost", opacity=0.5, color_discrete_sequence=[ro.TEAL],
                               title="Cost against hops for every pair"), width="stretch")

    st.subheader("Which locations sit in the middle")

    @st.cache_data
    def between(r, c, s, d):
        return ro.betweenness(get_graph(r, c, s, d)[0])

    st.plotly_chart(ro.plot_heat(g, between(rows, cols, int(seed), drop), "Cheapest routes passing through each location"),
                    width="stretch")

    st.subheader("Bellman-Ford passes")

    @st.cache_data
    def passes(r, c, s, d):
        return ro.bf_passes(get_graph(r, c, s, d)[0])

    st.plotly_chart(px.histogram(x=passes(rows, cols, int(seed), drop), labels=dict(x="passes until nothing improves"),
                                 color_discrete_sequence=[ro.TEAL]), width="stretch")

    st.subheader("What if road weights vary more?")

    @st.cache_data
    def sens(r, c, s):
        return pd.DataFrame(ro.weight_sensitivity(rows=r, cols=c, seed=s))

    sd = sens(rows, cols, int(seed)).melt("spread", var_name="measure", value_name="percent")
    st.plotly_chart(px.line(sd, x="spread", y="percent", color="measure", markers=True,
                            labels=dict(spread="weight range: 0.8 to 0.8 + spread, times distance")), width="stretch")
