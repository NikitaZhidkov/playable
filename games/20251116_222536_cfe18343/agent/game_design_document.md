# Mini-GDD: Tic Tac Toe vs AI

## 2) Core Loop

One-liner: Tap board cells to place marks; beat AI within 3 moves or achieve 3-in-a-row.

Steps:
1. Player taps empty board cell → cell highlights
2. System places player mark (X) → checks win/draw
3. If game active, AI places mark (O) → checks win/draw
4. Visual feedback (flash + SFX id: "mark_placed") → meter updates (+20% per valid move)

---

## 3) Session Flow

| Time | State | Entry Rule | Exit Rule | Persist |
|------|-------|-----------|-----------|---------|
| 0–1s | Preload | App init | Assets ready | RNG seed=1337, mute=false |
| 1–3.5s | Tutorial | Preload done | Step 3 complete OR 3.5s elapsed | board state, mute |
| 3.5–22s | Play | Tutorial exit | Win/Lose/Draw OR 22s timeout | board state, move count, mute |
| 22–30s | EndCard | Play end | CTA or timeout | final score, mute |

**State machine:**
- Preload → Tutorial (auto)
- Tutorial → Play (auto, skippable at 3.5s)
- Play → EndCard (win/loss/draw/timeout auto)
- EndCard → (mraid.open only)

**Persist across all:** mute toggle, RNG seed, move history (for replay if needed).

---

## 4) Controls & Input

**Gestures:** Single tap on board cells.

**Active area:** 3×3 grid covering 70–90% canvas width, centered; 44 px minimum hit target per cell (9×9 px grid cells → ~150 px per cell at 1080px width).

**Thresholds:**
- Tap debounce: 120 ms
- Idle timeout for hint: 5 s
- Max idle before auto-lose: 25 s

**Hitboxes:**
- Board cell: min 44×44 px; actual 140×140 px (9:16 device)
- CTA button: 60 px height, 70% canvas width, min safe distance 64 px from bottom edge

---

## 5) Mechanics & Rules

**Win condition:**
- Player achieves 3-in-a-row (horizontal, vertical, diagonal) = WIN (meter +40%, bonus SFX "win")
- Player reaches move #5 without loss = WIN (meter +20%)
- AI achieves 3-in-a-row = LOSE (meter −0%, game over)
- Board fills (9 moves) with no 3-in-a-row = DRAW (meter +10%, end card)

**Fail/Auto-complete rules:**
- AI loses (player wins before move 9): instant end, +40% meter
- Player loses (AI 3-in-a-row): instant end, −0% meter
- Idle 25 s without move: auto-LOSE, end card (meter = final state)
- Reach move 9 without win: DRAW, end card

**Difficulty seeding:**
- Easy start: AI responds randomly first 2 moves (RNG seed)
- Moves 3+: AI uses minimax (optimal) to block/win
- Seed: set RNG seed = 1337 at preload

**Hint logic:**
- Idle 5 s → subtle "?" appears near weakest cell
- Hint does not auto-complete

**Scoring/Meters:**
- Meter range: 0–100%
- Per move: +20%
- Win: +40% (capped at 100%)
- Draw: +10%
- Loss: meter stays at current %
- Win at move 5: instant 100% (5 × 20%)

---

## 6) Level / Content Data

**Layout spec (3×3 grid):**
- Grid cell dims: 140×140 px (9:16 canvas 1080 px wide → 70 px margin left/right, 60 px top, 80 px bottom for CTA)
- Grid coordinates (row, col, 0-indexed):
  - (0,0) @ 70, 60 | (0,1) @ 210, 60 | (0,2) @ 350, 60
  - (1,0) @ 70, 200 | (1,1) @ 210, 200 | (1,2) @ 350, 200
  - (2,0) @ 70, 340 | (2,1) @ 210, 340 | (2,2) @ 350, 340
- Canvas safe area: left/right ≥64 px, bottom ≥64 px for CTA

**Spawn/move table:**
- Turn 0: Player moves (no spawn)
- Turn 1: AI moves (random from remaining cells, seeded)
- Turn 2+: Alternating, minimax logic

**AI move timing:**
- 800 ms delay before AI places mark (UX breathing room)
- Transition anim: 200 ms mark fade-in

---

## 7) Tutorial Spec

**Steps (auto-advance or tap to skip):**

| Step | Copy | Visual | Condition |
|------|------|--------|-----------|
| 1 | "Tap a cell to place your X" | Highlight center cell (1,1) with pulsing glow | 2.5 s OR player taps any cell |
| 2 | "AI plays O. Get 3 in a row to win!" | Show completed center row with X's (fake), AI O in corner | 2.5 s OR player taps confirm |
| 3 | "Ready? Tap to start!" | Show empty board, ready state | Player taps OR 3.5 s total → auto-advance to Play |

**Fallbacks:**
- Idle 2 s in step 1/2 → hint arrow points to next action
- Step 3 auto-skips at 3.5 s total (game starts)

---

## 8) UI & Layout

**Anchors & scaling:**
- **9:16 (portrait, default):** Canvas 1080×1920 px; 3×3 grid 420×420 px, centered
- **1:1 (square):** Canvas 1080×1080 px; grid 350×350 px (scaled down), centered
- **16:9 (landscape):** Canvas 1920×1080 px; grid 420×420 px, centered; letterbox margins left/right ≥64 px
- Font scaling: 1% canvas height per point (responsive)

**Typography:**
- Font family: Arial, sans-serif (system default fallback)
- Title (tutorial): 48 px, weight bold, color #000000
- Label (X/O marks): 72 px, weight bold, color #0066CC (X) / #CC0000 (O)
- Meter label: 24 px, weight normal, color #333333
- CTA label: 32 px, weight bold, color #FFFFFF on #0066CC bg
- Max line width: 80% canvas width

**Color & contrast:**
- Background: #F5F5F5 (light gray)
- Grid lines: #CCCCCC (ratio 4.5:1 vs bg)
- X mark: #0066CC (blue, ratio 7:1 vs white)
- O mark: #CC0000 (red, ratio 5.5:1 vs white)
- Meter fill: #66CC00 (green)
- Text: #000000 (black, ratio 21:1 vs bg)
- CTA bg: #0066CC, text #FFFFFF (ratio 4.8:1)

**Safe areas:**
- Left/right: 64 px margin
- Top: 60 px margin
- Bottom: 80 px (CTA area)

---

## 9) End Card (CTA)

**Components:**
1. Logo: text "Tic Tac Toe AI" (48 px, #0066CC, centered, 20 px from top)
2. Feature bullets (3):
   - "Challenge AI opponent"
   - "Win in 3+ moves"
   - "Master strategy"
   (Each 18 px, left-aligned, 12 px spacing, 40 px from logo)
3. Rating stars: 5 fixed stars (yellow #FFD700), 60 px wide, centered, 20 px spacing from bullets
4. CTA button: 60 px height, 70% canvas width, centered, 64 px from bottom, label "PLAY NOW"

**Behavior:**
- Single mraid.open(clickUrl) on CTA tap
- CTA disabled until end card state entry (3 s delay for UX)
- Visual feedback: button scales to 0.95 on tap, rebounds 100 ms
- CTA always visible within safe area (bottom ≥64 px)
- No re-open if already clicked

---

## 10) Audio

**No audio pack provided; game uses silent/visual-only design.**

If audio desired in future:

| Event | Type | File ID |
|-------|------|---------|
| Background loop | Upbeat electronic, 60–90 BPM | bgm_tictactoe |
| Player mark placed | Pop/click, 200 ms | sfx_mark_placed |
| AI mark placed | Beep, 300 ms | sfx_ai_move |
| Win | Chime/fanfare, 1 s | sfx_win |
| Lose | Buzz/error, 500 ms | sfx_lose |
| Hover cell | Subtle tone, 100 ms | sfx_hover |

**Mute toggle:**
- Icon toggle (top-right corner, 44×44 px, safe area)
- State persisted in localStorage
- Default: **muted** (sound off at launch per policy)
- All SFX paused when muted

**Load policy:** Lazy load after first user input (tap cell).

---

## 11) Assets & Naming

### PixiJS Graphics Primitives

All visual elements created via PixiJS Graphics API; no external image assets required.

#### Board & Grid
- **Grid background:** Rectangle 420×420 px, fill #FFFFFF, stroke #CCCCCC 2 px
- **Grid lines:** 4 Lines (2 horizontal, 2 vertical), stroke #CCCCCC 2 px, spanning grid
- **Cell (empty):** Rectangle 140×140 px, fill #F5F5F5, stroke #CCCCCC 1 px, at grid positions

#### Marks (Player & AI)
- **X mark:** Two diagonal lines, 120 px each, stroke #0066CC 8 px, center of cell, 45° angle
- **O mark:** Circle diameter 120 px, stroke #CC0000 8 px (no fill), center of cell
- **Hover glow (tutorial):** Circle outline, diameter 150 px, stroke #FFD700 3 px, pulsing opacity 0.5–1.0 over 1 s

#### UI Elements
- **Meter background:** Rectangle 300 px wide × 20 px tall, fill #EEEEEE, stroke #999999 1 px, top-left area, 20 px margin
- **Meter fill:** Rectangle (dynamic width, max 300 px) × 20 px, fill #66CC00, animates on move
- **Meter label:** Text "Score: XX%", 24 px Arial, color #333333, left of meter
- **CTA button:** Rectangle 756 px wide (70% of 1080) × 60 px tall, fill #0066CC, rounded corners 8 px, stroke #004499 2 px
- **CTA text:** "PLAY NOW", 32 px Arial bold, color #FFFFFF, center-aligned in button
- **Mute toggle icon:** Circle 44 px diameter, fill #CCCCCC, text icon "🔊" or "🔇" (18 px), top-right, 20 px margin

#### Tutorial Elements
- **Hint arrow:** Polygon (triangle), pointing to recommended cell, 40 px base, fill #FFD700 (yellow), opacity 0.7
- **Tutorial text box:** Rectangle with padding, fill #FFFFFF, stroke #0066CC 2 px, rounded 4 px, shadow (PixiJS filter or overlay dark rect alpha 0.3)

#### Win/Lose State
- **Win line highlight:** Line connecting 3 winning marks, stroke #00CC00 (bright green) 6 px, drawn after win condition
- **Lose overlay:** Semi-transparent Rectangle 1080×1920 px, fill #000000, opacity 0.4, dimmed board effect

### Z-Order Layers (front to back)
1. CTA button & mute toggle
2. Tutorial text & hint arrow
3. Win/lose overlay & line
4. Meter & labels
5. Marks (X/O)
6. Grid & cells
7. Background

### File/Asset Naming Convention
- Primitives generated in-code: `BoardGrid`, `CellRect`, `XMark`, `OMark`, `MeterBar`, `CTAButton`, `HintArrow`, `TutorialBox`
- No external files; all RGB hex colors inline (#RRGGBB format)

### Total Asset Size Estimate
- **Graphics:** 0 KB (all PixiJS primitives, CPU-rendered)
- **Estimated final .zip:** < 50 KB (code only, no images)

---

## 13) Edge Cases & Policies

**Background/Resume:**
- If app backgrounded (visibility hidden), game paused; timer frozen
- On resume (visibility visible), game unpauses; no state loss
- CTA click triggers mraid.open immediately; game state discarded post-click

**Orientation changes:**
- Detect via window.orientationchange or matchMedia
- Rebuild grid layout; letterbox if needed (16:9 portrait → 1:1 or 16:9 landscape)
- Persist board state; no restart
- Transition time: 300 ms re-layout

**Lost focus:**
- Game pauses (AI move timer halted)
- Visual indicator: dim board overlay (opacity 0.2) + "Paused" text
- Resume on refocus (visibility change or click)

**Idle user path:**
- 5 s idle → hint shown ("?" or arrow)
- 10 s idle → subtle "tap to play" message
- 25 s idle → auto-LOSE, end card (no hard quit, UX-friendly)

**Policy compliance:**
- Sound: **OFF by default** (mute toggle, persisted)
- CTA: Single open only; button disabled post-click
- No external HTTP calls except mraid.open(clickUrl) on CTA
- No cookies; localStorage for mute state only (scoped to game domain)
- No microphone, camera, or location requests
- No console errors; all exceptions caught and logged silently

**RNG determinism:**
- Seed set to 1337 at preload
- AI move 1–2: Math.random() seeded (e.g., Alea(1337))
- Move 3+: Minimax deterministic (no randomness)
- Replay possible with seed + move log