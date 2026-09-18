from app.algorithms.astar import search
def dijkstra(graph,start,goal,cost): return search(graph,start,goal,cost,lambda _:0)
