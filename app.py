"""Flask server for the AI Search Visualizer.

Run:  python app.py      then open  http://127.0.0.1:5000
"""
from flask import Flask, jsonify, render_template, request

from algorithms import ALGOS, best_for, solve
from maze import DEFAULT_MAP, ROUTE_DEFS, TERRAIN, Maze

app = Flask(__name__)


def read_maze(data):
    """Build a Maze from the request (falls back to the default maze)."""
    return Maze(data.get("map") or DEFAULT_MAP)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/meta")
def meta():
    """Everything the page needs at start-up."""
    return jsonify(
        map=DEFAULT_MAP,
        terrain=TERRAIN,
        routes=ROUTE_DEFS,
        algorithms=[{"key": k, "name": a["name"], "group": a["group"], "info": a["info"]} for k, a in ALGOS.items()],
        best=best_for(Maze(DEFAULT_MAP)),
    )


@app.post("/api/run")
def run_algorithm():
    """Run one algorithm on the given maze and return every step so the browser can replay it."""
    data = request.get_json(silent=True) or {}
    key = data.get("algorithm")
    if key not in ALGOS:
        return jsonify(error=f"Unknown algorithm: {key!r}"), 400
    try:
        maze = read_maze(data)
        limit = max(1, min(int(data.get("limit", 20)), 500))
    except (ValueError, TypeError) as err:
        return jsonify(error=str(err)), 400
    result = solve(maze, key, limit=limit).to_dict()
    result["best"] = best_for(maze)
    return jsonify(result)


@app.post("/api/best")
def best():
    """Best possible cost / fewest steps for a (possibly edited) maze."""
    try:
        maze = read_maze(request.get_json(silent=True) or {})
    except ValueError as err:
        return jsonify(error=str(err)), 400
    return jsonify(best=best_for(maze))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
