// SPDX-License-Identifier: MIT
export function validCandidate(m, now, lastSequence) {
    return m !== null && typeof m === 'object' && m.type === 'pinch' &&
        (m.direction === 'in' || m.direction === 'out') &&
        Number.isSafeInteger(m.sequence) && m.sequence > lastSequence &&
        Number.isSafeInteger(m.monotonic_us) &&
        now >= m.monotonic_us && now - m.monotonic_us <= 300000;
}
