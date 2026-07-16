// mcft trajectory logger for Mindcraft (deployed into src/agent/ of the
// Mindcraft fork; canonical copy lives in the mcft repo).
//
// Writes one TrajectoryStep JSON line per model turn to
// data/raw/episodes/<episode_id>/steps.jsonl and maintains episode.json,
// matching the mcft schema (src/mcft/schemas). Buffered so it never blocks
// the game loop: flush every 20 steps or 5 seconds.

import { appendFileSync, mkdirSync, writeFileSync } from 'fs';
import { randomBytes, createHash } from 'crypto';
import path from 'path';

const FLUSH_EVERY_STEPS = 20;
const FLUSH_EVERY_MS = 5000;

function newId() {
    return randomBytes(16).toString('hex');
}

function utcNow() {
    return new Date().toISOString().replace('Z', '+00:00');
}

export class McftLogger {
    constructor(agent) {
        this.agent = agent;
        this.episode_id = newId();
        this.step_index = 0;
        this.buffer = [];
        this.last_flush = Date.now();
        this.dir = path.join('data', 'raw', 'episodes', this.episode_id);
        this.started_at = utcNow();
        this._initialized = false;
    }

    _init() {
        mkdirSync(this.dir, { recursive: true });
        this._writeEpisode(null);
        this._initialized = true;
    }

    _writeEpisode(outcome) {
        const episode = {
            id: this.episode_id,
            started_at: this.started_at,
            ended_at: utcNow(), // updated on every flush; final flush wins
            mindcraft_version: null,
            model_id: this.agent.prompter?.chat_model?.model_name || 'unknown',
            persona_id: this.agent.name.toLowerCase(),
            task_id: null,
            outcome: outcome,
            steps_path: path.join(this.dir, 'steps.jsonl'),
        };
        writeFileSync(path.join(this.dir, 'episode.json'), JSON.stringify(episode, null, 2));
    }

    _gameState() {
        const bot = this.agent.bot;
        if (!bot?.entity) return {};
        const inventory = {};
        for (const item of bot.inventory?.items() || []) {
            inventory[item.name] = (inventory[item.name] || 0) + item.count;
        }
        const nearby = Object.values(bot.entities || {})
            .filter(e => e !== bot.entity && e.position.distanceTo(bot.entity.position) < 16)
            .map(e => e.name || e.username || 'unknown')
            .slice(0, 20);
        return {
            position: [bot.entity.position.x, bot.entity.position.y, bot.entity.position.z],
            health: bot.health ?? null,
            hunger: bot.food ?? null,
            time_of_day: bot.time ? String(bot.time.timeOfDay) : null,
            inventory: inventory,
            nearby_entities: nearby,
        };
    }

    // res: full model output; command_name: parsed !command or null;
    // execute_res: command result string or null (null for chat steps).
    logStep(res, command_name, execute_res) {
        try {
            if (!this._initialized) this._init();
            const last = this.agent.prompter?.mcft_last || {};
            let step_type = 'chat';
            if (command_name === '!newAction') step_type = 'code';
            else if (command_name) step_type = 'command';

            let execution_result = null;
            if (command_name) {
                const msg = execute_res == null ? null : String(execute_res);
                const failed = msg !== null && /\b(error|fail|failed|cannot|can't|unable|invalid|timed out)\b/i.test(msg);
                execution_result = { ok: !failed, message: msg };
            }

            const step = {
                episode_id: this.episode_id,
                step_index: this.step_index++,
                timestamp: utcNow(),
                step_type: step_type,
                persona_id: this.agent.name.toLowerCase(),
                system_prompt_hash: createHash('sha256')
                    .update(last.prompt || '', 'utf8').digest('hex'),
                game_state: this._gameState(),
                model_input: last.messages || '[]',
                model_output: res,
                thinking_mode: false, // FAST mode requested via profile (think:false); ADR-0004
                deliberation_trigger: null,
                thinking: null,
                parsed_command: command_name,
                execution_result: execution_result,
                latency_ms: last.latency_ms ?? 0.0,
                reward_signals: {},
            };
            this.buffer.push(JSON.stringify(step));
            const stale = Date.now() - this.last_flush > FLUSH_EVERY_MS;
            if (this.buffer.length >= FLUSH_EVERY_STEPS || stale) this.flush();
        } catch (err) {
            console.warn('mcft_logger: failed to log step:', err.message);
        }
    }

    flush() {
        if (this.buffer.length === 0) return;
        try {
            appendFileSync(path.join(this.dir, 'steps.jsonl'), this.buffer.join('\n') + '\n');
            this.buffer = [];
            this.last_flush = Date.now();
            this._writeEpisode(null);
        } catch (err) {
            console.warn('mcft_logger: flush failed:', err.message);
        }
    }
}
