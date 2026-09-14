# GMU 44 Elk Scouting Tool

Backcountry elk hunting map for Colorado GMU 44 (White River NF, Frying Pan
drainage). Built by one person for his own archery hunt, heading toward a
commercial product.

**Alex is not a developer.** Explain in plain language. Define jargon the first
time. Think through second-order consequences before acting.

## What makes this project unusual

Two things no commercial app does. Everything else is table stakes — build it
plainly, copy established conventions, don't overthink it.

1. **Off-trail routing on a cost surface.** A 9-factor model scores every 17 m
   cell; A* finds the cheapest line. Not snapped to trails.
2. **Scent-aware routing.** Under draining thermals cold air follows the paths
   water does, so the router avoids ground that drains to the animal.

## Active files

- `app.html` — the MapLibre build. **This is the one being worked on.**
- `sw.js` — service worker. Bump `CACHE_VERSION` whenever the shell changes.
- `index.html` — old OpenSeadragon build, **frozen**. Reference only, no features.
  When porting anything from it, diff against it first.

## Constants that must never be re-derived

```js
W = 14989, H = 10004
COST_GRID_W = 1873, COST_GRID_H = 1250        // same for ELEV_GRID
GEO_LON0 = -106.8750600, GEO_LAT0 = 39.5000693   // upper-left
GEO_LON1 = -106.5003350, GEO_LAT1 = 39.2499693   // lower-right
COST_LOG_MIN = Math.log(0.02), COST_LOG_MAX = Math.log(28.35)
HEURISTIC_PER_CELL = (min cell dimension m / 1000) / 6.0   // 0.002869; was 0.30 before C58
IMPASSABLE = 100000
```

Georeferencing validated against Mount Massive and Holy Cross to within 10 ft.

## Grid decodes — each of these was got wrong once

- `cost_grid.png` — **R channel byte only**, 0–255. Not 16-bit.
- `elev_grid.png` — `(R*256 + G) * 0.25` = feet.
- `stealth_risk_grid.png` — R channel byte, tier 0–3.

A wrong decode does not throw. It produces plausible-looking routes that are
badly wrong — an 8.8 mi detour where the answer was 4.1 mi.

## How this project has broken before

Every bug came from porting code without checking what it depended on:

- cost decode guessed instead of read → costs 5 orders of magnitude out
- `COST_LOG_MIN/MAX` not carried over → `costAt` returned NaN
- `distPointToSegment` not carried over → auto-start threw
- callback signature backwards → every grid load reported as a failure
- `Math.max.apply` over 2.3M values → stack overflow
- 12 "nearest road" candidates were 7 duplicate points spanning 791 m

**Before handing over any file:** diff ported code against `index.html`, walk the
dependency tree of every extracted function, exercise numeric behaviour rather
than assuming it, check the data before trusting logic that reads it, confirm no
dangling DOM references, and syntax-check.

## Building another unit

**A new unit is NOT a config change yet.** This file used to say `pipeline/`
regenerates everything in `grids/`. An audit on 2026-09-14 checked which script
writes each grid the app loads, and most have no generator in the repo: the
finished files are committed, but the code that made them lived in session
scratch folders that were later wiped.

| grid | generator |
|---|---|
| canopy, forage, road distance | `make_grids.py` |
| Auto-Scout surface + areas | `autoscout_*.py` — restored 2026-09-14, verified byte-identical |
| **elevation** | none |
| **terrain multiplier** (routing) | `build_cost.py` stops at a scratch `.npy`; the step to the app's PNG is lost |
| **water distance** | none |
| **ownership / private land** | none |
| cost grid | none — **still read**: Guide routing and navigation's off-route reroute call `costAt` |
| stealth risk | none — nothing reads it; it only costs startup time |
| old hotspot layer | none; GMU 44 only, kept as Auto-Scout's reference |

Every data source the pipeline does use is national and takes a bounding box.

**Montana HD 401 was never built.** The earlier note here said it was "verified";
that meant only that `unit.json` derived a sensible cell size and extent once,
and the bounds were not even saved. Before a second unit: write generators for
every grid marked none, get the unit's bounds, then run the pipeline.

**Scratch is not storage.** Anything that produces a committed file goes into
`pipeline/` the same day it is written. Generators have now been lost twice.

**Storage:** git keeps every version of a binary forever. The repo is ~660 MB of
a 1 GB soft ceiling, and a second unit's tiles would be another ~100 MB plus its
rebuild history. A multi-unit product needs tiles hosted outside git — the app
already fetches them by URL, so it is a change to `BASE`, not to the code.

---

## Working agreements

- Bump the **build tag** (top-left readout) every build. GitHub Pages + browser
  cache + service worker means the version on screen is often not the version
  just pushed. Several hours were lost to this.
- Give a **commit summary line** with every file handed over.
- Don't overclaim. Say what was verified and what was assumed.
- Batch small fixes; Alex tests in blocks rather than one bug at a time.

## Settled decisions — do not revisit without reason

- **Ground-level detail: tested and closed.** A 10 m DEM renders as a smooth
  featureless field at zoom 17 (C12), and **real USGS 1 m data does not help**
  (retested 2026-09-07): MapLibre's terrain mesh is a fixed 128×128 grid per tile
  (`render/terrain.ts:145`), ~3.7 m spacing at zoom 17 and ~14.8 m at zoom 15.4,
  whatever the source resolution. `meshSize = 256` renders broken. Do not chase
  near-field detail without a MapLibre change. Numbers in `HANDOFF.md` section 6.
- **First-person camera placement: reopened and built (C76).** This file used to
  say there was no free-camera API because `FreeCameraOptions` does not exist —
  that is Mapbox's name, and the check searched only for it. MapLibre 5.6.0 has
  `calculateCameraOptionsFromCameraLngLatAltRotation` and
  `setCenterClampedToGround`. Measured: placement is exact (0.00 m offset, 0.00 m
  altitude error, pitch held). Two traps, both measured: **always pass roll**
  (omitting it throws inside `jumpTo`) and **clamp pitch to maxPitch before the
  calculation** (88 against 85 put the camera 32 m off and 523 m too high). The
  camera sits over the walker's own ground, so the camera-inside-terrain rewrite
  has nothing to trigger on. It cannot change the mesh: near ground stays smooth;
  ridges and drainages further out are what it shows. **C77 traps, all measured:**
  the call takes its reference height from wherever the map last was, so reset it
  every placement — left alone, walking downhill aimed the view 9.9 km out at
  zoom 10.8 and put the camera under the drawn hill. Cap pitch at 84: above
  ~84.26 MapLibre always aims 10 km out. Never let the solve exceed maxZoom: on
  an 844 px screen a fixed 80 m aim asked for zoom 19.2 and landed the camera
  105 m off, so the solve re-aims instead. And set camera height from the ground
  as DRAWN, not the true ground, or it floats 2,400 m over a flat map when terrain
  is missing. Details: HANDOFF 6.
- **1 m DEM is still worth something** — the hillshade is a per-pixel raster
  path, not mesh-limited, and gained +32.9% detail. A deep-zoom hillshade layer,
  not a per-area HD terrain download.
- **Navigation view:** two, toggled in the nav bar — Follow (oblique, pitch 72 /
  zoom 16.2, C18) and First person (10 m eye height, pitch 82, 55° FOV, C76).
  Both turn with the phone's compass, requested on the Begin route tap.
- **Guide mode is frozen, not extended (2026-09-10).** Alex: "I never quite
  understood how to make the guide mode not seem silly." It stays exactly as it
  is — do not invest in it, do not fix its open items. Guide stops being
  untappable (open item 1) is **closed as won't-fix**; that idea belongs to
  Auto-Scout instead. Auto-Scout is the priority because it replaces the hotspot
  layer, which is the feature this whole project started from.
- **Ask the Guide house position is restraint** — cow/calf over bugling, back out
  over pushing, because Colorado OTC ground is pressured. The aggressive school
  (Jacobsen, Warren) is preserved under "Other views", never blended away.
- **Scent model (rebuilt C60–C63; the 400 m / 800 m cutoffs are gone):** a field
  of how strongly the air at each cell reaches the animal. Connectivity along the
  thermal flow, taking the best branch rather than averaging (averaging broke
  midday, where rising flow diverges), times a power-law dilution on path length:
  core 70.0 m, exponent 1.20, blocked at >= 0.50, ignored below 0.15. No distance limit —
  the plume ends where it fades. Only active when a time of day is set.
- **Weather and live wind are out, deliberately.** The old build fetched
  Open-Meteo current conditions and attached them to pins. It was dropped in the
  port and is staying dropped: the unit has little to no service, so anything
  needing a network call is unavailable exactly when it would matter. The scent
  sheet's "read the actual wind" line is an instruction to the hunter, not a
  promise of data. Do not re-add it and do not file it as a regression — an
  audit on 2026-09-10 flagged it as an accidental loss because this was agreed
  in conversation and never written down.
- **Skipped forever:** `elev_above_*`, `elev_below_*`, `aspect_*` layers. These
  are pictures of values MapLibre now derives live from the DEM.

## Known data gaps — state these plainly, never paper over them

- No cliff or rock-band data; a route can cross terrain impassable on foot.
- No private land parcels; a route can cross private property.
- No seasonal closures or wilderness motor-vehicle restrictions.
- The **router** still ignores road class. The map shows it as of C23
  (passenger car / 4WD / high-clearance / unknown, from USFS `oper_maint_level`
  and OSM surface tags), but the cost grid is pre-baked and does not read it.
- **165 roads are rated by nobody** and are drawn as "condition unknown". That
  is deliberate: never invent a classification, because an invented one can only
  be checked by someone who has driven the ground.
- The hotspot model ignores private-land refuge effect, which is documented
  behaviour for the White River herd under pressure.

## Where things stand

See `HANDOFF.md` in this repo for full current state, the open item list, and the
next-session plan.
