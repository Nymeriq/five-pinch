// SPDX-License-Identifier: MIT
export function validCandidate(m, now, lastSequence) {
    return m !== null && typeof m === 'object' && m.type === 'pinch' &&
        (m.direction === 'in' || m.direction === 'out') &&
        Number.isSafeInteger(m.sequence) && m.sequence > lastSequence &&
        Number.isSafeInteger(m.monotonic_us) &&
        now >= m.monotonic_us && now - m.monotonic_us <= 300000;
}

export function validContactState(m, now, lastSequence) {
    return m !== null && typeof m === 'object' &&
        (m.type === 'five-contact' || m.type === 'pinch-end' || m.type === 'contact-begin') &&
        typeof m.device === 'string' && /^\/dev\/input\/event[0-9]+$/.test(m.device) &&
        Number.isSafeInteger(m.sequence) && m.sequence > lastSequence &&
        Number.isSafeInteger(m.monotonic_us) &&
        now >= m.monotonic_us && now - m.monotonic_us <= 300000;
}

export function validPinchEnd(m, now, lastSequence) {
    return m?.type === 'pinch-end' && validContactState(m, now, lastSequence);
}
