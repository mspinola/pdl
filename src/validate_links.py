import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from link_franchises import rosters, names, best_assignment, YEARS

R = {y: rosters(y) for y in YEARS}
N = {y: names(y) for y in YEARS}

def norm(s):
    return "".join(c for c in s.lower() if c.isalnum())

same = diff = 0
renames = []
for y1, y2 in zip(YEARS, YEARS[1:]):
    m = best_assignment(R[y1], R[y2])
    for fa, (fb, jac, inter) in m.items():
        if norm(N[y1][fa]) == norm(N[y2][fb]):
            same += 1
        else:
            diff += 1
            renames.append((y1, N[y1][fa], y2, N[y2][fb], jac, inter, fa, fb))

tot = same + diff
print(f"transitions: {tot}   name-identical: {same} ({same/tot:.1%})   name-changed: {diff}")
print("\nname changes (rename, or owner handoff -- needs your eye):")
for y1, n1, y2, n2, jac, inter, fa, fb in renames:
    print(f"  {y1} {n1!r} ({fa}) -> {y2} {n2!r} ({fb})   jac={jac:.2f} shared={inter}")

# how distinguishable is the correct match from the runner-up?
print("\nmargin check: correct match overlap vs best alternative")
worst = []
for y1, y2 in zip(YEARS, YEARS[1:]):
    for fa, pa in R[y1].items():
        sc = sorted(((len(pa & pb), fb) for fb, pb in R[y2].items()), reverse=True)
        worst.append((sc[0][0] - sc[1][0], y1, N[y1][fa], sc[0][0], sc[1][0]))
worst.sort()
for w in worst[:8]:
    print(f"  margin={w[0]}  {w[1]} {w[2]!r}  best={w[3]} runnerup={w[4]}")
