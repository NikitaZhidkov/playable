## 2) Core Loop

One-liner: Navigate curvy track while avoiding oil spills to maintain speed.

Steps: (1) Player drags car → (2) Car follows finger on track → (3) Hit oil = speed -40%, clean road = speed +10% → (4) Visual slowdown + particles.

## 3) Session Flow

0–1s preload → 1–4s tutorial → 4–24s play → 24–30s end card.

States: Preload (assets loaded) → Tutorial (first turn completed) → Play (finish line reached OR time >20s) → EndCard.

Persist: distance %, speed multiplier, mute state, RNG seed=1337.

## 4) Controls & Input

Drag gesture only; active area 100% of canvas.

Thresholds: drag threshold 12px, debounce 80ms, idle timeout 3s.

Hitboxes: car 44px minimum, CTA 64px minimum.

## 5) Mechanics & Rules

Win: Complete 800px track distance within 20s. Auto-complete: force win at 24s.

Difficulty: Start speed 120px/s, 2 oil spills in first 400px, 4 in second half.

Speed: base 120px/s, oil hit = ×0.6 for 2s, clean road recovery +15px/s per second, cap 180px/s.

## 6) Level / Content Data

Track: 400px wide, 800px total length, 3-lane system (left/center/right at 100px/200px/300px).

Spawn: Oil spills at predetermined positions: (150,100), (250,300), (400,200), (550,100), (650,300), (750,200).

Speed curve: Linear increase from 120px/s to 150px/s over 20 seconds baseline.

## 7) Tutorial Spec

Step 1: "Drag your car left and right!" - show finger drag animation, complete when car moves 50px laterally.

Step 2: "Avoid the oil!" - highlight oil spill, complete when player navigates around first oil.

Fallback: Auto-skip tutorial after 5s idle, show hint after 2s idle.

## 8) UI & Layout

9:16: UI anchored top/bottom 64px safe area. 1:1/16:9: letterbox with UI scaling.

Typography: Arial, title 28px, body 18px, max 70% screen width.

Colors: White text on dark overlay, contrast ratio 6:1, safe area 64px minimum.

## 9) End Card (CTA)

Components: Game logo (top), "Race through challenging tracks!" + "Customize your car!" + "Compete with friends!", 5 stars, "INSTALL NOW" CTA.

Behavior: Single mraid.open(clickUrl), button press feedback, CTA always 64px from edges.

## 10) Audio

SFX: engine_loop.mp3 (continuous), oil_splash.mp3 (oil hit), whoosh.mp3 (lane change).

Load: Lazy after first user input, mute toggle persists across states.

## 11) Assets & Naming

Player car: car_red_4.png
Track straight: road_asphalt22.png  
Track left turn: road_asphalt05.png
Track right turn: road_asphalt03.png
Track borders: road_asphalt21.png, road_asphalt23.png
Oil obstacle: oil.png
Background fill: land_sand12.png

Atlas: 1024×1024 PNG, 4px padding, power-of-two, estimated 180KB pre-zip / 95KB zipped.

Z-layers: background(0) → track(1) → oil(2) → car(3) → UI(4).

## 13) Edge Cases & Policies

Background: Pause game, resume from exact position. Orientation: Letterbox maintain aspect ratio.

Idle: 3s hint arrow → 5s auto-steer demo → 8s auto-complete to end card.

Policy: Sound off default, single CTA open, no external calls, COPPA compliant.