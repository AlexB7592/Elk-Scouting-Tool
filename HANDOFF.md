# GMU 44 Elk Scouting Tool — Project Handoff

Paste this at the start of a new conversation. It is written to be read cold.

---

## 1. What this is

A backcountry elk hunting map for Colorado GMU 44 (White River National Forest,
Frying Pan drainage — Meredith, Thomasville, Mount Thomas, Crowley Point). Built
by one person for his own archery hunt, now being taken toward something
sellable. Two things make it unusual and neither is available in any commercial
app:

1. **Off-trail routing on a terrain cost surface.** A 9-factor model scores every
   17 m cell for how hard it is to walk, and A* finds the cheapest line between
   two points. Not snapped to trails.
2. **Scent-aware routing.** Under draining thermals, cold air follows the same
   paths water does. The router avoids ground whose drainage reaches the animal.

Everything else — waypoints, layers, navigation — is table stakes and should be
built plainly, copying established conventions.

**Repo:** `github.com/alexb7592/Elk-Scouting-Tool`
**Live:** `alexb7592.github.io/Elk-Scouting-Tool/app.html`

---

## 2. Current state

### Two apps, both live

| File | What it is | Status |
|---|---|---|
| `index.html` | Original OpenSeadragon build, 7 MB, build B25 | Frozen. Reference only. Do not add features. |
| `app.html` | MapLibre GL JS rebuild, 120 KB, **build C13** | Active development. |
| `sw.js` | Service worker for offline | Active. `CACHE_VERSION = 'gmu44-v3'` |

`app.html` is the one being worked on. `index.html` stays live because it is the
known-good reference — several bugs were caught by comparing the two.

### Repo layout

```
/app.html            MapLibre build
/index.html          old OpenSeadragon build (frozen)
/sw.js               service worker
/tiles/              PMTiles archives (see below)
/grids/              routing grids as PNG (see below)
/data/               access points + trail topology as JSON
/data/vectors/       roads, trails, streams, water as GeoJSON (1.8 MB, C13)
/GeoPDFs/            4 USGS quads, 208 MB (source material)
/base_topo_files/    old DZI pyramid (source for the topo tiles)
/*_files/            ~30 other DZI pyramids from the old build
```

### Tiles — pushed and live in `/tiles/`

| File | Size | Notes |
|---|---|---|
| `gmu44_topo.pmtiles` | 52.7 MB | USGS quads, JPEG, z8–15 |
| `gmu44_terrain.pmtiles` | 85.5 MB | Terrain-RGB, PNG, z8–14 |
| `gmu44_elk_probability.pmtiles` | 4.5 MB | hotspots |
| `gmu44_canopy_band1–4.pmtiles` | 0.7–3.7 MB | 4 of 6 bands |

Built but **not pushed**: `gmu44_terrain_z11/z12/z13` (smaller variants, only made
because pushing 85 MB was failing). Not needed.

**Not built:** canopy bands 5–6, all forage bands, roaddist bands. Deliberate —
LANDFIRE GeoTIFFs will replace them with real per-cell values.

**Deliberately skipped forever:** `elev_above_*`, `elev_below_*` (12 layers) and
`aspect_*` (4 layers). These are pre-rendered pictures of values MapLibre now
derives live from the DEM.

### Grids — in `/grids/`, loaded into memory at startup

| File | Decode | Purpose |
|---|---|---|
| `cost_grid.png` | **R channel byte only**, 0–255 | terrain cost |
| `elev_grid.png` | `(R*256+G) * 0.25` = feet | elevation |
| `stealth_risk_grid.png` | R channel byte, tier 0–3 | elk-probability risk |

These decodes are **exact and were each got wrong once**. Do not guess them.

### Data — in `/data/`

- `access_points.json` — 3,773 points, `[lat, lon, type]`, type 0 = road (2,768)
- `trails_topology.json` — 139 trails with `pts`, `trailheadStart`, `trailheadEnd`

---

## 3. Critical constants — never re-derive these

```js
var W = 14989, H = 10004;                    // source mosaic size in px
var COST_GRID_W = 1873, COST_GRID_H = 1250;  // same for ELEV_GRID
var GEO_LON0 = -106.8750600, GEO_LAT0 = 39.5000693;   // upper-left
var GEO_LON1 = -106.5003350, GEO_LAT1 = 39.2499693;   // lower-right
var IMPASSABLE = 100000;
var COST_LOG_MIN = Math.log(0.02), COST_LOG_MAX = Math.log(28.35);
var HEURISTIC_PER_CELL = 0.30;
```

Georeferencing validated against Mount Massive (14,411 vs 14,421 published) and
Mount of the Holy Cross (14,004 vs 14,011). Within 10 ft.

`costAt` returns `exp(COST_LOG_MIN + (byte/255) * (COST_LOG_MAX - COST_LOG_MIN))`
→ range 0.020 to 28.35, median 1.275.

---

## 4. Features currently working in `app.html`

**Layout.** Full-screen map, five bottom tabs (Map, Route, Waypoints, Guide,
Tools), each opening a sheet. Swipe down to dismiss. Three round buttons right
edge: 2D/3D, locate, compass rose. Scale bar + live elevation + build tag top-left.

**Tap the map** → point card with coordinates, Copy button, elevation, then
actions: route destination, route start, my position, and save as one of 8
waypoint types (Location, Parking, Glassing, Water, Deadfall, Camp, Sign, Kill
site). Waypoints persist in localStorage.

**Routing.** A* on the cost grid, ~0.4 s typical. Start modes: nearest road
(auto), pick on map, my position. Auto-start uses multi-source Dijkstra outward
from the destination and **stops at the first candidate reached** — provably the
cheapest, and 107× less work than waiting for all of them.

**Guide.** Weapon / season stage / pressure / time of day → picks a posture from
`GUIDE_KB` (locate, full_vocal, cow_calf, silent), builds the scent mask, routes
with the drainage constraint, drops numbered stops, lists plan steps and triggers
with sources.

**Scent model.** `SCENT_HARD_M = 400` (hard block), `SCENT_ADVISORY_M = 800`
(4× cost penalty), `SCENT_CAPTURE_M = 75` lateral, plus a dispersion constant so a
plume spreads like cold air rather than threading one cell like water. Reverse
BFS from a seed ring around the pin; sign flips for midday (rising) vs
morning/evening (draining). Only active when a time of day is set.

**Ask the Guide.** 23 scenarios, 7 categories, filtered by weapon. House position
is **restraint** — cow/calf over bugling, back out over pushing, because Colorado
OTC ground is pressured. Aggressive school (Jacobsen, Warren) preserved under
"Other views" rather than blended away. Position-aware scenarios check whether
you are in the scent block or on the wrong side of the thermal and lead with that.

**Navigation.** Begin route → heading-up oblique camera (pitch 60, zoom 15.4),
distance to go, climb left, next stop with bearing, graded off-route, free look
with Recentre, Ask the guide inline, simulator that walks the route at 12 m/s.
Tab bar stays available; navigation is not a dead end.

**Heading.** Magnetometer when still, GPS course above 0.8 m/s, 8° declination
correction. iOS needs the permission prompt from a tap: Tools ▸ Enable compass.

**Off-route.** Clear under 40 m, amber 40–80 m, alert past 80 m after 3
consecutive fixes, thresholds widen with poor GPS accuracy. Start gate at 50 m
offers reroute-from-here or take-me-to-the-start.

**Vectors (C13).** USFS roads and trails plus NHD streams and lakes, as plain
GeoJSON line/fill layers with two toggles in the Layers sheet. Roads are coloured
and dashed by `oper_maint_level`: ML2 (high-clearance only, 89 in the extent) is
dashed tan so it cannot be mistaken for a drivable road, ML3 mid-brown, ML4/5
dark. Trails dashed rust. **No text labels** — symbol layers need a `glyphs` URL
and this style has none; a remote glyph endpoint would break offline, so that is
a separate decision.

**Saved routes.** Save, list, load, delete. localStorage.

**Offline.** Service worker caches app shell, grids, data and libraries on
install. Tools ▸ Offline maps downloads the 7 archives (~140 MB). Range requests
are sliced from the cached full copy into proper 206 responses — this is subtle
and was a real bug.

---

## 5. Open items

| # | Item | Notes |
|---|---|---|
| 1 | Guide stops not tappable | prompts exist in the data, no click handler |
| 2 | Are stops the right idea at all? | they land at 35%/65% of route — a percentage with a hunting word on it |
| 3 | Access points have no road class | **Data now in hand** — `data/vectors/roads.geojson` carries `oper_maint_level`. Drawn in C13; the router does not read it yet. |
| 4 | Line distance tool | stubbed, says "not built yet" |
| 5 | Firebase sync / buddy location | in old build, not ported |
| 6 | GPX export | in old build, not ported |
| 7 | Contours from DEM | would replace scanned-map look |
| 8 | GMU 45 north half | needs quads + DEM for new bounds |

---

## 6. Eye-level first person — tested and closed

Attempted at pitch 84 / zoom 17, **removed in C12** because a 10 m DEM gives only
~36 elevation samples across a ~360 m screen. The open question was whether the
USGS 1 m DEM would fix it.

**Tested 2026-09-07 on a 3 km patch near Mount Thomas. It does not.**

The blocker is not the data. It is MapLibre's terrain mesh. Verified in the
source of the pinned version (5.6.0):

- `src/render/terrain.ts:145` — `meshSize = 128`. Every terrain tile is a uniform
  128x128 grid built by a flat loop. No adaptive simplification, no LOD.
- `src/source/terrain_source_cache.ts:70` — `deltaZoom = 1`, terrain `tileSize`
  forced to 1024; line 265 clamps the DEM request to the source's `maxzoom`.
- `src/geo/projection/covering_tiles.ts:163` — terrain tile zoom is
  `floor(mapZoom - 1)`.

So mesh spacing = tile width at `floor(mapZoom-1)` / 128. At latitude 39.44 that
is **~3.7 m at zoom 17** and **~14.8 m at zoom 15.4** — coarser, at the navigation
view, than the 10 m data already in use.

Measured with the drape texture held constant so only geometry varied:

| Comparison | Pixels changed | Detail |
|---|---|---|
| 3D geometry, 10 m -> 1 m | 8.5% | +3.1% |
| Hillshade raster, 10 m -> 1 m | **66.5%** | **+32.9%** |
| Geometry, meshSize 128 -> 256 | 38.0% | +9.6% |

The meshSize lever moves geometry **18.8x more** than the data upgrade does. The
mesh is the ceiling, not the DEM.

`map.terrain.meshSize = 256` was tried and **renders broken** — a sawtooth band
across the frame and missing foreground geometry, reproduced after a clean
terrain teardown and rebuild. It is an undocumented private field. Seen in one
configuration only, on tiles with edge-clamped surroundings; would need one more
check on a normally-tiled area before being called a MapLibre bug.

**Do not revisit eye level without a MapLibre change.** Better source data cannot
fix it.

**What 1 m data IS worth.** The hillshade is a per-pixel raster path, not
mesh-limited, and it improved sharply — 66.5% of pixels changed, +32.9% detail.
1 m earns its place as a **deep-zoom hillshade layer**. That is a much smaller
feature than the per-area HD terrain download this plan used to assume.

Not measured: frame rate. The test ran in a headless pane where
`requestAnimationFrame` is frozen and had to be shimmed, so timings reflected CPU
dispatch, not GPU cost. **Any meshSize or 1 m performance claim must be tested on
the actual phone.**

### USGS 1 m DEM — traps found while doing this

Source: `tnmaccess.nationalmap.gov/api/v1/products`, project
`CO_Central_Western_2016`. **31 tiles cover the GMU 44 box**, so full-unit
coverage exists.

- Tiles are **440 MB each** (10012x10012 float32) but internally tiled and LZW
  compressed, so a windowed `/vsicurl/` read pulls only what is needed. The 3 km
  test patch cost **23.7 MB, not 440 MB**.
- **Every overview level in these files is pure nodata.** Full-resolution reads
  are fine. Downsampling through overviews — the obvious way to build lower-zoom
  tiles — returns empty output **without throwing**. Read full-res only.
- CRS is **EPSG:26913 (NAD83 / UTM zone 13N) in metres**; elevations are metres
  with no `VerticalUnits` key present. The app is lat/lon and feet.
- Conversion verified: vs USGS EPQS at 10 points, mean **+0.1 ft**, worst 1.4 ft.
  vs this repo's `elev_grid.png`, mean +2.2 ft, worst 23.6 ft (its cells are
  ~17-22 m, so compare on gentle ground only).

---

## 7. Working agreements

**Verification before shipping.** Every bug in this project came from porting code
without checking what it depended on. Required checks before handing over a file:

- diff anything lifted from `index.html` against the original — decodes,
  constants, every function it calls
- walk the dependency tree of every extracted function
- exercise numeric behaviour, do not assume it
- inspect the data before trusting logic that reads it
- confirm no dangling DOM references
- `node --check` the extracted script

**Bugs this caught, or should have:**
- cost grid decoded as 16-bit `(R*256+G)/100` instead of the R byte → costs
  5 orders of magnitude wrong → 8.8 mi route instead of 4.1 mi
- `COST_LOG_MIN/MAX` not carried over → `costAt` returned `NaN` → search wandered
- `distPointToSegment` not carried over → auto-start threw
- callback signature backwards → all grid loads reported as failures
- `Math.max.apply` over 2.3 M values → stack overflow
- 12 "nearest road" candidates were 7 unique points spanning 791 m → auto-start
  never considered the real trailhead

**Every file handed over gets a commit summary line.**

**Build tag** in the top-left readout. Bump it every build. GitHub Pages plus
browser cache plus service worker means the version on screen often is not the
version just pushed — several rounds were lost to this.

**Communication:** plain language, no jargon without explaining it. Consider
second-order consequences before moving.

**Do not overclaim.** Say what was verified and what was assumed.

---

## 8. Next session plan

**Block 1 (1 m DEM) is done — see section 6. Eye level is closed.** The per-area
HD terrain download idea is dropped; 1 m survives only as a future deep-zoom
hillshade layer.

**Vectors: data in, drawn, not yet wired to the router.** Done in C13 — see
section 4. Sourced from the agencies' own query APIs rather than bulk downloads:
USFS `EDW_RoadBasic_01` and `EDW_TrailNFSPublish_01`, USGS `nhd/MapServer`
layers 6 and 12, all clipped to the box `-106.92 / -106.32 / 39.18 / 39.55`.
That avoided a 631 MB USFS download and a 304 MB state transportation file.
After clipping to the app extent, pruning fields and simplifying to ~3.5 m the
four files are **1.8 MB total**, small enough that plain GeoJSON beats a vector
tile pipeline — no tippecanoe, no new toolchain.

**Still open on vectors:** text labels (needs self-hosted glyphs to stay
offline), and teaching the router to read `oper_maint_level` so an ML2
two-track stops scoring like a maintained road.

**Downloads needed:**

1. **USGS National Map** — Transportation + NHD (hydrography), box
   `-106.92 / -106.32 / 39.18 / 39.55`, Shapefile or GeoPackage.
2. **LANDFIRE** — Forest Canopy Cover + Existing Vegetation Type, GeoTIFF,
   same box.

**Order of work:**

1. **Vectors.** Roads, trails, water as line layers. Then use the road class
   attribute to fix the router's "a 4WD two-track scores like a gravel road"
   gap (open item 3).
2. **LANDFIRE canopy.** Per-cell values fill the reposition scorer's empty
   tiebreak and collapse 4 picture layers into 1.
3. **1 m hillshade** for deep zoom, if it still looks worth it after vectors.
4. **Open list** — stop taps, contours, line distance, GPX export.

**Then:** GMU 45 north half, and the commercial questions (hosting on Cloudflare
R2, terms of service, LLC, insurance).

**Toolchain note.** There is no GDAL, Homebrew, QGIS or Node on this Mac, and no
build scripts in the repo — whatever produced the existing PMTiles and grids was
built elsewhere. A working setup now lives at `~/gmu44-scratch/venv`
(Python 3.9 venv, `rasterio` 1.4.3 with GDAL 3.9.3 bundled, `pmtiles`, `pillow`),
installed with pip only — no Homebrew, no admin password. Delete with
`rm -rf ~/gmu44-scratch`.

---

## 9. Known data gaps — state these plainly to any future user

- No cliff or rock-band data. A route can cross terrain impassable on foot.
- No private land parcels. A route can cross private property.
- No seasonal closures or wilderness motor-vehicle restrictions.
- No water-crossing data.
- No road classification — a 4WD two-track scores like a maintained road.
- The hotspot model does not account for private-land refuge effect, which is
  documented behaviour for the White River herd under pressure.
