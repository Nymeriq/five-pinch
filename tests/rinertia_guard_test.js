import {RinertiaGuard} from '../rinertiaGuard.js';
let checks = 0;
function check(value) {checks++; if (!value) throw new Error(`Rinertia check ${checks} failed`);}
const node = '/dev/input/event5';
const name = 'rinertia Virtual Device';
const g = new RinertiaGuard();
check(!g.filter(name, 1000, 1000));
g.arm(node, 2000, 2000);
check(!g.filter('External Mouse', 3000, 3000));
check(!g.filter(null, 3000, 3000));
check(!g.filter('Unrelated virtual mouse', 3000, 3000));
check(!g.filter('Apple SPI Touchpad', 3000, 3000));
check(!g.filter(name, 1000, 3000));
check(g.filter(name, 3000, 3000));
g.release(node, 5000, 5000);
check(g.filter(name, 15000, 15000));
check(g.filter(name, 30000, 30000));
check(!g.filter(name, 160001, 160001)); // Momentum stream has gone quiet.
g.arm(node, 200000, 200000);
g.release(node, 210000, 210000);
g.begin(node, 220000); // Even one new physical contact restores normal scroll.
check(!g.filter(name, 221000, 221000));
g.arm(node, 300000, 300000);
g.begin('/dev/input/event6', 310000);
check(g.filter(name, 320000, 320000));
g.reset();
check(!g.filter(name, 330000, 330000));
g.arm(node, 400000, 400000);
check(!g.filter(name, 3400001, 3400001)); // Missing release cannot block forever.
g.arm(node, 4000000, 4000000);
g.release(node, 4010000, 4010000);
for (let t = 4020000; t <= 6010000; t += 100000)
    check(g.filter(name, t, t));
check(!g.filter(name, 6020000, 6020000)); // Continuous output also expires.
// Regression: actual capture 03 timings, including the scroll which switched workspaces.
g.arm(node, 4758274712, 4758275594);
check(g.filter(name, 4758494000, 4758508979));
g.release(node, 4758557420, 4758562551);
check(g.filter(name, 4758566000, 4758570000));
g.begin(node, 4758600000);
check(!g.filter(name, 4758610000, 4758610000));
print(`${checks} rinertia guard checks passed`);
