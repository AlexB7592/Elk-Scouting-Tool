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
HEURISTIC_PER_CELL = 0.30, IMPASSABLE = 100000
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

`pipeline/` regenerates everything in `grids/`, `tiles/` and `data/vectors/`
from public APIs. Every source is national and takes a bounding box, so nothing
in it is Colorado-specific.

To build a new unit: edit `pipeline/unit.json` — bounds, slug, grid size,
treeline — and run the scripts in the order in `pipeline/README.md`. No code
changes. Verified by pointing the config at Montana HD 401 and checking the
derived cell size and extent came out right.

**What does not transfer yet:** `cost_grid.png`, `stealth_risk_grid.png` and
`gmu44_elk_probability.pmtiles` are pre-baked for GMU 44 and their generators
were lost before this repo existed. Routing and the hotspot layer will not work
in a new unit until those are rebuilt from the live grids.

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

- **Eye-level first person: tested and closed.** Removed in C12 because a 10 m
  DEM renders as a smooth featureless field at zoom 17. **Retested 2026-09-07
  with real USGS 1 m data — it does not help.** MapLibre's terrain mesh is a
  fixed 128×128 grid per tile (`render/terrain.ts:145`), giving ~3.7 m spacing
  at zoom 17 and ~14.8 m at the zoom 15.4 navigation view, so better source data
  cannot get past it; `meshSize = 256` renders broken. Also verified: **no
  free-camera API** (`FreeCameraOptions` does not exist in its source). Do not
  revisit without a MapLibre change. Numbers in `HANDOFF.md` section 6.
- **1 m DEM is still worth something** — the hillshade is a per-pixel raster
  path, not mesh-limited, and gained +32.9% detail. A deep-zoom hillshade layer,
  not a per-area HD terrain download.
- **Navigation view:** single oblique following camera, pitch 60, zoom 15.4.
- **Ask the Guide house position is restraint** — cow/calf over bugling, back out
  over pushing, because Colorado OTC ground is pressured. The aggressive school
  (Jacobsen, Warren) is preserved under "Other views", never blended away.
- **Scent model:** 400 m hard block, 800 m advisory, only active when a time of
  day is set.
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
