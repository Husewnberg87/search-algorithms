"""Uninformed and informed search algorithms.

Every algorithm receives a Recorder (`run`), does its search, and calls run.step(...)
after each expansion. The Flask API sends the recorded steps to the browser.
"""
import heapq
import itertools
from collections import deque

from maze import Maze


# ---------------------------------------------------------------- uninformed search
def bfs(run, **_):
    m = run.maze
    queue, seen, parent = deque([m.start]), {m.start}, {}
    run.frontier.add(m.start)
    run.step(f"Start: put {m.name(m.start)} in the FIFO queue.")
    while queue:
        cur = queue.popleft()
        run.frontier.discard(cur)
        run.expanded += 1
        if cur == m.goal:
            run.finish(parent)
            run.step(f"Dequeued {m.name(cur)} - that is the exit! Fewest-step route: "
                     f"{run.path_steps} steps, cost {run.path_cost}.", current=cur)
            return
        added = []
        for nb in m.neighbors(cur):
            if nb not in seen:
                seen.add(nb)
                parent[nb] = cur
                queue.append(nb)
                run.frontier.add(nb)
                added.append(m.name(nb))
        run.step(f"Dequeue {m.name(cur)} -> enqueue {', '.join(added) if added else 'nothing new'} "
                 f"(queue size {len(queue)}).", current=cur)
    run.end("no path")
    run.step("Queue is empty - there is no path to the exit.")


def dfs(run, **_):
    m = run.maze
    stack, visited, parent = [(m.start, -1)], set(), {}
    run.frontier.add(m.start)
    run.step(f"Start: push {m.name(m.start)} on the LIFO stack.")
    while stack:
        n, p = stack.pop()
        run.frontier.discard(n)
        if n in visited:                      # stale duplicate on the stack
            continue
        if p >= 0:
            parent[n] = p
        visited.add(n)
        run.expanded += 1
        if n == m.goal:
            run.finish(parent)
            run.step(f"Popped {m.name(n)} - that is the exit! Route found: "
                     f"{run.path_steps} steps, cost {run.path_cost}.", current=n)
            return
        nbs = [x for x in m.neighbors(n) if x not in visited]
        for nb in reversed(nbs):              # reversed, so the first neighbour is popped first
            stack.append((nb, n))
            run.frontier.add(nb)
        if nbs:
            run.step(f"Pop {m.name(n)} -> push {', '.join(map(m.name, nbs))} "
                     f"(dives into {m.name(nbs[0])} first; stack size {len(stack)}).", current=n)
        else:
            run.step(f"Pop {m.name(n)} -> dead end, backtrack (stack size {len(stack)}).", current=n)
    run.end("no path")
    run.step("Stack is empty - there is no path to the exit.")


def dls(run, limit=20, **_):
    m = run.maze
    best, parent, cutoff = {}, {}, False       # best = smallest depth at which a cell was expanded
    stack = [(m.start, -1, 0)]
    run.frontier.add(m.start)
    run.step(f"Start with depth limit l = {limit}.")
    while stack:
        n, p, d = stack.pop()
        run.frontier.discard(n)
        if n in best and best[n] <= d:        # already expanded at the same or a smaller depth
            continue
        best[n] = d
        if p >= 0:
            parent[n] = p
        run.set_g(n, d)                        # the "g-values" overlay shows the depth for DLS
        run.expanded += 1
        if n == m.goal:
            run.finish(parent)
            run.step(f"Popped {m.name(n)} at depth {d} - the exit! "
                     f"{run.path_steps} steps, cost {run.path_cost}.", current=n)
            return
        if d >= limit:
            cutoff = True
            run.step(f"{m.name(n)} is at depth {d} = limit {limit}: CUTOFF, not expanded further.", current=n)
            continue
        nbs = [x for x in m.neighbors(n) if not (x in best and best[x] <= d + 1)]
        for nb in reversed(nbs):
            stack.append((nb, n, d + 1))
            run.frontier.add(nb)
        run.step(f"Pop {m.name(n)} (depth {d}) -> push {', '.join(map(m.name, nbs)) if nbs else 'nothing'}.",
                 current=n)
    if cutoff:
        run.end("cutoff")
        run.step(f"No solution within depth limit {limit} (cutoff). The exit is deeper - try a bigger limit.")
    else:
        run.end("no path")
        run.step("Stack is empty - there is no path to the exit.")


# ------------------------------------------- best-first family: UCS, Greedy, A*, Dijkstra
def best_first(run, key, prio, label, greedy=False, exhaustive=False):
    m = run.maze
    heap, counter, closed, parent = [], itertools.count(), set(), {}

    def push(g, n):
        heapq.heappush(heap, (prio(g, n), next(counter), n))   # counter = first-in-first-out tie-break

    run.set_g(m.start, 0)
    push(0, m.start)
    run.frontier.add(m.start)
    goal_seen = False
    run.step(f"Start: put {m.name(m.start)} in the priority queue ({label(0, m.start)}).")
    while heap:
        p, _, cur = heapq.heappop(heap)
        if cur in closed:                      # stale entry
            continue
        closed.add(cur)
        run.frontier.discard(cur)
        run.expanded += 1
        g = run.g[cur]
        if cur == m.goal:
            if not exhaustive:
                run.finish(parent)
                run.step(f"Pop {m.name(cur)} - the exit! Route: {run.path_steps} steps, "
                         f"total cost {run.path_cost}.", current=cur)
                return
            if not goal_seen:
                goal_seen = True
                run.step(f"Exit {m.name(cur)} settled with distance {g}. Dijkstra keeps going until every "
                         f"reachable cell has its final distance.", current=cur)
        notes = []
        for nb in m.neighbors(cur):
            if nb in closed:
                continue
            ng = g + m.cost(nb)
            if greedy:
                if nb in run.g:                # greedy never revises a cell
                    continue
            elif nb in run.g and ng >= run.g[nb]:
                continue
            improved = nb in run.g
            run.set_g(nb, ng)
            parent[nb] = cur
            run.frontier.add(nb)
            push(ng, nb)
            notes.append(f"{m.name(nb)} [{label(ng, nb)}]{' improved' if improved else ''}")
        run.step(f"Pop {m.name(cur)} (lowest {key} = {p}) -> "
                 f"{'queue ' + ', '.join(notes) if notes else 'nothing new to queue'}.", current=cur)
    if exhaustive and m.goal in run.g:
        run.finish(parent)
        run.step(f"All reachable cells are settled. Shortest distance to the exit = {run.path_cost}; "
                 f"route has {run.path_steps} steps.")
        return
    run.end("no path")
    run.step("Priority queue is empty - there is no path to the exit.")


def ucs(run, **_):
    best_first(run, "g", lambda g, n: g, lambda g, n: f"g={g}")


def dijkstra(run, **_):
    best_first(run, "distance", lambda g, n: g, lambda g, n: f"dist={g}", exhaustive=True)


def greedy(run, **_):
    m = run.maze
    best_first(run, "h", lambda g, n: m.h(n), lambda g, n: f"h={m.h(n)}", greedy=True)


def astar(run, **_):
    m = run.maze
    best_first(run, "f", lambda g, n: g + m.h(n), lambda g, n: f"g={g}+h={m.h(n)}={g + m.h(n)}")


# ------------------------------------------------------------------------- registry
ALGOS = {
    "bfs": {"name": "Breadth-First Search (BFS)", "group": "Uninformed search", "run": bfs, "info": {
        "idea": "Expands the shallowest unexpanded node first, level by level, like a ripple spreading out from the start.",
        "structure": "FIFO queue", "time": "O(b^d)", "space": "O(b^d)", "complete": "Yes (finite b)",
        "optimal": "Yes for the fewest steps - only when every step costs the same",
        "note": "BFS ignores terrain cost, so it returns the route with the fewest cells even if it wades through mud."}},
    "dfs": {"name": "Depth-First Search (DFS)", "group": "Uninformed search", "run": dfs, "info": {
        "idea": "Always expands the deepest node: follows one branch as far as it can, then backtracks to the last choice.",
        "structure": "LIFO stack", "time": "O(b^m)", "space": "O(b*m)",
        "complete": "Only in finite spaces (with a visited set, as here)", "optimal": "No",
        "note": "Neighbour order is down, right, up, left, so DFS dives downward first and returns whatever route it stumbles on - not necessarily a good one."}},
    "dls": {"name": "Depth-Limited Search (DLS)", "group": "Uninformed search", "run": dls, "info": {
        "idea": "DFS that refuses to go deeper than a limit l, which prevents endless descent into a long branch.",
        "structure": "LIFO stack + depth", "time": "O(b^l)", "space": "O(b*l)",
        "complete": "No - fails (cutoff) if l < d", "optimal": "No",
        "note": "Try limit 15 (the nearest exit is 18 steps away, so you get a cutoff) and limit 20 (a route is found). Cells show their depth if \"Show g-values\" is on."}},
    "ucs": {"name": "Uniform-Cost Search (UCS)", "group": "Uninformed search", "run": ucs, "info": {
        "idea": "Expands the node with the lowest path cost g(n) so far, so cheap roads are preferred over grass and mud.",
        "structure": "Priority queue ordered by g(n)", "time": "O(b^(1+floor(C*/e)))", "space": "O(b^(1+floor(C*/e)))",
        "complete": "Yes (if every step cost >= e > 0)", "optimal": "Yes - cheapest total cost",
        "note": "Finds the cheapest route even though it is the longest one in steps. Turn on \"Show g-values\" to see the cost of reaching each cell."}},
    "greedy": {"name": "Greedy Best-First Search", "group": "Informed search", "run": greedy, "info": {
        "idea": "Expands the node that looks closest to the exit, h(n) = Manhattan distance, and ignores the cost already paid.",
        "structure": "Priority queue ordered by h(n)", "time": "O(b^m) worst case", "space": "O(b^m) worst case",
        "complete": "No in looping spaces (yes here, thanks to the visited set)", "optimal": "No",
        "note": "Very few expansions, but it walks straight toward the exit - right through the mud."}},
    "astar": {"name": "A* Search", "group": "Informed search", "run": astar, "info": {
        "idea": "Combines both ideas: f(n) = g(n) + h(n), the cost so far plus the estimated cost remaining.",
        "structure": "Priority queue ordered by f(n)", "time": "O(b^d) worst case (far less with a good heuristic)",
        "space": "O(b^d)", "complete": "Yes",
        "optimal": "Yes, if h(n) is admissible (never overestimates). Manhattan distance with minimum step cost 1 is admissible.",
        "note": "Finds the same cheapest route as UCS but usually expands fewer cells because h(n) steers it toward the exit."}},
    "dijkstra": {"name": "Dijkstra's Algorithm", "group": "Informed search", "run": dijkstra, "info": {
        "idea": "Single-source shortest paths: settles cells in order of distance from the start and continues until all reachable cells have a final distance.",
        "structure": "Min-heap (priority queue) of distances", "time": "O((V + E) log V)", "space": "O(V)",
        "complete": "Yes", "optimal": "Yes (non-negative weights)",
        "note": "Same ordering as UCS, but UCS stops when the exit is popped while Dijkstra fills the whole map. Turn on \"Show g-values\" to see the distance map."}},
}

# ---- Local & nature-inspired search (Hill Climbing, Genetic, Ant Colony) - disabled for now ----
# To enable them, uncomment the next two lines. They then appear in the dropdown automatically.
# from local_search import LOCAL_ALGOS
# ALGOS.update(LOCAL_ALGOS)


# ------------------------------------------------------------------------- helpers
def solve(maze, key, **opts):
    """Run one algorithm to the end and return its Recorder."""
    from maze import Recorder
    run = Recorder(maze)
    ALGOS[key]["run"](run, **opts)
    if run.status == "running":
        run.status = "found" if run.found else "no path"
    return run


def best_for(maze):
    """Best possible cost (UCS) and fewest steps (BFS) for this maze, or None if there is no route."""
    u, b = solve(maze, "ucs"), solve(maze, "bfs")
    if not u.found:
        return None
    return {"cost": u.path_cost, "steps": b.path_steps}
