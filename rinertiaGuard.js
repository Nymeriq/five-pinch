// SPDX-License-Identifier: MIT
import {validNode} from './pinchTailGuard.js';

// No service control or global scrolling changes. Only the known virtual
// pointer's SCROLL events are filtered in a bounded five-contact window.
export class RinertiaGuard {
    constructor() { this.reset(); }

    reset() { this.cycle = null; }

    arm(node, at, now) {
        if (validNode(node))
            this.cycle = {node, at, released: false, expires: now + 3000000, lastScroll: now};
    }

    begin(node, at) {
        // A NEW physical contact cycle always wins over old momentum.
        if (this.cycle?.node === node && at > this.cycle.at)
            this.reset();
    }

    release(node, at, now) {
        if (this.cycle?.node === node && at >= this.cycle.at) {
            this.cycle.released = true;
            this.cycle.expires = now + 2000000;
            this.cycle.lastScroll = now;
        }
    }

    filter(deviceName, at, now) {
        if (deviceName !== 'rinertia Virtual Device')
            return false;
        const c = this.cycle;
        if (!c)
            return false;
        if (now > c.expires || (c.released && now - c.lastScroll > 120000)) {
            this.reset();
            return false;
        }
        if (at < c.at)
            return false;
        c.lastScroll = now;
        return true;
    }
}
