"""Optional read-only hardware smoke test; never performs a desktop action."""
import json
from pathlib import Path
import subprocess
import sys
import time

service = Path(__file__).resolve().parents[1] / 'reader' / 'service.py'
for mode in ('lease-expiry', 'parent-close'):
    child = subprocess.Popen(['/usr/bin/python3', '-I', str(service)],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        for _ in range(5):
            child.stdin.write('run\n')
            child.stdin.flush()
            time.sleep(.15)
        started = time.monotonic()
        if mode == 'parent-close':
            child.stdin.close()
        code = child.wait(timeout=2)
        messages = [json.loads(line) for line in child.stdout]
        assert code == 0, (code, messages)
        assert any(m.get('type') == 'status' and 'Recognition active' in m.get('message', '') for m in messages), messages
        print(json.dumps({'test': mode, 'exit_code': code,
                          'exit_after_last_pulse_s': round(time.monotonic() - started, 3),
                          'reader_opened': True}))
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
        child.stdout.close()
        if not child.stdin.closed:
            child.stdin.close()
