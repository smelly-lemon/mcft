"""Patch Mindcraft with the intent-graph integration (Phase 2, era-F candidate).

Everything lands behind settings.mcft_intent (default FALSE): with the flag
off, prompts, command docs, journals, and logs are byte-identical to era E -
rollback is one toggle. Wiring:

- settings.js + settings_spec.json: the toggle (spec entry required, or the
  mindserver's create-agent allowlist strips the key).
- mindserver.js: loads mcft_intent.json (single writer), serves ops + views
  over two socket events.
- mindserver_proxy.js: agent-side intentOp/intentView with 3s timeout.
- commands/actions.js: !goalDone / !goalAdd / !goalSwitch (instant actions).
- commands/index.js: intent commands hidden from command docs when disabled.
- models/prompter.js: $INTENT placeholder + per-prompt snapshot for logging.
- history.js: journal SITE/GOAL lines regenerated from the graph after each
  summary (journal drift fix: those lines become code-owned).
- agent.js: loop-breaker v3 - on repetition, block the active node and
  present siblings (principled unstuck instead of a bare nudge).
- mcft_logger.js: per-step active goal path (rationale-annotated corpus).

Run AFTER deploying mcft_intent.js to src/agent/. Idempotent per file.
"""

from __future__ import annotations

import json
from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"
MARKER = "mcft intent"


def patch(path: Path, anchor: str, insert: str, before: bool = False) -> bool:
    text = path.read_text(encoding="utf-8")
    if MARKER in text and insert.strip() in text:
        print(f"  = {path.name} already patched")
        return False
    assert text.count(anchor) == 1, f"anchor not unique in {path.name}: {anchor[:60]!r}"
    new = insert + anchor if before else anchor + insert
    path.write_text(text.replace(anchor, new, 1), encoding="utf-8")
    print(f"  + {path.name}")
    return True


# -- 1. settings toggle ------------------------------------------------------

settings = MC / "settings.js"
text = settings.read_text(encoding="utf-8")
if '"mcft_intent"' not in text:
    anchor = '    "max_messages": 75,'
    assert text.count(anchor) == 1
    text = text.replace(
        anchor,
        '    "mcft_intent": false, // mcft intent graph (era F); see ops/patch_intent.py\n'
        + anchor,
        1,
    )
    settings.write_text(text, encoding="utf-8")
    print("  + settings.js toggle")

spec_fp = MC / "src" / "mindcraft" / "public" / "settings_spec.json"
spec = json.loads(spec_fp.read_text(encoding="utf-8"))
if "mcft_intent" not in spec:
    spec["mcft_intent"] = {
        "type": "boolean",
        "description": "mcft: enable intent graph (code-owned goal tree + values)",
        "default": False,
        "required": False,
    }
    spec_fp.write_text(json.dumps(spec, indent=4) + "\n", encoding="utf-8")
    print("  + settings_spec.json entry")

# -- 2. mindserver: graph owner + socket surface ------------------------------

mindserver = MC / "src" / "mindcraft" / "mindserver.js"
text = mindserver.read_text(encoding="utf-8")
if "mcft_intent.js" not in text:
    first_import = text.index("import ")
    text = (
        text[:first_import]
        + "import { IntentGraph } from '../agent/mcft_intent.js'; // mcft intent\n"
        + "let _mcft_graph = undefined; // lazy singleton; mindserver is the single writer\n"
        + "function mcftGraph() {\n"
        + "    if (_mcft_graph === undefined) _mcft_graph = IntentGraph.loadIfPresent();\n"
        + "    return _mcft_graph;\n"
        + "}\n"
        + "function mcftPartner(bot) {\n"
        + "    const g = mcftGraph();\n"
        + "    if (!g) return null;\n"
        + "    return Object.keys(g.active).find(b => b !== bot) || null;\n"
        + "}\n"
        + text[first_import:]
    )
    mindserver.write_text(text, encoding="utf-8")

HANDLERS = """
        // mcft intent: single-writer op + view surface for agents
        socket.on('mcft-intent-op', (agentName, op, args, callback) => {
            try {
                const g = mcftGraph();
                if (!g) { callback?.({ ok: false, message: 'intent graph not loaded' }); return; }
                const bot = String(agentName || '').toLowerCase();
                const res = g.applyOp(bot, op, args || {});
                console.log(`[intent] ${bot} ${op} -> ${res.message}`);
                callback?.(res);
            } catch (e) {
                callback?.({ ok: false, message: 'intent op error: ' + e.message });
            }
        });
        socket.on('mcft-intent-view', (agentName, callback) => {
            try {
                const g = mcftGraph();
                if (!g) { callback?.(null); return; }
                const bot = String(agentName || '').toLowerCase();
                callback?.(g.info(bot, mcftPartner(bot)));
            } catch (e) { callback?.(null); }
        });
"""
patch(
    mindserver,
    "        socket.on('create-agent', async (settings, callback) => {",
    HANDLERS,
    before=True,
)

# -- 3. proxy: agent-side accessors -------------------------------------------

proxy = MC / "src" / "agent" / "mindserver_proxy.js"
PROXY_METHODS = """
    // mcft intent: ops/views against the mindserver graph (3s timeout, never throws)
    _intentEmit(event, payload) {
        return new Promise((resolve) => {
            const timer = setTimeout(() => resolve(null), 3000);
            try {
                this.socket.emit(event, this.name, ...payload, (res) => {
                    clearTimeout(timer);
                    resolve(res);
                });
            } catch (e) { clearTimeout(timer); resolve(null); }
        });
    }
    async intentOp(op, args) {
        return await this._intentEmit('mcft-intent-op', [op, args]);
    }
    async intentView() {
        return await this._intentEmit('mcft-intent-view', []);
    }
"""
patch(proxy, "    getSocket() {", PROXY_METHODS, before=True)

# -- 4. commands ---------------------------------------------------------------

actions = MC / "src" / "agent" / "commands" / "actions.js"
text = actions.read_text(encoding="utf-8")
if "!goalDone" not in text:
    assert "import settings from '../settings.js';" in text
    if "serverProxy" not in text.split("export const actionsList")[0]:
        text = text.replace(
            "import settings from '../settings.js';",
            "import settings from '../settings.js';\n"
            "import { serverProxy } from '../mindserver_proxy.js'; // mcft intent",
            1,
        )
    anchor = "export const actionsList = [\n"
    assert text.count(anchor) == 1
    COMMANDS = """    // mcft intent commands (hidden from docs unless settings.mcft_intent)
    {
        name: '!goalDone',
        description: 'Mark your current intent-graph goal complete.',
        params: {
            'reason': { type: 'string', description: 'One line: how you know it is done.' }
        },
        perform: async function (agent, reason) {
            if (!settings.mcft_intent) return 'Intent graph is disabled.';
            const res = await serverProxy.intentOp('goalDone', { reason });
            return res ? res.message : 'Intent graph unavailable.';
        }
    },
    {
        name: '!goalAdd',
        description: 'Add a subgoal under your current goal (or a given parent) and switch to it.',
        params: {
            'title': { type: 'string', description: 'Short goal title.' },
            'why': { type: 'string', description: 'Why this serves the parent goal.' },
            'parent_id': { type: 'string', description: 'Parent goal id, or empty for current.' }
        },
        perform: async function (agent, title, why, parent_id) {
            if (!settings.mcft_intent) return 'Intent graph is disabled.';
            const res = await serverProxy.intentOp('goalAdd', { title, why, parent_id });
            return res ? res.message : 'Intent graph unavailable.';
        }
    },
    {
        name: '!goalSwitch',
        description: 'Switch your active goal to another open goal by id.',
        params: {
            'node_id': { type: 'string', description: 'Goal id from the INTENT section.' },
            'why': { type: 'string', description: 'Why switch now.' }
        },
        perform: async function (agent, node_id, why) {
            if (!settings.mcft_intent) return 'Intent graph is disabled.';
            const res = await serverProxy.intentOp('goalSwitch', { node_id, why });
            return res ? res.message : 'Intent graph unavailable.';
        }
    },
"""
    text = text.replace(anchor, anchor + COMMANDS, 1)
    actions.write_text(text, encoding="utf-8")
    print("  + actions.js commands")

index = MC / "src" / "agent" / "commands" / "index.js"
text = index.read_text(encoding="utf-8")
if "mcft intent docs gate" not in text:
    if "import settings from '../settings.js';" not in text:
        first_import = text.index("import ")
        text = (
            text[:first_import]
            + "import settings from '../settings.js'; // mcft intent docs gate\n"
            + text[first_import:]
        )
    anchor = (
        "        if (agent.blocked_actions.includes(command.name)) {\n"
        "            continue;\n        }"
    )
    assert text.count(anchor) == 1
    GATE = (
        "\n        // mcft intent docs gate: keep era-E prompts byte-identical\n"
        "        if (!settings.mcft_intent && command.name.startsWith('!goal')"
        " && command.name !== '!goal') {\n"
        "            continue;\n        }"
    )
    text = text.replace(anchor, anchor + GATE, 1)
    index.write_text(text, encoding="utf-8")
    print("  + index.js docs gate")

# -- 5. prompter: $INTENT + snapshot -------------------------------------------

prompter = MC / "src" / "models" / "prompter.js"
text = prompter.read_text(encoding="utf-8")
if "$INTENT" not in text:
    if "serverProxy" not in text.split("async replaceStrings")[0]:
        first_import = text.index("import ")
        text = (
            text[:first_import]
            + "import { serverProxy } from '../agent/mindserver_proxy.js'; // mcft intent\n"
            + text[first_import:]
        )
    anchor = "        if (prompt.includes('$MEMORY'))"
    assert text.count(anchor) == 1
    INTENT_BLOCK = """        if (prompt.includes('$INTENT')) { // mcft intent
            let intent_text = '';
            if (settings.mcft_intent) {
                const info = await serverProxy.intentView();
                if (info?.view) {
                    intent_text = info.view;
                    this.mcft_intent_snapshot = info; // read by mcft_logger per step
                }
            }
            prompt = prompt.replaceAll('$INTENT', intent_text);
        }
"""
    text = text.replace(anchor, INTENT_BLOCK + anchor, 1)
    prompter.write_text(text, encoding="utf-8")
    print("  + prompter.js $INTENT")

# -- 6. history: journal lines from graph --------------------------------------

history = MC / "src" / "agent" / "history.js"
text = history.read_text(encoding="utf-8")
if "mcft intent journal" not in text:
    if "serverProxy" not in text.split("export class History")[0]:
        text = text.replace(
            "import settings from './settings.js';",
            "import settings from './settings.js';\n"
            "import { serverProxy } from './mindserver_proxy.js'; // mcft intent journal",
            1,
        )
    anchor = "        console.log(\"Memory updated to: \", this.memory);"
    assert text.count(anchor) == 1
    JOURNAL_BLOCK = """        // mcft intent journal: SITE/GOAL lines are code-owned when the graph
        // is on - the model cannot drift them (journal-drift fix).
        if (settings.mcft_intent) {
            try {
                const info = await serverProxy.intentView();
                if (info?.goal_title) {
                    const goal_line = `GOAL: ${info.goal_title}`;
                    this.memory = /^GOAL:.*$/m.test(this.memory)
                        ? this.memory.replace(/^GOAL:.*$/m, goal_line)
                        : goal_line + '\\n' + this.memory;
                }
                if (info?.site) {
                    const site_line = `SITE: ${info.site}`;
                    this.memory = /^SITE:.*$/m.test(this.memory)
                        ? this.memory.replace(/^SITE:.*$/m, site_line)
                        : site_line + '\\n' + this.memory;
                }
            } catch (e) { /* graph unavailable: keep model text */ }
        }
"""
    text = text.replace(anchor, JOURNAL_BLOCK + anchor, 1)
    history.write_text(text, encoding="utf-8")
    print("  + history.js journal lines")

# -- 7. agent: loop-breaker v3 ---------------------------------------------------

agent = MC / "src" / "agent" / "agent.js"
text = agent.read_text(encoding="utf-8")
if "loop-breaker v3" not in text:
    anchor = (
        "                console.warn(`${this.name} mcft loop-breaker v2 "
        "(${_mcft_p1 ? 'repeat' : 'alternation'}), removed ${_removed} duplicate turns`);"
    )
    assert text.count(anchor) == 1, "loop-breaker v2 anchor not found"
    V3 = """
                // mcft loop-breaker v3: with the intent graph on, a loop
                // blocks the active node and re-routes to a sibling goal.
                if (settings.mcft_intent) {
                    serverProxy.intentOp('block', { reason: 'repeating the same action' })
                        .then(r => { if (r?.message) this.history.add('system', r.message); })
                        .catch(() => {});
                }"""
    text = text.replace(anchor, anchor + V3, 1)
    agent.write_text(text, encoding="utf-8")
    print("  + agent.js loop-breaker v3")

# -- 8. logger: per-step goal path -----------------------------------------------

logger = MC / "src" / "agent" / "mcft_logger.js"
text = logger.read_text(encoding="utf-8")
if "intent_path" not in text:
    anchor = "                parsed_command: command_name,"
    assert text.count(anchor) == 1
    text = text.replace(
        anchor,
        "                // mcft intent: active goal path at prompt time (null = graph off)\n"
        "                intent_path: this.agent.prompter?.mcft_intent_snapshot?.path ?? null,\n"
        + anchor,
        1,
    )
    logger.write_text(text, encoding="utf-8")
    print("  + mcft_logger.js intent_path")

print("done - toggle stays FALSE until era F")
