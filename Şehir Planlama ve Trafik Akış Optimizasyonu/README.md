# 🗺️ PageRank City Traffic Analyzer

> **Visualizing Google's PageRank algorithm on real urban street networks**

A Streamlit web application that applies the **PageRank algorithm** to real-world city street data to identify the most critical intersections in a neighborhood. Built as a university presentation project to demonstrate how PageRank — the algorithm behind Google Search — can be applied beyond the web to model traffic flow and urban planning.

---

## 🎯 What It Does

The app models a city neighborhood as a **directed graph**:
- **Nodes** → street intersections
- **Edges** → road segments (directional, respecting one-way streets)

PageRank is then applied to this graph. Intersections that many important roads flow through receive a **high PageRank score**, making them the most critical points in the traffic network — just like how important web pages receive more links from other important pages.

---

## 🏙️ Supported Neighborhoods

| Neighborhood | Character |
|---|---|
| Mission District | Dense, irregular grid — high traffic variety |
| Castro | Grid breaks from hills — interesting edge cases |
| Haight-Ashbury | Organic layout near parks — natural dead-ends |
| Noe Valley | Hilly terrain — many low-connectivity streets |
| Brisbane | Small city south of SF — clean suburban network |

---

## ✨ Features

- **Interactive map** — Dark-themed Folium map with color-coded intersections (green → red by PageRank score)
- **Live road network** — Real street data pulled from OpenStreetMap via OSMnx
- **Animated Top 10 markers** — Pulsing ping animation highlights the 10 most critical intersections
- **Click-to-fly navigation** — Click any item in the Top 10 panel to fly the map to that intersection
- **Adjustable damping factor** — Slider to change α (0.50–0.99) and watch PageRank scores update in real time
- **Offline cache** — Street graphs are cached locally after first download; no internet needed on subsequent runs
- **One-click setup** — `baslat.bat` installs all dependencies and launches the app automatically

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher — [Download here](https://www.python.org/downloads/)
  > ⚠️ During installation, check **"Add Python to PATH"**

### Windows (recommended)
Just double-click **`baslat.bat`** — it handles everything automatically.

### Manual (any OS)
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/pagerank-city-traffic.git
cd pagerank-city-traffic

# Install dependencies
pip install -r requirements.txt

# Run the app
python -m streamlit run app.py
```

Open your browser at **http://localhost:8501**

---

## 🧠 Algorithm

PageRank is computed using NetworkX's implementation:

$$PR(u) = \frac{1-\alpha}{N} + \alpha \sum_{v \in B_u} \frac{PR(v)}{L(v)}$$

| Parameter | Value | Description |
|---|---|---|
| α (damping factor) | 0.85 | Probability of following a road vs. teleporting — Google's original value |
| max_iter | 100 | Maximum iterations for convergence |
| tol | 1e-6 | Convergence tolerance |

At each iteration, a driver is modeled as either following a connected road (probability α) or teleporting to a random intersection (probability 1−α). After convergence, intersections with the highest scores are the most "central" in the network.

---

## 🛠️ Tech Stack

| Library | Purpose |
|---|---|
| [OSMnx](https://osmnx.readthedocs.io/) | Download real street networks from OpenStreetMap |
| [NetworkX](https://networkx.org/) | Graph construction and PageRank computation |
| [Streamlit](https://streamlit.io/) | Web application framework |
| [Folium](https://python-visualization.github.io/folium/) | Interactive Leaflet.js maps |
| [Matplotlib](https://matplotlib.org/) | Score distribution visualization |
| [NumPy](https://numpy.org/) | Numerical operations |

---

## 📁 Project Structure

```
pagerank-city-traffic/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── baslat.bat             # Windows one-click launcher
├── README.md
├── data/                  # OSMnx graph cache (.graphml files, git-ignored)
└── output/                # Generated Folium maps (.html files, git-ignored)
```

---

## 📖 Background

This project was developed as part of a university course presentation on the **PageRank algorithm**. The goal was to demonstrate that PageRank is not just a web-ranking algorithm — its graph-theoretic foundation makes it applicable to any network where flow and connectivity matter, including urban transportation systems.

---

## 📄 License

MIT License — feel free to use, modify, and distribute.
