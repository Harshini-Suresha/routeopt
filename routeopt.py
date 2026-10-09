"""RouteOpt core: weighted graph, shortest-path algorithms, traversal, Trie and benchmarking."""
from __future__ import annotations

import heapq
import math
import random
import statistics
import time
import tracemalloc
from collections import deque
from dataclasses import dataclass

NAMES = ["Harbour Gate", "Mill Lane", "Old Market", "Canal Street", "Station Square", "Library",
         "Clock Tower", "Botanic Garden", "Riverside", "Fort Road", "Orchard Hill", "Chapel Yard",
         "Bridge End", "Foundry", "Granary", "Hospital", "Ironworks", "Junction", "Kiln Row",
         "Lantern Court", "Museum", "North Gate", "Observatory", "Parkside", "Quarry Bend",
         "Rose Court", "South Quay", "Tannery", "University", "Viaduct", "Wharf", "Yew Tree",
         "Zenith Plaza", "Abbey", "Brook End", "Cathedral",
         "Alder Gate", "Birch Crescent", "Cedar Wharf", "Dove Lane", "Elder Court", "Fern Hollow",
         "Grove End", "Hazel Drive", "Ivy Terrace", "Juniper Row", "Acorn Way", "Beechwood",
         "Chestnut Hill", "Dogwood", "Elm Park", "Fig Orchard", "Gorse Field", "Holly Bank",
         "Iris Meadow", "Jasmine Walk", "Kingfisher Quay", "Larkspur Lane", "Magnolia Court", "Nettlebed",
         "Oakenshaw", "Primrose Hill", "Quince Orchard", "Rowan Gate", "Sycamore", "Thistledown",
         "Umber Quay", "Vetch Field", "Willowbank", "Yarrow", "Amberley", "Brambletye",
         "Copperfield", "Dunmore", "Easthaven", "Foxglove", "Goldcrest", "Heathfield",
         "Inkwell", "Jubilee", "Kestrel Rise", "Linen Yard", "Marlowe", "Netherby",
         "Osprey Point", "Plover Court", "Quartz Row", "Ravenscar", "Saltmarsh", "Tidewater",
         "Upton", "Valve House", "Wexford", "Xylon", "Yarmouth", "Zennor",
         "Ashcombe", "Blackfriars", "Crows Nest", "Dovecote"]
TEAL, AMBER, ROUTE, INK, EDGE = "#0E7C86", "#E9A23B", "#C81E5A", "#14232D", "#B3C2CB"


# ---------------------------------------------------------------- graph
@dataclass
class Graph:
    pos: list   # (x, y) per node
    adj: list   # adjacency lists: adj[u] = [(v, weight), ...]

    @property
    def n(self):
        return len(self.pos)

    @property
    def edges(self):
        return [(u, v, w) for u in range(self.n) for v, w in self.adj[u] if u < v]

    @property
    def labels(self):
        return [NAMES[i] if i < len(NAMES) else f"Node {i}" for i in range(self.n)]


def make_grid_graph(rows=6, cols=6, seed=11, drop=0.25, diag=0.3, spread=0.6) -> Graph:
    """Jittered grid map. Weights are 0.8x to 1.4x the straight-line distance, so
    0.8 * Euclidean distance is an admissible, consistent A* heuristic."""
    rng = random.Random(seed)
    pos = [(c + rng.uniform(-.38, .38), r + rng.uniform(-.45, .45)) for r in range(rows) for c in range(cols)]
    adj = [[] for _ in pos]

    def link(a, b):
        w = math.dist(pos[a], pos[b]) * rng.uniform(.8, .8 + spread)
        adj[a].append((b, w))
        adj[b].append((a, w))

    for i in range(rows * cols):
        r, c = divmod(i, cols)
        if c < cols - 1 and (r == 0 or rng.random() > drop):
            link(i, i + 1)
        if r < rows - 1:
            link(i, i + cols)          # all vertical edges + top row keep the graph connected
        if r < rows - 1 and c < cols - 1 and rng.random() < diag:
            link(i, i + cols + 1)
        if r < rows - 1 and c > 0 and rng.random() < diag * .67:
            link(i, i + cols - 1)
    return Graph(pos, adj)


# ---------------------------------------------------------------- shortest paths
@dataclass
class Result:
    name: str
    path: list
    cost: float
    visited: list          # nodes in the order the search touched them
    edges_checked: int
    seconds: float
    pushes: int = 0        # heap pushes (Dijkstra, A*)
    peak_heap: int = 0     # largest heap size reached
    passes: int = 0        # Bellman-Ford passes over all edges

    @property
    def found(self):
        return bool(self.path)


def _finish(name, g, order, edges, prev, s, t, t0):
    secs = time.perf_counter() - t0
    path, v = [], t
    while v != -1:
        path.append(v)
        if v == s:
            break
        v = prev[v]
    path.reverse()
    if not path or path[0] != s:
        path = []
    cost = sum(dict(g.adj[a])[b] for a, b in zip(path, path[1:]))
    return Result(name, path, cost, order, edges, secs)


def _best_first(g, s, t, use_h, name):
    t0 = time.perf_counter()
    h = (lambda n: 0.8 * math.dist(g.pos[n], g.pos[t])) if use_h else (lambda n: 0.0)
    dist, prev = [math.inf] * g.n, [-1] * g.n
    dist[s], done, order, edges = 0.0, set(), [], 0
    heap = [(h(s), s)]                       # binary heap (heapq)
    pushes, peak = 1, 1
    while heap:
        _, u = heapq.heappop(heap)
        if u in done:
            continue
        done.add(u)
        order.append(u)
        if u == t:
            break
        for v, w in g.adj[u]:
            edges += 1
            nd = dist[u] + w
            if nd < dist[v]:
                dist[v], prev[v] = nd, u
                heapq.heappush(heap, (nd + h(v), v))
                pushes += 1
                peak = max(peak, len(heap))
    r = _finish(name, g, order, edges, prev, s, t, t0)
    r.pushes, r.peak_heap = pushes, peak
    return r


def dijkstra(g, s, t):
    return _best_first(g, s, t, False, "Dijkstra")


def astar(g, s, t):
    return _best_first(g, s, t, True, "A*")


def bellman_ford(g, s, t):
    t0 = time.perf_counter()
    dist, prev = [math.inf] * g.n, [-1] * g.n
    dist[s], seen, order, edges = 0.0, {s}, [s], 0
    passes = 0
    for _ in range(g.n - 1):
        passes += 1
        changed = False
        for u in range(g.n):
            if dist[u] == math.inf:
                continue
            for v, w in g.adj[u]:
                edges += 1
                if dist[u] + w < dist[v]:
                    dist[v], prev[v], changed = dist[u] + w, u, True
                    if v not in seen:
                        seen.add(v)
                        order.append(v)
        if not changed:
            break
    r = _finish("Bellman-Ford", g, order, edges, prev, s, t, t0)
    r.passes = passes
    return r


def bfs(g, s, t):
    """Fewest hops, ignoring weights."""
    t0 = time.perf_counter()
    prev, seen, q, order, edges = [-1] * g.n, {s}, deque([s]), [], 0
    while q:
        u = q.popleft()
        order.append(u)
        if u == t:
            break
        for v, _ in g.adj[u]:
            edges += 1
            if v not in seen:
                seen.add(v)
                prev[v] = u
                q.append(v)
    return _finish("BFS", g, order, edges, prev, s, t, t0)


ALGORITHMS = {"Dijkstra": dijkstra, "A*": astar, "Bellman-Ford": bellman_ford, "BFS": bfs}


# ---------------------------------------------------------------- traversal, DAGs
def bfs_order(g, s):
    seen, q, out = {s}, deque([s]), []
    while q:
        u = q.popleft()
        out.append(u)
        for v, _ in g.adj[u]:
            if v not in seen:
                seen.add(v)
                q.append(v)
    return out


def dfs_order(g, s):
    seen, stack, out = set(), [s], []
    while stack:
        u = stack.pop()
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
        stack.extend(v for v, _ in reversed(g.adj[u]) if v not in seen)
    return out


def components(g):
    seen, comps = set(), []
    for s in range(g.n):
        if s not in seen:
            comp = bfs_order(g, s)
            seen.update(comp)
            comps.append(comp)
    return comps


def topological_sort(deps: dict):
    """deps maps task -> list of prerequisites. Kahn's algorithm; raises ValueError on a cycle."""
    nodes = set(deps) | {p for ps in deps.values() for p in ps}
    waiting = {n: set(deps.get(n, [])) for n in nodes}
    children = {n: [] for n in nodes}
    for n, ps in waiting.items():
        for p in ps:
            children[p].append(n)
    ready, out = sorted(n for n, ps in waiting.items() if not ps), []
    while ready:
        n = ready.pop(0)
        out.append(n)
        for c in sorted(children[n]):
            waiting[c].discard(n)
            if not waiting[c]:
                ready.append(c)
    if len(out) < len(nodes):
        raise ValueError("cycle among: " + ", ".join(sorted(nodes - set(out))))
    return out


def has_cycle(deps: dict) -> bool:
    try:
        topological_sort(deps)
        return False
    except ValueError:
        return True


# ---------------------------------------------------------------- Trie autocomplete
class Trie:
    def __init__(self, words=()):
        self.root = {}
        for i, w in enumerate(words):
            self.insert(w, i)

    def insert(self, word, value):
        node = self.root
        for ch in word.lower():
            node = node.setdefault(ch, {})
        node.setdefault("$", []).append(value)

    def complete(self, prefix, limit=8):
        node = self.root
        for ch in prefix.lower():
            if ch not in node:
                return []
            node = node[ch]
        out = []

        def walk(n):
            if len(out) >= limit:
                return
            out.extend(n.get("$", []))
            for ch in sorted(k for k in n if k != "$"):
                walk(n[ch])

        walk(node)
        return out[:limit]


# ---------------------------------------------------------------- benchmarking
def benchmark(sides=(10, 20, 30, 40), repeats=3, seed=5):
    """Corner-to-corner searches on k x k grids: median runtime, nodes visited, peak memory."""
    rows = []
    for k in sides:
        g = make_grid_graph(k, k, seed)
        s, t = 0, g.n - 1
        for name, fn in ALGORITHMS.items():
            runs = [fn(g, s, t) for _ in range(repeats)]
            tracemalloc.start()
            fn(g, s, t)
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            r = runs[-1]
            rows.append(dict(nodes=g.n, algorithm=name, ms=1000 * statistics.median(x.seconds for x in runs),
                             visited=len(r.visited), edges_checked=r.edges_checked,
                             peak_kb=peak / 1024, cost=r.cost))
    return rows


def pair_effort(g, n_pairs=100, seed=1):
    """Run every algorithm on random start/destination pairs."""
    rng, rows = random.Random(seed), []
    for _ in range(n_pairs):
        s, t = rng.sample(range(g.n), 2)
        for name, fn in ALGORITHMS.items():
            r = fn(g, s, t)
            rows.append(dict(algorithm=name, visited=len(r.visited), edges_checked=r.edges_checked,
                             ms=1000 * r.seconds, cost=r.cost))
    return rows


def visit_counts(g, algo="Dijkstra", max_pairs=400, seed=1):
    """How often each location is visited when searching every pair (or a random sample of pairs)."""
    allp = [(s, t) for s in range(g.n) for t in range(s + 1, g.n)]
    pairs = allp if len(allp) <= max_pairs else random.Random(seed).sample(allp, max_pairs)
    counts, fn = [0] * g.n, ALGORITHMS[algo]
    for s, t in pairs:
        for v in fn(g, s, t).visited:
            counts[v] += 1
    return counts, len(pairs)


def optimality_gap(g, n_pairs=200, seed=1):
    """Average % by which each algorithm's route costs more than the cheapest route."""
    rng, tot = random.Random(seed), {k: 0.0 for k in ALGORITHMS}
    for _ in range(n_pairs):
        s, t = rng.sample(range(g.n), 2)
        base = dijkstra(g, s, t).cost
        for k, fn in ALGORITHMS.items():
            tot[k] += fn(g, s, t).cost / base
    return {k: 100 * (v / n_pairs - 1) for k, v in tot.items()}


def effort_by_hops(g, max_pairs=500, seed=1):
    """Average nodes visited, grouped by the hop distance between start and destination."""
    allp = [(s, t) for s in range(g.n) for t in range(s + 1, g.n)]
    pairs = allp if len(allp) <= max_pairs else random.Random(seed).sample(allp, max_pairs)
    acc = {}
    for s, t in pairs:
        hops = len(bfs(g, s, t).path) - 1
        for name, fn in ALGORITHMS.items():
            acc.setdefault((hops, name), []).append(len(fn(g, s, t).visited))
    return [dict(hops=h, algorithm=a, visited=sum(v) / len(v), pairs=len(v)) for (h, a), v in sorted(acc.items())]


def astar_savings(g, n_pairs=300, seed=1):
    """For random pairs: % fewer nodes A* visits than Dijkstra."""
    rng, out = random.Random(seed), []
    for _ in range(n_pairs):
        s, t = rng.sample(range(g.n), 2)
        out.append(100 * (1 - len(astar(g, s, t).visited) / len(dijkstra(g, s, t).visited)))
    return out


def heap_stats(g, n_pairs=200, seed=1):
    """Average heap pushes and peak heap size for Dijkstra and A*."""
    rng, rows = random.Random(seed), {"Dijkstra": [0, 0], "A*": [0, 0]}
    for _ in range(n_pairs):
        s, t = rng.sample(range(g.n), 2)
        for name, fn in (("Dijkstra", dijkstra), ("A*", astar)):
            r = fn(g, s, t)
            rows[name][0] += r.pushes
            rows[name][1] += r.peak_heap
    return [dict(algorithm=k, avg_pushes=v[0] / n_pairs, avg_peak_heap=v[1] / n_pairs) for k, v in rows.items()]


def cost_from(g, s):
    """Cheapest route cost from s to every node (Dijkstra without a target)."""
    dist, heap = [math.inf] * g.n, [(0.0, s)]
    dist[s] = 0.0
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v, w in g.adj[u]:
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(heap, (dist[v], v))
    return dist


def route_stats(g, max_pairs=600, seed=1):
    """Cheapest routes for many pairs: how often each road is used, plus cost, hops and detour per pair."""
    allp = [(s, t) for s in range(g.n) for t in range(s + 1, g.n)]
    pairs = allp if len(allp) <= max_pairs else random.Random(seed).sample(allp, max_pairs)
    usage, rows = {}, []
    for s, t in pairs:
        r = dijkstra(g, s, t)
        for a, b in zip(r.path, r.path[1:]):
            usage[(min(a, b), max(a, b))] = usage.get((min(a, b), max(a, b)), 0) + 1
        straight = math.dist(g.pos[s], g.pos[t])
        rows.append(dict(cost=r.cost, hops=len(r.path) - 1, straight=straight, detour=r.cost / straight))
    return usage, rows


def betweenness(g, max_pairs=600, seed=1):
    """How many cheapest routes pass through each location (as an intermediate stop)."""
    allp = [(s, t) for s in range(g.n) for t in range(s + 1, g.n)]
    pairs = allp if len(allp) <= max_pairs else random.Random(seed).sample(allp, max_pairs)
    counts = [0] * g.n
    for s, t in pairs:
        for v in dijkstra(g, s, t).path[1:-1]:
            counts[v] += 1
    return counts


def bf_passes(g, max_pairs=300, seed=1):
    """Passes Bellman-Ford needs before nothing improves, for many pairs."""
    allp = [(s, t) for s in range(g.n) for t in range(s + 1, g.n)]
    pairs = allp if len(allp) <= max_pairs else random.Random(seed).sample(allp, max_pairs)
    return [bellman_ford(g, s, t).passes for s, t in pairs]


def weight_sensitivity(spreads=(0, .3, .6, .9, 1.2), rows=6, cols=6, seed=11, n_pairs=300):
    """Rebuild the map with wider road-weight ranges (0.8 to 0.8+spread times distance)."""
    out = []
    for sp in spreads:
        g = make_grid_graph(rows, cols, seed, spread=sp)
        rng, gap, sav = random.Random(1), 0.0, 0.0
        for _ in range(n_pairs):
            s, t = rng.sample(range(g.n), 2)
            d = dijkstra(g, s, t)
            gap += bfs(g, s, t).cost / d.cost
            sav += 1 - len(astar(g, s, t).visited) / len(d.visited)
        out.append(dict(spread=sp, bfs_extra_cost_pct=100 * (gap / n_pairs - 1), astar_fewer_nodes_pct=100 * sav / n_pairs))
    return out


# ---------------------------------------------------------------- plotting (plotly)
def _base(g, height):
    import plotly.graph_objects as go
    X, Y = [p[0] for p in g.pos], [-p[1] for p in g.pos]
    ex, ey = [], []
    for u, v, _ in g.edges:
        ex += [X[u], X[v], None]
        ey += [Y[u], Y[v], None]
    fig = go.Figure(go.Scatter(x=ex, y=ey, mode="lines", line=dict(color=EDGE, width=1.5), hoverinfo="skip"))
    fig.update_layout(template="plotly_white", showlegend=False, height=height,
                      margin=dict(l=8, r=8, t=40, b=8),
                      xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"))
    return fig, X, Y


def plot_graph(g, start=None, end=None, visited=(), path=(), title="", height=520):
    import plotly.graph_objects as go
    fig, X, Y = _base(g, height)
    if len(path) > 1:
        fig.add_trace(go.Scatter(x=[X[i] for i in path], y=[Y[i] for i in path], mode="lines",
                                 line=dict(color=ROUTE, width=5), hoverinfo="skip"))
    colors = ["#FFFFFF"] * g.n
    for i in visited:
        colors[i] = AMBER
    for i in path:
        colors[i] = ROUTE
    if start is not None:
        colors[start] = TEAL
    if end is not None:
        colors[end] = INK
    size = max(5, min(14, 22 - 2 * math.sqrt(g.n)))
    fig.add_trace(go.Scatter(x=X, y=Y, mode="markers", text=g.labels, hovertemplate="%{text}<extra></extra>",
                             marker=dict(size=size, color=colors, line=dict(color=INK, width=1.5))))
    ends = [i for i in (start, end) if i is not None]
    fig.add_trace(go.Scatter(x=[X[i] for i in ends], y=[Y[i] for i in ends], mode="text",
                             text=[g.labels[i] for i in ends], textposition="top center", hoverinfo="skip"))
    fig.update_layout(title=title)
    return fig


def plot_order(g, order, title="", height=420):
    """Colour every node by the rank at which a traversal reached it."""
    import plotly.graph_objects as go
    fig, X, Y = _base(g, height)
    rank = [None] * g.n
    for k, i in enumerate(order):
        rank[i] = k
    fig.add_trace(go.Scatter(
        x=X, y=Y, mode="markers", text=[f"{l}: step {r}" for l, r in zip(g.labels, rank)],
        hovertemplate="%{text}<extra></extra>",
        marker=dict(size=12, color=[r if r is not None else -1 for r in rank], colorscale="Tealgrn",
                    showscale=True, colorbar=dict(title="step"), line=dict(color=INK, width=1))))
    fig.update_layout(title=title)
    return fig


def plot_heat(g, counts, title="", height=460):
    """Shade each node by a count (for example how often searches visit it)."""
    import plotly.graph_objects as go
    fig, X, Y = _base(g, height)
    fig.add_trace(go.Scatter(
        x=X, y=Y, mode="markers", text=[f"{l}: {c}" for l, c in zip(g.labels, counts)],
        hovertemplate="%{text}<extra></extra>",
        marker=dict(size=14, color=counts, colorscale="Tealgrn", showscale=True,
                    colorbar=dict(title="visits"), line=dict(color=INK, width=1.5))))
    fig.update_layout(title=title)
    return fig


def plot_edge_usage(g, usage, title="", height=460):
    """Road thickness shows how many cheapest routes use each road."""
    import plotly.graph_objects as go
    fig, X, Y = _base(g, height)
    mx, labels = max(usage.values()), g.labels
    for (a, b), c in usage.items():
        fig.add_trace(go.Scatter(x=[X[a], X[b]], y=[Y[a], Y[b]], mode="lines", hoverinfo="skip",
                                 line=dict(color=TEAL, width=1 + 9 * c / mx)))
    mids = list(usage)
    fig.add_trace(go.Scatter(x=[(X[a] + X[b]) / 2 for a, b in mids], y=[(Y[a] + Y[b]) / 2 for a, b in mids],
                             mode="markers", marker=dict(size=8, opacity=0),
                             text=[f"{labels[a]} to {labels[b]}: {usage[(a, b)]} routes" for a, b in mids],
                             hovertemplate="%{text}<extra></extra>"))
    fig.add_trace(go.Scatter(x=X, y=Y, mode="markers", hoverinfo="skip",
                             marker=dict(size=6, color="#FFFFFF", line=dict(color=INK, width=1.5))))
    fig.update_layout(title=title)
    return fig
