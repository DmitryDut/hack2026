"""Progress report for docs/PLAN.md: `make progress`, `make todo`."""

import re
import sys
from pathlib import Path

PLAN = Path(__file__).resolve().parent.parent / "docs" / "PLAN.md"
STEP = re.compile(r"^- \[( |x)\] (P\d+b?\.\d+)\s+(.*)$")
HEAD = re.compile(r"^## (P\d+b?)\s+(.*)$")
TODO = re.compile(r"^\| (TD-\d+) \| ([^|]*) \| (.*) \| ([^|]*) \| \[( |x)\] \|$")


def parse(lines):
    iterations, todos, current = [], [], None
    for line in lines:
        head = HEAD.match(line)
        if head:
            current = {"id": head.group(1), "title": head.group(2), "steps": []}
            iterations.append(current)
            continue
        step = STEP.match(line)
        if step and current:
            current["steps"].append((step.group(1) == "x", step.group(2), step.group(3)))
            continue
        todo = TODO.match(line)
        if todo:
            todos.append((todo.group(5) == "x", *todo.group(1, 2, 3, 4)))
    return iterations, todos


def main() -> None:
    iterations, todos = parse(PLAN.read_text(encoding="utf-8").splitlines())
    open_todos = [t for t in todos if not t[0]]
    if "--todo" in sys.argv:
        for _, tid, origin, text, when in open_todos:
            print(f"{tid}  [{origin}] {text}  → {when}")
        print(f"\nОткрыто: {len(open_todos)} из {len(todos)}")
        return
    next_step = None
    for it in iterations:
        done = sum(1 for s in it["steps"] if s[0])
        total = len(it["steps"])
        pct = 100 * done // total if total else 0
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        pending = next((s for s in it["steps"] if not s[0]), None)
        if pending and next_step is None:
            next_step = pending
        print(f"{it['id']:<4} {bar} {done:>2}/{total:<2} {pct:>3}%  {it['title']}")
    if next_step:
        print(f"\nДальше: {next_step[1]} {next_step[2]}")
    else:
        print("\nВсе шаги выполнены")
    print(f"TODO: открыто {len(open_todos)} из {len(todos)} (make todo)")


if __name__ == "__main__":
    main()
