// Cross-runtime smoke test for the intent graph: JS runtime drives ops on a
// Python-seeded mcft_intent.json. Run from a scratch dir containing the seed:
//   cd /tmp/intent_smoke && node smoke_intent.mjs
// Pull the mutated file back and validate with mcft.intent (Python) after.
import { IntentGraph } from 'file:///Users/tim/Desktop/mindcraft/src/agent/mcft_intent.js';

const g = IntentGraph.loadIfPresent();
if (!g) { console.error('FAIL: no mcft_intent.json in cwd'); process.exit(1); }

const checks = [];
function check(name, cond) { checks.push([name, !!cond]); if (!cond) console.error('FAIL:', name); }

// view before any ops
let info = g.info('sable', 'jolt');
check('view has INTENT header', info.view.startsWith('INTENT'));
check('view shows values', info.view.includes('You value:'));
check('view shows NOW on walls', info.view.includes('NOW: [walls]'));
check('view shows partner', info.view.includes('jolt is on:'));
check('site from root anchor', info.site === '(0, 86, 64)');
check('view under budget', info.view.length < 900);

// model op surface
let r = g.applyOp('sable', 'goalAdd', { title: 'gather 32 cobblestone', why: 'walls need stone' });
check('goalAdd ok', r.ok && g.active['sable'] === r.node_id);
check('goalAdd rejects missing why', !g.applyOp('sable', 'goalAdd', { title: 'x' }).ok);
check('unknown op rejected', !g.applyOp('sable', 'goalTeleport', {}).ok);
check('switch to value rejected', !g.applyOp('sable', 'goalSwitch', { node_id: 'val_safety' }).ok);

r = g.applyOp('sable', 'goalDone', { reason: 'chest stocked' });
check('goalDone walks back to walls', r.ok && g.active['sable'] === 'walls');

// code op: block + reroute (loop-breaker v3 path)
r = g.applyOp('jolt', 'block', { reason: 'repeating the same action' });
check('block reroutes jolt', r.ok && g.active['jolt'] !== 'walls');
check('block message has alternatives', r.message.includes('Alternatives:'));
// era-F fix: system mission goals never lose their status to a block
check('walls survives block (system node)', g.nodes['walls'].status === 'active');

// era-F fix: persona tasks block WITH a decay timer, and expire
r = g.applyOp('jolt', 'goalAdd', { title: 'dig clay pit', why: 'bricks for the roof' });
const taskId = r.node_id;
g.applyOp('jolt', 'block', { reason: 'flooded' });
check('persona task blocked with timer',
    g.nodes[taskId].status === 'blocked' && g.nodes[taskId].blocked_until);
g.nodes[taskId].blocked_until = '2020-01-01T00:00:00Z';
g.applyOp('jolt', 'goalSwitch', { node_id: 'walls' });
check('expired block reopens', g.nodes[taskId].status === 'active');

// era-F fix: switch revives a blocked goal and accepts exact titles
g.applyOp('jolt', 'goalSwitch', { node_id: taskId });
g.applyOp('jolt', 'block', { reason: 'still flooded' });
r = g.applyOp('jolt', 'goalSwitch', { node_id: 'dig clay pit', why: 'water drained' });
check('switch by title revives blocked', r.ok && g.nodes[taskId].status === 'active');

// era-F fix: all-blocked tree heals instead of deadlocking
for (const n of Object.values(g.nodes)) if (n.kind !== 'value') n.status = 'blocked';
for (const k of Object.keys(g.active)) delete g.active[k];
info = g.info('sable', 'jolt');
check('all-blocked tree auto-heals', info.view.includes('NOW:'));
r = g.applyOp('sable', 'goalAdd', { title: 'restart effort', why: 'mission stalled' });
check('goalAdd works after heal (root fallback)', r.ok);

// alignment steering: jolt is spectacle-heavy, improve should rank over door
check('alignment steers jolt to improve', g.alignment('jolt', 'improve') > g.alignment('jolt', 'door'));

info = g.info('sable', 'jolt');
check('sable path logged', info.path.length >= 1);

const failed = checks.filter(([, ok]) => !ok);
console.log(`${checks.length - failed.length}/${checks.length} checks passed`);
process.exit(failed.length ? 1 : 0);
