## 2) Core Loop

One-liner: Navigate curved track avoiding oil spills to maintain speed and reach finish.

Steps: (1) Player taps/drags to steer → (2) Car follows finger position → (3) Oil contact slows car 50% for 2s → (4) Speed meter updates with visual feedback.

## 3) Session Flow

0–1s preload → 1–4s tutorial → 4–24s play → 24–30s end card.

States: Preload (assets loaded) → Tutorial (completed turn + oil avoid) → Play (finish reached or 24s timeout) → EndCard.

Persist: speed meter %, distance %, mute state, RNG seed=1337.

## 4) Controls & Input

Tap/drag steering within 100% canvas area.

Thresholds: drag 12px, debounce 80ms, idle timeout 3s.

Hitboxes: CTA minimum 44px, car responsive area 60px radius.

## 5) Mechanics & Rules

Win: Complete 800px track distance in ≤24s. Fail: >24s auto-complete. 

Easy start: straight road 200px, oil spawns after 3s. Hint after 2s idle.

Speed: base 40px/s, oil contact reduces to 20px/s for 2s, max 60px/s.

## 6) Level / Content Data

Track: 5-lane curved path, 800px total length, lanes 80px wide.

Oil spawn: 4-8s intervals, random lanes (exclude player lane), RNG seed 1337.

Speed curve: starts 40px/s, +5px/s every 100px distance, caps 60px/s.

## 7) Tutorial Spec

Step 1: "Drag to steer" (drag detected), 2s.
Step 2: "Avoid oil spills" (oil avoided or hit), 2s.
Fallback: auto-complete after 5s total.

## 8) UI & Layout

9:16 anchor top-left, scale to fit with letterbox. 1:1/16:9 center with black bars.

Font: Arial, UI text 24px, tutorial 28px, max 80% line width.

White text on dark overlay, 4.5:1 contrast, 64px safe margins.

## 9) End Card (CTA)

Logo top-center, bullets: "Epic Racing Action!", "Challenge Friends!", "Download Now!"

4.5-star rating, "PLAY NOW" CTA button. Single mraid.open(clickUrl).

CTA always visible 64px from bottom, button press feedback scale 0.95x.

## 10) Audio

Background music: None specified - use silent/minimal ambient.

SFX events: Oil hit → oil_splash.mp3, Speed boost → engine_rev.mp3.

Load after first input, mute toggle top-right, persist across states.

## 11) Assets & Naming

Player car: car_blue_2.png
Track segments: road_asphalt22.png (straight), road_asphalt03.png (right turn), road_asphalt05.png (left turn)
Track borders: road_asphalt21.png, road_asphalt23.png, road_asphalt04.png, road_asphalt40.png
Obstacles: oil.png
Background: land_sand12.png (off-track areas)

Atlas: 512x512 PNG, 4px padding, PoT format.
Z-layers: background(0), track(1), oil(2), car(3), UI(4).
Est: 180KB pre-zip, 45KB zipped.

## 13) Edge Cases & Policies

Background: pause game, resume on focus. Orientation: letterbox maintain aspect.

Idle: 3s hint arrow → 8s auto-steer → 15s end card transition.

Compliance: sound off default, single CTA tap only, no external API calls.