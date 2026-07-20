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
        writeFileSync(tmp, JSON.stringify({ nodes: this.nodes, active: this.active }, null, 1) + '\n');
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

    // -- ops (single entry point, mirrors Python apply_op) -------------------

    applyOp(bot, op, args) {
        try {
            const handlers = {
                goalDone: () => this._opDone(bot, args.reason || ''),
                goalAdd: () => this._opAdd(bot, args.title || '', args.why || '', args.parent_id || ''),
                goalSwitch: () => this._opSwitch(bot, args.node_id || '', args.why || ''),
                block: () => this._opBlock(bot, args.reason || ''),
            };
            const handler = handlers[op];
            if (!handler) return { ok: false, message: `unknown intent op '${op}'` };
            const res = handler();
            if (res.ok) this.save();
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
        const parent = parentId || this.active[bot];
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
            weights: {}, serves_values: {}, status_reason: '',
        };
        this.active[bot] = id;
        return { ok: true, message: `added and switched to: ${title.trim()}`, node_id: id };
    }

    _opSwitch(bot, nodeId, why) {
        const node = this.nodes[nodeId];
        if (!node) return { ok: false, message: `no such goal '${nodeId}'` };
        if (node.kind === 'value') return { ok: false, message: 'cannot work a value directly - pick a goal that serves it' };
        if (node.status !== 'active') return { ok: false, message: `'${node.title}' is ${node.status}` };
        this.active[bot] = nodeId;
        return { ok: true, message: `switched to: ${node.title}`, node_id: nodeId };
    }

    _opBlock(bot, reason) {
        // Code-driven (loop-breaker v3): block the active node, present siblings.
        const nodeId = this.active[bot];
        if (!nodeId) return { ok: false, message: 'no active goal to block' };
        const node = this.nodes[nodeId];
        node.status = 'blocked';
        node.status_reason = reason;
        const sibs = node.parent
            ? this.children(node.parent).filter(c => c.status === 'active')
                  .sort((a, b) => this.alignment(bot, b.id) - this.alignment(bot, a.id)).slice(0, 3)
            : [];
        const nxt = sibs[0] || this._nextLeaf(node.parent);
        if (nxt) this.active[bot] = nxt.id;
        else delete this.active[bot];
        const alts = sibs.map(s => `[${s.id}] ${s.title}`).join('; ');
        const msg = `Your goal '${node.title}' is blocked (${reason}). ` +
            (nxt ? `Now on: ${nxt.title}.` : 'No open goals - add one with !goalAdd.') +
            (alts ? ` Alternatives: ${alts}. Use !goalSwitch to change.` : '');
        return { ok: true, message: msg, node_id: nxt ? nxt.id : null };
    }

    _nextLeaf(start) {
        const firstActiveLeaf = (nodeId) => {
            const kids = this.children(nodeId).filter(c => c.status === 'active');
            if (!kids.length) {
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
        const lines = ['INTENT (why you are doing what you are doing):'];
        const vals = this.valuesFor(bot);
        if (vals.length) {
            lines.push('You value: ' + vals.map(([t, w]) => `${t} (${w.toFixed(1)})`).join(', '));
        }
        const nodeId = this.active[bot];
        const pathIds = [];
        if (!nodeId) {
            lines.push('No active goal. Pick one with !goalSwitch or add one with !goalAdd.');
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
