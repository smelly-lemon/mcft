// mcft intent graph runtime (v1). JS twin of src/mcft/intent/model.py -
// same JSON schema, round-trips with the Python tooling that seeds and
// analyzes it. LOADED ONLY BY THE MINDSERVER: one process owns the file,
// agents propose ops over sockets (single writer + atomic rename; two agent
// processes sharing one JSON file is how journals used to get corrupted).
//
// Design contract (docs/intent-graph-design.md): code owns the graph, the
// model proposes ops through a narrow validated surface, malformed ops are
// rejected with a helpful message, never an exception.

import { readFileSync, writeFileSync, renameSync, existsSync } from 'fs';

const FILE = 'mcft_intent.json';

export class IntentGraph {
    constructor(data) {
        this.nodes = data.nodes || {};
        this.active = data.active || {};
        // v1.2 ping-pong guard: bot -> node_id -> avoid-until ISO (the 07-21
        // ablation showed block-steering bouncing between two siblings)
        this.recent = data.recent_steps_away || {};
    }

    static loadIfPresent() {
        if (!existsSync(FILE)) return null;
        try {
            return new IntentGraph(JSON.parse(readFileSync(FILE, 'utf8')));
        } catch (e) {
            console.error('[intent] failed to load graph:', e.message);
            return null;
        }
    }

    save() {
        const tmp = FILE + '.tmp';
        const data = { nodes: this.nodes, active: this.active, recent_steps_away: this.recent };
        writeFileSync(tmp, JSON.stringify(data, null, 1) + '\n');
        renameSync(tmp, FILE); // atomic on POSIX
    }

    // -- queries ------------------------------------------------------------

    path(nodeId) {
        const out = [];
        const seen = new Set();
        let cur = nodeId;
        while (cur) {
            if (seen.has(cur)) break;
            seen.add(cur);
            const node = this.nodes[cur];
            if (!node) break;
            out.push(node);
            cur = node.parent;
        }
        return out.reverse();
    }

    children(nodeId) {
        return Object.values(this.nodes).filter(n => n.parent === nodeId);
    }

    effectiveAnchor(nodeId) {
        const chain = this.path(nodeId);
        for (let i = chain.length - 1; i >= 0; i--) {
            if (chain[i].anchor) return chain[i].anchor;
        }
        return null;
    }

    valuesFor(persona, top = 3) {
        return Object.values(this.nodes)
            .filter(n => n.kind === 'value' && (n.weights?.[persona] ?? 0) > 0)
            .map(n => [n.title, n.weights[persona]])
            .sort((a, b) => b[1] - a[1])
            .slice(0, top);
    }

    alignment(persona, nodeId) {
        // How well a goal serves this persona's values: the steering signal.
        const byTitle = {};
        for (const n of Object.values(this.nodes)) {
            if (n.kind === 'value') byTitle[n.title] = n.weights?.[persona] ?? 0;
        }
        const chain = this.path(nodeId).filter(n => n.kind !== 'value');
        let score = 0;
        chain.reverse().forEach((node, i) => {
            const factor = i === 0 ? 1.0 : 0.5;
            for (const [title, serve] of Object.entries(node.serves_values || {})) {
                score += factor * serve * (byTitle[title] ?? 0);
            }
        });
        return score;
    }

    // -- self-healing (mirrors Python _expire_blocks) -------------------------

    _expireBlocks() {
        // Reactivate expired blocks; heal an all-blocked tree; repoint bots
        // standing on dead nodes. The era-F soak deadlocked without this.
        // Returns true if anything changed (callers persist).
        let changed = false;
        const now = new Date().toISOString();
        const goals = Object.values(this.nodes).filter(n => n.kind !== 'value');
        for (const n of goals) {
            if (n.status === 'blocked' && n.blocked_until && n.blocked_until <= now) {
                n.status = 'active';
                n.status_reason = 'block expired';
                n.blocked_until = null;
                changed = true;
            }
        }
        if (goals.length && !goals.some(n => n.status === 'active')) {
            for (const n of goals) {
                if (n.status === 'blocked') {
                    n.status = 'active';
                    n.status_reason = 'auto-heal: tree had no open goals';
                    n.blocked_until = null;
                    changed = true;
                }
            }
        }
        for (const [bot, nodeId] of Object.entries(this.active)) {
            const node = this.nodes[nodeId];
            if (!node || node.status !== 'active') {
                const start = node ? node.parent : this._missionRoot();
                const leaf = this._nextLeaf(start);
                if (leaf) this.active[bot] = leaf.id;
                else delete this.active[bot];
                changed = true;
            }
        }
        return changed;
    }

    _missionRoot() {
        const root = Object.values(this.nodes).find(n => n.kind !== 'value' && !n.parent);
        return root ? root.id : null;
    }

    _byTitle(text) {
        const want = String(text).trim().toLowerCase();
        const matches = Object.values(this.nodes)
            .filter(n => n.kind !== 'value' && n.title.trim().toLowerCase() === want);
        return matches.length === 1 ? matches[0] : null;
    }

    // -- ops (single entry point, mirrors Python apply_op) -------------------

    applyOp(bot, op, args) {
        try {
            this._expireBlocks();
            const handlers = {
                goalDone: () => this._opDone(bot, args.reason || ''),
                goalAdd: () => this._opAdd(bot, args.title || '', args.why || '', args.parent_id || ''),
                goalSwitch: () => this._opSwitch(bot, args.node_id || '', args.why || ''),
                block: () => this._opBlock(bot, args.reason || ''),
            };
            const handler = handlers[op];
            if (!handler) return { ok: false, message: `unknown intent op '${op}'` };
            const res = handler();
            this.save(); // healing above may have mutated even on a rejected op
            return res;
        } catch (e) {
            return { ok: false, message: `intent op rejected: ${e.message}` };
        }
    }

    _opDone(bot, reason) {
        const nodeId = this.active[bot];
        if (!nodeId) return { ok: false, message: 'you have no active goal to complete' };
        const node = this.nodes[nodeId];
        if (this.children(nodeId).some(c => c.status === 'active')) {
            return { ok: false, message: `'${node.title}' still has active subgoals - finish or abandon them first` };
        }
        node.status = 'done';
        node.status_reason = reason;
        const nxt = this._nextLeaf(node.parent);
        if (nxt) {
            this.active[bot] = nxt.id;
            const because = nxt.why || 'it serves the mission';
            return { ok: true, message: `done: ${node.title}. Next up: ${nxt.title} (because ${because})`, node_id: nxt.id };
        }
        delete this.active[bot];
        return { ok: true, message: `done: ${node.title}. No open subgoals - pick or add one.`, node_id: null };
    }

    _opAdd(bot, title, why, parentId) {
        if (!title.trim()) return { ok: false, message: 'goalAdd needs a title' };
        if (!why.trim()) return { ok: false, message: 'goalAdd needs a why - every goal must serve its parent' };
        const parent = parentId || this.active[bot] || this._missionRoot();
        const parentNode = this.nodes[parent];
        if (!parentNode) return { ok: false, message: `parent '${parent}' not found` };
        if (parentNode.kind === 'value') return { ok: false, message: 'value nodes cannot have children' };
        if (parentNode.status === 'done' || parentNode.status === 'abandoned') {
            return { ok: false, message: `parent '${parentNode.title}' is ${parentNode.status}` };
        }
        let id = title.toLowerCase().replace(/[^a-z0-9]+/g, '_').slice(0, 16).replace(/^_|_$/g, '');
        while (!id || this.nodes[id]) id = (id || 'goal') + Math.floor(Math.random() * 100);
        this.nodes[id] = {
            id, kind: 'task', title: title.trim().slice(0, 80), why: why.trim().slice(0, 120),
            parent, status: 'active', owner: bot, anchor: null,
            created_by: 'persona', created_at: new Date().toISOString(),
            weights: {}, serves_values: {}, status_reason: '', blocked_until: null,
        };
        this.active[bot] = id;
        return { ok: true, message: `added and switched to: ${title.trim()}`, node_id: id };
    }

    _opSwitch(bot, nodeId, why) {
        const node = this.nodes[nodeId] || this._byTitle(nodeId);
        if (!node) return { ok: false, message: `no such goal '${nodeId}'` };
        if (node.kind === 'value') return { ok: false, message: 'cannot work a value directly - pick a goal that serves it' };
        if (node.status === 'blocked') {
            // deliberate revive: switching back to a blocked goal unblocks it
            node.status = 'active';
            node.status_reason = why ? `revived by ${bot}: ${why}` : `revived by ${bot}`;
            node.blocked_until = null;
        } else if (node.status !== 'active') {
            return { ok: false, message: `'${node.title}' is ${node.status}` };
        }
        this.active[bot] = node.id;
        // a deliberate switch overrides the ping-pong guard for this goal
        if (this.recent[bot]) delete this.recent[bot][node.id];
        return { ok: true, message: `switched to: ${node.title}`, node_id: node.id };
    }

    _freshAvoids(bot) {
        // Prune expired step-away entries; return node ids still to avoid.
        const now = new Date().toISOString();
        const entries = this.recent[bot] || {};
        const fresh = {};
        for (const [nid, until] of Object.entries(entries)) {
            if (until > now) fresh[nid] = until;
        }
        if (Object.keys(fresh).length) this.recent[bot] = fresh;
        else delete this.recent[bot];
        return new Set(Object.keys(fresh));
    }

    _opBlock(bot, reason) {
        // Code-driven (loop-breaker v3): step away from the stuck goal.
        // Only persona tasks change status (with a decay timer); system
        // mission goals are structure and merely lose this bot's pointer.
        // v1.2: remember what we stepped away from and do not steer straight
        // back to it - that is how the ablation arm doubled its alternations.
        const nodeId = this.active[bot];
        if (!nodeId) return { ok: false, message: 'no active goal to block' };
        const node = this.nodes[nodeId];
        if (node.created_by !== 'system') {
            node.status = 'blocked';
            node.status_reason = reason;
            node.blocked_until = new Date(Date.now() + 20 * 60 * 1000).toISOString();
        }
        if (!this.recent[bot]) this.recent[bot] = {};
        this.recent[bot][nodeId] = new Date(Date.now() + 20 * 60 * 1000).toISOString();
        const avoid = this._freshAvoids(bot);
        const sibs = node.parent
            ? this.children(node.parent)
                  .filter(c => c.status === 'active' && c.id !== nodeId && !avoid.has(c.id))
                  .sort((a, b) => this.alignment(bot, b.id) - this.alignment(bot, a.id)).slice(0, 3)
            : [];
        const nxt = sibs[0]
            || this._nextLeaf(node.parent, avoid)
            || this._nextLeaf(node.parent); // everything avoided: any leaf beats none
        if (nxt) this.active[bot] = nxt.id;
        else delete this.active[bot];
        const alts = sibs.map(s => `[${s.id}] ${s.title}`).join('; ');
        const stuckNote = node.created_by === 'system'
            ? `You are stuck on '${node.title}' (${reason}) - stepping away for now; come back with a different approach.`
            : `Your goal '${node.title}' is blocked (${reason}) and will reopen in 20 minutes.`;
        const msg = stuckNote + ' ' +
            (nxt ? `Now on: ${nxt.title}.` : 'No open goals - add one with !goalAdd.') +
            (alts ? ` Alternatives: ${alts}. Use !goalSwitch to change.` : '');
        return { ok: true, message: msg, node_id: nxt ? nxt.id : null };
    }

    _nextLeaf(start, avoid = null) {
        const skip = avoid || new Set();
        const firstActiveLeaf = (nodeId) => {
            const kids = this.children(nodeId).filter(c => c.status === 'active');
            if (!kids.length) {
                if (skip.has(nodeId)) return null;
                const node = this.nodes[nodeId];
                return node && node.status === 'active' && node.kind !== 'value' ? node : null;
            }
            for (const kid of kids) {
                const leaf = firstActiveLeaf(kid.id);
                if (leaf) return leaf;
            }
            return null;
        };
        let cur = start;
        while (cur) {
            const leaf = firstActiveLeaf(cur);
            if (leaf) return leaf;
            cur = this.nodes[cur]?.parent;
        }
        return null;
    }

    // -- prompt view (INTENT section, ~200 token budget) ---------------------

    info(bot, partner) {
        if (this._expireBlocks()) this.save();
        const lines = ['INTENT (why you are doing what you are doing):'];
        const vals = this.valuesFor(bot);
        if (vals.length) {
            lines.push('You value: ' + vals.map(([t, w]) => `${t} (${w.toFixed(1)})`).join(', '));
        }
        let nodeId = this.active[bot];
        if (!nodeId) {
            // pointerless bot: auto-point at the best open leaf rather than
            // asking the model to recover (era-F showed it fumbles that)
            const leaf = this._nextLeaf(this._missionRoot());
            if (leaf) {
                this.active[bot] = leaf.id;
                nodeId = leaf.id;
                this.save();
            }
        }
        const pathIds = [];
        if (!nodeId) {
            lines.push('No active goal. Add one with !goalAdd.');
        } else {
            const chain = this.path(nodeId).filter(n => n.kind !== 'value');
            chain.forEach((node, depth) => {
                pathIds.push(node.id);
                const marker = node.id === nodeId ? 'NOW:' : '->';
                const why = node.why ? ` - because ${node.why}` : '';
                const anchor = node.anchor ? ` @ (${node.anchor.join(', ')})` : '';
                lines.push(`${'  '.repeat(depth)}${marker} [${node.id}] ${node.title}${anchor}${why}`);
            });
            const parent = chain[chain.length - 1]?.parent;
            if (parent) {
                const sibs = this.children(parent)
                    .filter(c => c.id !== nodeId && c.status === 'active')
                    .sort((a, b) => this.alignment(bot, b.id) - this.alignment(bot, a.id))
                    .slice(0, 3);
                if (sibs.length) {
                    lines.push('Alternatives serving the same parent: ' + sibs.map(s => `[${s.id}] ${s.title}`).join('; '));
                }
            }
        }
        if (partner && this.active[partner]) {
            lines.push(`${partner} is on: ${this.nodes[this.active[partner]].title}`);
        }
        const goal = nodeId ? this.nodes[nodeId].title : null;
        const anchor = nodeId ? this.effectiveAnchor(nodeId) : null;
        return {
            view: lines.join('\n'),
            path: pathIds,
            goal_title: goal,
            site: anchor ? `(${anchor.join(', ')})` : null,
        };
    }
}
