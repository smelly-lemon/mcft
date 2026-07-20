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
check('walls now blocked', g.nodes['walls'].status === 'blocked');

// alignment steering: jolt is spectacle-heavy, improve should rank over door
check('alignment steers jolt to improve', g.alignment('jolt', 'improve') > g.alignment('jolt', 'door'));

info = g.info('sable', 'jolt');
check('sable path logged', info.path.length >= 1);

const failed = checks.filter(([, ok]) => !ok);
console.log(`${checks.length - failed.length}/${checks.length} checks passed`);
process.exit(failed.length ? 1 : 0);
