import heapq, itertools, math
def search(graph,start,goal,cost,heuristic):
    counter=itertools.count(); queue=[(heuristic(start),next(counter),0,start)]
    best={start:0}; parent={}; expanded=0
    while queue:
        _,_,g,u=heapq.heappop(queue)
        if g>best.get(u,math.inf): continue
        expanded+=1
        if u==goal:
            path=[u]
            while u in parent: u=parent[u]; path.append(u)
            return list(reversed(path)),g,expanded
        for v,distance in graph[u]:
            step=cost(u,v,distance)
            if not math.isfinite(step): continue
            candidate=g+step
            if candidate<best.get(v,math.inf):
                best[v]=candidate; parent[v]=u
                heapq.heappush(queue,(candidate+heuristic(v),next(counter),candidate,v))
    raise ValueError('No feasible maritime route meets the selected constraints')
