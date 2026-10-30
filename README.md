# AI Search Visualizer (Python + Flask)

Pick a search algorithm from the dropdown and watch it solve a weighted maze step by step.
The algorithms run in **Python**; **Flask** serves the page and the API; the browser replays the recorded steps.

## Run it (Windows)

```
cd ai_search_flask
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

## Project layout

| File | What it does |
|---|---|
| `app.py` | Flask server: `/` (page), `/api/meta`, `/api/run`, `/api/best` |
| `maze.py` | Maze model (terrain costs, neighbours, heuristic) and the step `Recorder` |
| `algorithms.py` | BFS, DFS, DLS, Uniform Cost, Greedy, A*, Dijkstra + the algorithm registry |
| `local_search.py` | Hill Climbing, Genetic Algorithm, Ant Colony (**disabled for now**) |
| `templates/index.html` | The page |
| `static/app.js`, `static/style.css` | Drawing, controls, step replay |

## The maze

Terrain costs: road 1, grass 3, mud 5. There are three routes from Start to Exit:

| Route | Steps | Cost | Found by |
|---|---|---|---|
| A (mud, straight) | 18 | 62 | BFS, Greedy, DLS (limit 20) |
| B (grass, bottom) | 24 | 46 | DFS |
| C (road, top) | 28 | 28 | Uniform Cost, A*, Dijkstra |

You can paint walls / road / grass / mud on the maze to build your own.

## Enable Hill Climbing, Genetic and Ant Colony

Open `algorithms.py`, find the block near the bottom, and uncomment these two lines:

```python
# from local_search import LOCAL_ALGOS
# ALGOS.update(LOCAL_ALGOS)
```

Restart the server; they appear in the dropdown under "Local & nature-inspired".

## Not included yet

Minimax with alpha-beta pruning and FOL Wumpus World (separate tasks).
