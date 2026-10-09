# RouteOpt — graph-based route optimization

Graph-based navigation project: Dijkstra, A*, Bellman–Ford and BFS on the same
weighted map, plus Trie autocomplete, BFS/DFS traversal, topological sort, and
a benchmarking framework. PES University, Data Structures & Algorithms.

## Live links

> Replace `YOUR-USERNAME/YOUR-REPO` below with your real repo path, and paste
> the same value into `LINKS.repo` at the top of `index.html`.

- **Website (GitHub Pages):** https://YOUR-USERNAME.github.io/YOUR-REPO/
- **Source code:** https://github.com/YOUR-USERNAME/YOUR-REPO
- **Notebook in Colab:**
  https://colab.research.google.com/github/YOUR-USERNAME/YOUR-REPO/blob/main/RouteOpt.ipynb
- **Notebook file (.ipynb):**
  https://github.com/YOUR-USERNAME/YOUR-REPO/blob/main/RouteOpt.ipynb
- **Streamlit app:** your Streamlit Cloud URL after deploy (see below)

## What's what (the two apps are different)

| File | What it is | Where it runs |
|---|---|---|
| `index.html` | Static website, all algorithms re-implemented in JavaScript, runs in the browser | GitHub Pages (free, no server) |
| `app.py` + `routeopt.py` | Interactive Streamlit app, Python/Plotly, includes scaling benchmark | Streamlit Community Cloud |
| `RouteOpt.ipynb` | Notebook with every analysis, step by step | Colab / Jupyter |
| `routeopt.py` | Core Python: graph, Dijkstra, A*, Bellman-Ford, BFS, DFS, Trie, benchmarks | Imported by `app.py` and the notebook |

## Run locally

```bash
pip install -r requirements.txt

# Streamlit app
streamlit run app.py

# Static website (just open it, no server needed)
open index.html
```

## Push to GitHub

```bash
git init
git add index.html app.py routeopt.py RouteOpt.ipynb requirements.txt README.md .gitignore
git commit -m "RouteOpt: website, Streamlit app, notebook"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

## Turn on the website (GitHub Pages)

1. Push (above).
2. GitHub repo → **Settings → Pages**.
3. **Source:** Deploy from a branch → **Branch:** `main`, folder `/ (root)`.
4. Save. Your site is live at `https://YOUR-USERNAME.github.io/YOUR-REPO/` in ~1 min.
5. Edit `index.html` → set `LINKS.repo = "YOUR-USERNAME/YOUR-REPO"`, commit + push,
   and the Links section auto-shows GitHub / Colab / notebook links.

## Deploy the Streamlit app (separate from the website)

1. Push (above) — Streamlit Cloud reads from GitHub.
2. Go to https://share.streamlit.io → **New app** → pick your repo/branch,
   **Main file path:** `app.py`.
3. Deploy. You get a URL like `https://your-app.streamlit.app`.
4. Paste that URL into `LINKS.streamlit` in `index.html`, push again — the
   website then links to the Streamlit app.

## Open in Colab

No setup needed once pushed. Just visit:

```
https://colab.research.google.com/github/YOUR-USERNAME/YOUR-REPO/blob/main/RouteOpt.ipynb
```

Contact: harshinisuresha7@gmail.com
