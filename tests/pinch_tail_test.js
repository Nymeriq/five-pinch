import {PinchTailGuard} from '../pinchTailGuard.js';
let checks = 0;
function check(value) { checks++; if (!value) throw new Error(`Tail guard check ${checks} failed`); }
const node = '/dev/input/event5';
const guard = new PinchTailGuard();
const filter = (phase, fingers, at, now = at, device = node) => guard.filter(device, phase, fingers, at, now);
// An independent gesture never arms this guard, regardless of sensitivity.
for (const fingers of [1, 2, 3, 4]) {
    check(!filter('begin', fingers, 1000));
    check(!filter('update', fingers, 2000));
    check(!filter('end', fingers, 3000));
}
guard.arm(node, 10000, 10000);
check(!filter('begin', 2, 11000));
check(!filter('begin', 4, 11000, 11000, '/dev/input/event6'));
check(!filter('update', 4, 11000)); // Existing native sequence must finish normally.
check(filter('begin', 4, 12000));
check(filter('update', 3, 13000));
check(filter('cancel', 3, 14000));
check(!filter('update', 3, 15000));
// Queued old tail events are blocked, but a NEW hand cycle is not.
guard.release(node, 20000, 21000);
check(filter('begin', 3, 19000, 22000));
check(filter('end', 3, 20000, 23000));
for (const fingers of [1, 2, 3, 4])
    check(!filter('begin', fingers, 24000, 24000));
check(!filter('begin', 4, 9000, 25000)); // Before the confirmed pinch.
check(!filter('begin', 4, 19000, 400000)); // Stale evidence expires.
guard.arm(node, 500000, 500000);
check(filter('begin', 3, 501000));
check(!filter('update', 3, 4000001)); // Missing end cannot latch forever.
guard.arm(node, 5000000, 5000000);
guard.reset();
check(!filter('begin', 4, 5001000));
guard.arm('not-a-device', 6000000, 6000000);
check(!filter('begin', 4, 6001000));
print(`${checks} pinch-tail checks passed`);
