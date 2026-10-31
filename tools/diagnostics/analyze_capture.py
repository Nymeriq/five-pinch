"""Replay saved coordinate frames without requiring device access."""
import collections
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'reader'))
from detector import Detector


def analyze(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines()]
    detector = Detector()
    counts = collections.Counter()
    directions = collections.Counter()
    ready = False
    cycles = 0
    five_cycles = 0
    active = False
    saw_five = False
    latencies = []
    baseline_time = None
    for row in rows[1:]:
        points = {int(k): tuple(v) for k, v in row.get('points', row.get('points_mm', {})).items()}
        counts[len(points)] += 1
        if points:
            if not active:
                cycles += 1
                active = True
                saw_five = False
            if len(points) == 5 and not saw_five:
                five_cycles += 1
                saw_five = True
        else:
            active = False
        if not ready:
            ready = not points
            continue
        if len(points) == 5 and detector.ids is None:
            baseline_time = row['time']
        event = detector.frame(row['time'], points, row['clicked'])
        if event:
            directions[event['direction']] += 1
            latencies.append(round(1000 * (row['time'] - baseline_time), 1))
    return {'file': str(path), 'frames': len(rows) - 1,
            'observed_span_s': round(rows[-1]['time'] - rows[1]['time'], 3) if len(rows) > 2 else 0,
            'frames_by_contact_count': dict(sorted(counts.items())),
            'contact_cycles': cycles, 'cycles_reaching_five_contacts': five_cycles,
            'candidates': dict(directions),
            'threshold_crossing_ms': latencies,
            'note': 'Unlabelled diagnostic candidates, not measured accuracy.'}


if __name__ == '__main__':
    for path in sys.argv[1:]:
        print(json.dumps(analyze(path), ensure_ascii=False))
