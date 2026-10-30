// Run: gjs -m tests/protocol_test.js
import {validCandidate} from '../protocol.js';
function assert(condition) { if (!condition) throw new Error('Protocol assertion failed'); }
const now = 1000000;
const m = {type: 'pinch', direction: 'in', sequence: 1, monotonic_us: now};
assert(validCandidate(m, now, 0));
assert(!validCandidate(m, now, 1));
assert(!validCandidate({...m, monotonic_us: now + 1}, now, 0));
assert(!validCandidate({...m, monotonic_us: now - 300001}, now, 0));
assert(!validCandidate({...m, direction: 'execute'}, now, 0));
assert(!validCandidate({...m, sequence: 1.5}, now, 0));
assert(!validCandidate(null, now, 0));
assert(!validCandidate({...m, type: 'status'}, now, 0));
print('8 protocol checks passed');
