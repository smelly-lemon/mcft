# EULA / platform / moderation gate — 2026-07-20

Master-plan Phase 1 parallel task. Question: does anything in Mojang's rules,
platform policy, or moderation reality block the eventual monetized show?

**Verdict: GO, with four constraints.** Nothing blocks the planned shape
(free-to-view stream, platform-native monetization, steering as a stream
interaction). One competitor lane is structurally non-compliant, which is
good news for us.

## Minecraft Usage Guidelines (Mojang, consolidated 2024+ version)

Source: minecraft.net/en-us/usage-guidelines (fetched 2026-07-20).

- Streams/videos: allowed, monetizable via ad revenue, if free to view, with
  your own original content/commentary added, no promotion of
  Minecraft-unrelated products, sponsor callouts outside game content and
  all-ages appropriate. An AI-driven show is original content by
  construction - this fits.
- Selling copies of streams/videos: prohibited (we don't plan to).
- Servers: may charge access; may not sell competitive gameplay advantages;
  must provide purchase history for real-currency purchases. Our viewers are
  not players on the server, so the server-monetization section mostly does
  not bind the steering product - but if we ever sell in-world effects to
  *players*, this section applies.
- Artificial scarcity / crypto: the 2024 consolidation explicitly expanded
  guidance against scarcity mechanics and crypto tied to Minecraft.
  **Implication: the ClaudeCraft/CLAUDEMINE memecoin lane is likely
  non-compliant with Mojang's guidelines - our platform-native monetization
  plan is the defensible one.** Do not add tokens/NFT mechanics, ever.

## Platform policy (Twitch precedent)

- No AI-specific prohibition; AI streamers are governed by the same
  Community Guidelines as humans (VTuber enforcement notes are explicit
  precedent). YouTube similar.
- The enforcement risk that actually materializes: **a single bad
  generation**. Neuro-sama's 2023 temporary ban (hateful conduct from an
  unfiltered response) is the canonical case; the fix accepted by the
  platform was an output filter. "Nothing, Forever" (Twitch) had the same
  arc.
- Practical requirements: content classification labels where applicable,
  all-ages posture (matches Mojang requirement anyway), and disclosure that
  the streamers are AI (best practice + emerging regulatory direction).

## The four constraints (binding on the show design)

1. **Every AI-generated string that leaves the system (chat overlay, TTS,
   stream titles) passes an output moderation layer.** No raw model text on
   stream, ever. Implemented as `mcft.moderation` (see below).
2. Free-to-view stream; monetization via platform subs/bits/donations and
   steering perks - never selling stream copies, never selling gameplay
   advantages to server players, never scarcity/token mechanics.
3. All-ages content posture end to end (personas, sponsor callouts, chat).
4. AI disclosure visible on the stream page/overlay.

## Moderation spike (implemented)

`src/mcft/moderation.py`: layered outgoing-text gate.

- Layer 1 (always, ~0ms): normalization + blocklist/pattern screen for
  slurs, sexual content, violence-glorification, doxx-shaped strings
  (emails/phones/addresses), and prompt-injection echo ("ignore previous
  instructions" class). Verdict: allow / redact / block.
- Layer 2 (show mode, async): judge-model screen on a rolling window for
  contextual harms a wordlist misses (harassment-by-implication, hateful
  framing). Budget: Sonnet 5 batch / DeepSeek Flash class, cents per hour.
- Fail-closed: anything erroring in the pipeline renders as a persona-safe
  fallback line, never the raw text.
- Wired into the show overlay/TTS path when that exists (Phase 5); the
  in-game-only era-E chat does not stream anywhere, so no runtime hook yet.

## Open items (non-blocking, revisit at Phase 5)

- Exact framing of paid steering on Twitch (bits-triggered goal insertion vs
  channel-point redemption + subs) - a product choice, not a compliance one;
  all candidate framings are standard stream-interaction mechanics.
- YouTube simulcast policy check if we go multi-platform.
- If the show ever runs a public player-joinable server, re-read the server
  monetization section before charging anyone anything.
