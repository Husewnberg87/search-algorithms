"""Maze model and step recorder shared by all search algorithms."""
import math

# Legend: # wall   . road (cost 1)   g grass (cost 3)   m mud (cost 5)   S start   E exit
DEFAULT_MAP = [
    "#####################",
    "#...................#",
    "#.###.###.###.###.#.#",
    "#.#################.#",
    "#.#################.#",
    "#.#################.#",
    "#S...mmmmmmmmmmm...E#",
    "#.#.###############.#",
    "#.#.###############.#",
    "#....ggggggggggg....#",
    "#.#.#.#.#.#.#.#.#.#.#",
    "#####################",
]

# Neighbour order used by every algorithm: down, right, up, left
DIRS = [(1, 0), (0, 1), (-1, 0), (0, -1)]

# cost None = wall (impassable)
TERRAIN = {
    ".": {"name": "Road", "cost": 1},
    "g": {"name": "Grass", "cost": 3},
    "m": {"name": "Mud", "cost": 5},
    "#": {"name": "Wall", "cost": None},
}

# Three reference routes for the default maze (corner points as [row, col])
ROUTE_DEFS = [
    {"name": "A", "label": "short but muddy", "color": "#f43f5e", "wps": [[6, 1], [6, 19]]},
    {"name": "B", "label": "medium, grassy", "color": "#a855f7", "wps": [[6, 1], [9, 1], [9, 19], [6, 19]]},
    {"name": "C", "label": "long but all road", "color": "#10b981", "wps": [[6, 1], [1, 1], [1, 19], [6, 19]]},
]


class Maze:
    """A grid of cells. Cells are numbered row by row: index = row * cols + col."""

    def __init__(self, rows):
        if not rows or any(len(r) != len(rows[0]) for r in rows):
            raise ValueError("All maze rows must have the same length.")
        self.rows = len(rows)
        self.cols = len(rows[0])
        self.cells = []
        self.start = None
        self.goal = None
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                i = r * self.cols + c
                if ch == "S":
                    if self.start is not None:
                        raise ValueError("The maze has more than one start (S).")
                    self.start, ch = i, "."
                elif ch == "E":
                    if self.goal is not None:
                        raise ValueError("The maze has more than one exit (E).")
                    self.goal, ch = i, "."
                if ch not in TERRAIN:
                    raise ValueError(f"Unknown cell character {ch!r}.")
                self.cells.append(ch)
        if self.start is None or self.goal is None:
            raise ValueError("The maze needs one start (S) and one exit (E).")
        self.n = len(self.cells)

    def cost(self, i):
        return TERRAIN[self.cells[i]]["cost"]

    def rc(self, i):
        return divmod(i, self.cols)

    def name(self, i):
        r, c = self.rc(i)
        return f"({r},{c})"

    def h(self, i):
        """Heuristic: Manhattan distance to the exit (admissible, because every step costs at least 1)."""
        r, c = self.rc(i)
        gr, gc = self.rc(self.goal)
        return abs(r - gr) + abs(c - gc)

    def neighbors(self, i):
        r, c = self.rc(i)
        out = []
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                j = nr * self.cols + nc
                if self.cells[j] != "#":
                    out.append(j)
        return out

    def path_cost(self, path):
        return sum(self.cost(n) for n in path[1:])


class Recorder:
    """Collects the algorithm's state after every step so the browser can replay it."""

    def __init__(self, maze):
        self.maze = maze
        self.steps = []
        self.frontier = set()      # discovered but not yet expanded
        self.g = {}                # best known cost (or depth for DLS) per cell
        self._g_new = []
        self.expanded = 0
        self.max_frontier = 0
        self.path = []
        self.found = False
        self.status = "running"

    # ---- helpers used by the algorithms ----
    def set_g(self, cell, value):
        self.g[cell] = value
        self._g_new.append([cell, value])

    def step(self, msg, current=None, visit=None, trail=None, pher=None):
        """Record one step. `current` is the node being expanded (it becomes 'explored')."""
        self.max_frontier = max(self.max_frontier, len(self.frontier))
        if visit is None:
            visit = [current] if current is not None else []
        step = {
            "msg": msg,
            "current": current,
            "visit": visit,
            "frontier": sorted(self.frontier),
            "g": self._g_new,
            "expanded": self.expanded,
        }
        if trail is not None:
            step["trail"] = trail
        if pher is not None:
            step["pher"] = pher
        self._g_new = []
        self.steps.append(step)

    def finish(self, parent):
        """Rebuild the route from the parent links."""
        path, cell = [], self.maze.goal
        while cell is not None:
            path.append(cell)
            if cell == self.maze.start:
                break
            cell = parent.get(cell)
        path.reverse()
        self.set_path(path)

    def set_path(self, path):
        self.path = path
        self.found = True
        self.status = "found"

    def end(self, status):
        self.status = status

    @property
    def path_steps(self):
        return len(self.path) - 1 if self.found else None

    @property
    def path_cost(self):
        return self.maze.path_cost(self.path) if self.found else None

    def to_dict(self):
        return {
            "steps": self.steps,
            "path": self.path,
            "found": self.found,
            "status": self.status,
            "pathSteps": self.path_steps,
            "pathCost": self.path_cost,
            "expanded": self.expanded,
            "maxFrontier": self.max_frontier,
        }
