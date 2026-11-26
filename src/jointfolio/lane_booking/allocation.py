from collections import Counter, deque


def reservations(candidates, remaining, resource_cap):
    order = {}
    for row in candidates:
        order.setdefault(row.resource, deque()).append(row)
    rooms = deque(order)
    assigned = set()
    rejected = {}
    spent = Counter()
    while rooms:
        branch = rooms.popleft()
        queue = order[branch]
        next_case = queue.popleft()
        if next_case.units + spent[branch] > resource_cap:
            rejected[next_case.case_id] = "RESOURCE_CEILING"
        elif next_case.units <= remaining:
            assigned.add(next_case.case_id)
            spent[branch] += next_case.units
            remaining -= next_case.units
        if queue:
            rooms.append(branch)
    return assigned, rejected
