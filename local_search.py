"""Local and nature-inspired search: Hill Climbing, Genetic Algorithm, Ant Colony Optimisation.

DISABLED FOR NOW. To enable, uncomment the two lines near the bottom of algorithms.py
(`from local_search import LOCAL_ALGOS` and `ALGOS.update(LOCAL_ALGOS)`).
"""
import random

from maze import DIRS


# ------------------------------------------------- Hill climbing (steepest ascent on h)
def hill_climbing(run, **_):
    m = run.maze
    cur = m.start
    trail = [cur]
    run.step(f"Start at {m.name(cur)} with h = {m.h(cur)}. Always move to the neighbour with the lowest h.",
             current=cur, trail=trail[:])
    while True:
        run.expanded += 1
        if cur == m.goal:
            run.set_path(trail[:])
            run.step(f"Reached the exit in {run.path_steps} steps, cost {run.path_cost}.", current=cur, trail=trail[:])
            return
        best, best_h = None, m.h(cur)
        for nb in m.neighbors(cur):
            if m.h(nb) < best_h:
                best, best_h = nb, m.h(nb)
        if best is None:
            run.end("stuck")
            run.step(f"STUCK at {m.name(cur)} (h = {m.h(cur)}): no neighbour is better - a local optimum. "
                     f"Hill climbing never backtracks.", current=cur, trail=trail[:])
            return
        cur = best
        trail.append(cur)
        run.step(f"Move to {m.name(cur)} (h = {best_h}).", current=cur, trail=trail[:])


# --------------------------------------- Genetic algorithm (chromosome = list of moves)
def genetic(run, **_):
    m = run.maze
    POP, LEN, GENS, MUT, ELITE = 60, 45, 300, 0.06, 2

    def walk(genes):                           # run the moves; walls and borders block movement
        cur, min_h, trail, reached = m.start, m.h(m.start), [m.start], False
        for gene in genes:
            r, c = m.rc(cur)
            r, c = r + DIRS[gene][0], c + DIRS[gene][1]
            if not (0 <= r < m.rows and 0 <= c < m.cols):
                continue
            nxt = r * m.cols + c
            if m.cells[nxt] == "#":
                continue
            cur = nxt
            trail.append(cur)
            min_h = min(min_h, m.h(cur))
            if cur == m.goal:
                reached = True
                break
        fit = 1000 - m.path_cost(trail) if reached else -(min_h + m.h(cur))
        return {"genes": genes, "trail": trail, "fit": fit, "reached": reached}

    def tournament(ev):
        return max(random.sample(ev, 3), key=lambda e: e["fit"])

    pop = [[random.randrange(4) for _ in range(LEN)] for _ in range(POP)]
    run.step(f"Generation 0: {POP} random chromosomes, each {LEN} moves long. Fitness = closeness to the exit.")
    for gen in range(1, GENS + 1):
        ev = sorted((walk(g) for g in pop), key=lambda e: -e["fit"])
        best = ev[0]
        run.expanded = gen * POP
        if best["reached"]:
            run.set_path(best["trail"])
            run.step(f"Generation {gen}: a chromosome reaches the exit! {run.path_steps} steps, cost {run.path_cost}.",
                     current=best["trail"][-1], visit=best["trail"], trail=best["trail"])
            return
        if gen == GENS:
            break
        nxt = [e["genes"][:] for e in ev[:ELITE]]
        while len(nxt) < POP:
            a, b = tournament(ev)["genes"], tournament(ev)["genes"]
            cut = random.randint(1, LEN - 1)
            child = a[:cut] + b[cut:]
            nxt.append([random.randrange(4) if random.random() < MUT else x for x in child])
        pop = nxt
        run.step(f"Generation {gen}: best fitness {best['fit']} (closest it got to the exit: {-best['fit']} cells away). "
                 f"Selection + crossover + mutation -> next generation.",
                 current=best["trail"][-1], visit=best["trail"], trail=best["trail"])
    run.end("no path")
    run.step(f"No chromosome reached the exit within {GENS} generations.")


# ------------------------------------------ Ant colony optimisation (pheromone on cells)
def ant_colony(run, **_):
    m = run.maze
    ANTS, ITER, ALPHA, BETA, RHO, Q, MAXSTEP = 30, 40, 1, 2, 0.3, 100, 150
    ph = [1.0] * m.n
    best_path, best_cost = None, float("inf")
    run.step(f"Start: {ANTS} ants per iteration, evaporation rate {RHO}. "
             f"Ants prefer cells with more pheromone and cheaper terrain.", pher=[round(x, 2) for x in ph])
    for it in range(1, ITER + 1):
        done, lost = [], 0
        for _ in range(ANTS):
            cur, path = m.start, [m.start]
            seen = {m.start}
            while cur != m.goal and len(path) < MAXSTEP:
                opts = [n for n in m.neighbors(cur) if n not in seen]
                if not opts:
                    break
                weights = [(ph[n] ** ALPHA) * ((1 / m.cost(n)) ** BETA) for n in opts]
                cur = random.choices(opts, weights=weights)[0]
                path.append(cur)
                seen.add(cur)
            if cur == m.goal:
                done.append((path, m.path_cost(path)))
            else:
                lost += 1
        ph = [max(0.01, x * (1 - RHO)) for x in ph]                  # evaporation
        for path, c in done:                                          # deposit
            for n in path:
                ph[n] += Q / c
            if c < best_cost:
                best_cost, best_path = c, path
        run.expanded += ANTS
        run.step(f"Iteration {it}: {len(done)}/{ANTS} ants reached the exit, {lost} got lost. "
                 f"Best cost so far: {best_cost if best_path else 'none yet'}.",
                 current=best_path[-1] if best_path else None, visit=[],
                 trail=best_path or [], pher=[round(x, 2) for x in ph])
    if best_path:
        run.set_path(best_path)
        run.step(f"Done. Best route found: {run.path_steps} steps, cost {run.path_cost}. Brighter purple = more pheromone.",
                 trail=best_path, pher=[round(x, 2) for x in ph])
    else:
        run.end("no path")
        run.step("No ant reached the exit.")


LOCAL_ALGOS = {
    "hill": {"name": "Hill Climbing", "group": "Local & nature-inspired", "run": hill_climbing, "info": {
        "idea": "Greedy local search: always step to the neighbour with the lowest h(n). It never backtracks and remembers nothing but where it is.",
        "structure": "None - keeps only the current cell", "time": "O(m) moves, one neighbour scan each", "space": "O(1)",
        "complete": "No - can get stuck at local optima or plateaus", "optimal": "No",
        "note": "Paint a wall right in front of the straight route and watch it get stuck."}},
    "ga": {"name": "Genetic Algorithm", "group": "Local & nature-inspired", "run": genetic, "info": {
        "idea": "Evolves a population of move sequences using selection, crossover and mutation. Fitness = how close the walk gets to the exit.",
        "structure": "Population of chromosomes (lists of moves)", "time": "O(generations x population x length)",
        "space": "O(population x length)", "complete": "No (stochastic)", "optimal": "No guarantee",
        "note": "The purple line is the best chromosome of the current generation. Results differ from run to run."}},
    "aco": {"name": "Ant Colony Optimisation", "group": "Local & nature-inspired", "run": ant_colony, "info": {
        "idea": "Artificial ants build routes at random, biased by pheromone and terrain cost. Good routes get more pheromone; pheromone evaporates over time.",
        "structure": "Pheromone value per cell", "time": "O(iterations x ants x path length)", "space": "O(V)",
        "complete": "Probabilistic", "optimal": "No guarantee (converges toward good routes)",
        "note": "Purple glow = pheromone. The purple line is the best route found so far."}},
}
