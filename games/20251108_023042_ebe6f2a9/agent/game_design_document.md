## 2) Core Loop

One-liner: Navigate turns and avoid oil patches to maintain speed for 15 seconds.

Steps: (1) Player drags to steer → (2) Car follows curved track → (3) Oil avoided, speed maintained → (4) Progress bar fills, time decreases.

## 3) Session Flow

0–1s preload → 1–4s tutorial → 4–22s play → 22–30s end card.

States: Preload (assets loaded) → Tutorial (first turn completed) → Play (15s elapsed = win, 3 oil hits = lose) → EndCard.

Persist: speed meter %, oil hit count, mute state, RNG seed=1337.

## 4) Controls & Input

Gestures: horizontal drag only; active area 100% of canvas width, bottom 70% height.

Thresholds: drag threshold 12px, debounce 80ms, idle timeout 3s.

Hitboxes: car 70x131px, oil 109x95px, CTA minimum 44px.

## 5) Mechanics & Rules

Win: survive 15 seconds without hitting oil 3 times; auto-complete at 25s if still alive.

Fail: hit oil 3 times (speed drops to 20% each hit).

Difficulty: first 5s straight road, then gentle curves; oil spawns every 2–4s after 3s mark.

Speed: starts 100%, -20% per oil hit, recovers +5% per second when clean.

## 6) Level / Content Data

Layout: curved track, 3 lanes (left/center/right), track width 384px.

Spawn table: oil appears lanes 0-2, every 2.0–4.0s intervals starting at t=3s.

Track curvature: sine wave amplitude 80px, frequency 0.3 cycles/second.

RNG seed: 1337 for deterministic oil placement.

## 7) Tutorial Spec

Step 1: "Drag left and right to steer" (finger icon animation), complete on first successful lane change.

Step 2: "Avoid oil patches!" (oil highlight), complete after 2s display.

Fallback: auto-skip tutorial after 6s total; idle hint at 2s per step.

## 8) UI & Layout

Anchors: progress bar top-center, speed meter top-right, car bottom-center.

9:16 scale 1x, 1:1 scale 0.8x centered, 16:9 scale 0.6x letterboxed.

Typography: Arial 24px progress, 18px speed meter, max 60% line width.

Colors: white text on dark background (contrast 7:1), safe area 64px from edges.

## 9) End Card (CTA)

Components: game logo top, "Realistic Racing Physics!" + "100+ Tracks!" bullets, 5 stars, "PLAY NOW" CTA.

Behavior: mraid.open(clickUrl) on tap, button highlight feedback, CTA always in safe area.

Single interaction policy enforced.

## 10) Audio

SFX: engine_loop.mp3 (continuous), oil_splash.wav (oil hit), turn_screech.wav (sharp turns).

Load policy: lazy load after first user input.

Mute toggle top-left, persists across states, default OFF.

## 11) Assets & Naming

Player car: car_red_4.png
Track surface: road_asphalt03.png, road_asphalt04.png, road_asphalt05.png (tiled)
Track borders: land_sand12.png (side barriers)
Oil obstacle: oil.png
Background rocks: rock1.png (scattered decoration)

Additional lanes use road_asphalt21.png, road_asphalt22.png for variety.

Atlas: racing_atlas.png (1024x1024), 4px padding, total ~180KB pre-zip, ~85KB zipped.

Z-order: background(0) → track(1) → oil(2) → car(3) → UI(4).

## 13) Edge Cases & Policies

Background/resume: pause timer, maintain state; orientation changes letterbox with black bars.

Idle path: 3s hint → 5s auto-steer demo → 25s auto-complete → end card.

Compliance: sound off default, single CTA interaction, no external calls during gameplay.

Lost focus pauses game timer and physics updates.