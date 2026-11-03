// SPDX-License-Identifier: MIT
// Filter only whole native swipe sequences which BEGIN in a confirmed pinch's
// tail on the same physical input node. Never disable Shell's swipe trackers.
export class PinchTailGuard {
    constructor() { this.reset(); }

    reset() {
        this.pinch = null;
        this.blocked = new Map();
    }

    arm(node, at, now) {
        if (!validNode(node))
            return;
        this.pinch = {node, at: Math.floor(at / 1000) * 1000,
            released: null, expires: now + 3000000};
    }

    release(node, at, now) {
        if (this.pinch?.node === node) {
            this.pinch.released = Math.floor(at / 1000) * 1000;
            // Retain timestamps briefly for queued events, not new gestures.
            this.pinch.expires = now + 300000;
        }
    }

    filter(node, phase, fingers, at, now) {
        if (!validNode(node))
            return false;
        if (this.pinch && now > this.pinch.expires)
            this.pinch = null;
        for (const [key, expiry] of this.blocked) {
            if (now > expiry)
                this.blocked.delete(key);
        }
        if (phase === 'begin') {
            this.blocked.delete(node);
            const p = this.pinch;
            if (p?.node === node && fingers >= 3 && fingers <= 4 &&
                at >= p.at && (p.released === null || at <= p.released))
                this.blocked.set(node, now + 3000000);
        }
        const stop = this.blocked.has(node);
        if (phase === 'end' || phase === 'cancel')
            this.blocked.delete(node);
        return stop;
    }
}

export function validNode(node) {
    return typeof node === 'string' && /^\/dev\/input\/event[0-9]+$/.test(node);
}
