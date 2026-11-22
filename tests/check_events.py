"""Proof: the events file matches the generator's ground truth exactly."""
import json
from pathlib import Path

# 1) What the generator SAYS it sent
truth = json.loads(Path("data/ground_truth.json").read_text())

# 2) What is ACTUALLY in the file
total_lines = 0
lines_per_topic = {"searches": 0, "bookings": 0}
unique_ids = {"searches": set(), "bookings": set()}

with open("data/events.jsonl") as f:
    for line in f:
        ev = json.loads(line)
        topic = ev["topic"]
        total_lines += 1
        lines_per_topic[topic] += 1
        unique_ids[topic].add(ev["event_id"])     # a set keeps each ID only once


# 3) Compare the two
def check(name, actual, expected):
    status = "PASS" if actual == expected else "FAIL"
    print(f"{status}  {name}: actual={actual} expected={expected}")


check("total lines", total_lines, truth["total_sent"])
for topic in ("searches", "bookings"):
    unique = len(unique_ids[topic])
    duplicates = lines_per_topic[topic] - unique
    check(f"unique {topic}", unique, truth[f"unique_{topic}"])
    check(f"duplicate {topic}", duplicates, truth[f"duplicates_{topic}"])