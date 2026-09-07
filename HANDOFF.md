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
| `app.html` | MapLibre GL JS rebuild, 128 KB, **build C18** | Active development. |
| `sw.js` | Service worker for offline | Active. `CACHE_VERSION = 'gmu44-v8'` |

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
/data/vectors/       roads, trails, streams, water as GeoJSON (2.1 MB, C14)
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

**Vectors (C13, extended C14).** Two road sources, because neither alone is
enough:

- **USFS National Forest System roads** (89) carry `oper_maint_level`, the
  classification open item 3 needed. Drawn on top, one layer per level.
- **USGS NTD** local roads (642) and 4WD roads (80) underneath. C13 shipped USFS
  only and **Frying Pan Road was missing** — it is an Eagle County road, not a
  Forest Service road, so the USFS dataset does not contain it. Every `105.x`
  feature in the USFS file is a spur *off* it. C14 fixed this.

Plus NHD streams (5,586) and lakes (562). All plain GeoJSON, 2.1 MB total.

**Layers sheet.** "Roads & trails" is a master toggle that reveals a per-class
sub-list — ML4/5, ML3, ML2, 4WD, Other roads, USFS trails — each with its own
switch. The master gates everything, so unchecking it hides all classes whatever
their individual state. "Streams & lakes" is a separate single toggle.

**Styling (reworked in C15).** The first palette was earthy so the lines would
blend with the topo. That was the wrong instinct: nobody turns this layer on to
admire it, they turn it on to answer "how do I get in there?", so it has to jump
off the map. Now a **purple/magenta family with white casings**:

| Class | Colour | Style |
|---|---|---|
| ML4/5 maintained | `#6d28d9` deep violet | solid, thickest |
| ML3 passenger car | `#9333ea` purple | solid |
| ML2 high clearance | `#c026d3` fuchsia | dashed |
| 4WD (USGS) | `#db2777` vivid pink | dashed, tighter |
| Main access roads | `#111827` near-black | solid, thickest |
| Other roads (USGS) | `#78716c` warm grey | solid, thin |
| USFS trails | `#0f766e` deep teal | dashed |

**USGS NTD contains the Forest Service roads as well.** This was got wrong in
C17: promoting the longest named USGS roads swept in Eagle-Thomasville, Ivanhoe
Lake, Hardscrabble, Hat Creek, Jakeman and others that are USFS roads with a
real maintenance class, so they drew black underneath their own classification.
**C18 deduplicates spatially** — any USGS feature whose sampled points are >=60%
within 30 m of a USFS line is dropped, because USFS is authoritative and carries
the class. 175 of 642 local roads and 1 of 80 4WD roads were duplicates. Main
access dropped from 37 names / 258 features to **14 names / 129 features**.
Re-check this whenever either dataset is refreshed.

**Main access roads** are the USGS local roads *remaining after dedup* whose
named segments total >= 2 miles — Frying Pan (23.3 mi), Eagle-Thomasville (20.4), Ivanhoe Lake (17.3),
Hardscrabble (14.3): 37 names, 258 features. These are the roads anyone would be
sent down, and burying them in grey "other roads" was wrong. USGS carries no
usable class of its own here — `tnmfrc` is 4 on all 642 features — so length per
name is the discriminator. Near-black and thickest, standard for a primary road.

Hue choice is deliberate, not taste: **elk probability owns red/orange/yellow and
water owns blue**, so a warm or blue road would read as one of those whenever an
overlay is on. Verified legible with the elk ramp turned on. Every class has a
white casing beneath it (`<id>-case`) so it survives pale topo, dark hillshade
and canopy green alike — the toggle drives both layers.

**No text labels** — symbol layers need a `glyphs` URL and this style has none;
a remote glyph endpoint would break offline, so that is a separate decision.

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

### Navigation camera: MapLibre rewrites your pitch and zoom (C16/C17)

`_elevateCameraIfInsideTerrain` (`ui/camera.ts:1238` in 5.6.0) silently replaces
the requested pitch and zoom whenever it thinks the camera is underground. It is
not clipping or failing — it is *changing the angle you asked for*.

Instrumented locally at the shipping view (pitch 60 / zoom 15.4):

```
camAlt 755 m   minAlt 4077 m   inside=true  ->  pitch 17.8 / zoom 13.90
```

Camera altitude is computed as if the centre were at sea level (`transform.
elevation` still 0), then compared against real terrain **times exaggeration**
(2,912 m x 1.4). Every pitch/zoom combination tested was rewritten, including
the one that ships. So the oblique nav view has probably never been the angle it
claims.

**Caveat, important:** this was measured in a headless harness with a shimmed
`requestAnimationFrame`, where `transform.elevation` never left 0 even after
settling. That may itself be a harness artifact. The mechanism is real and read
from source; the magnitude on a real device is **not confirmed**. Verify on
hardware before building anything further on it.

**Field observation that pinned the cause:** ending a route and immediately
restarting the same one gives a much better camera. The second start works
because the terrain is already warm and `transform.elevation` is populated. So
C18 primes deliberately — `jumpTo` flat over the target first (a flat camera
cannot collide), then wait until **`transform.elevation` is non-zero**, not just
until `queryTerrainElevation` returns a value. The query can read real while the
transform is still 0, which is why the C16 guard was not enough.

Changed in C16/C17/C18: wait for a real terrain elevation before the first nav
camera move; do not stack a second easing on `setDim`'s; re-apply once on `idle`;
and **drop terrain exaggeration to 1.0 while navigating** (1.4 raises the wall
the camera must clear by 40% for no navigational benefit). NAV_VIEW moved to
pitch 72 / zoom 16.2 — the two numbers to tune.

There is no "pass-through" or see-through camera in MapLibre, and there cannot
usefully be one: a camera inside a hill has nothing to draw. The fix is
geometric — keep it above ground — not optical.

### The shaded-relief grid artifact (found C15)

The visible grid mesh over the 3D base is **the hillshade, not the topo scan and
not the terrain mesh**. `gmu44_terrain.pmtiles` renders at **3.69 m/px at z14**
but the source DEM is **10 m**, so it is upsampled 2.7x. Hillshade is a
derivative, so it amplifies the interpolation seams from invisible into a
visible grid. Measured: **28.6% of the hillshade's spectral energy sits in the
10 m band**. Entering 3D auto-enables shaded relief (`app.html`, `setDim`),
which is why it appears to be always on in 3D.

Workarounds today: turn Shaded relief off, or lower `hillshade-exaggeration`
(0.55). The real fix is a DEM whose resolution matches the tiles — which is the
1 m hillshade below. That single change addresses the grid artifact, the topo
scan going soft past its native ~2 m/px, and the measured +32.9% hillshade
detail.

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
offline); teaching the router to read `oper_maint_level` so an ML2 two-track
stops scoring like a maintained road; and possibly splitting trails by motorised
vs non-motorised, since the USFS trail data carries `allowed_terra_use` and
motorised trails are a pressure signal.

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
3. **1 m hillshade** — promoted. It now fixes three separate complaints at once:
   the shaded-relief grid artifact (above), the scanned topo degrading past its
   native resolution at high zoom, and the +32.9% detail measured in section 6.
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
- The **router** still has no road classification. The map now shows it
  (`oper_maint_level`), but the cost model does not read it, so a 4WD two-track
  still scores like a maintained road.
- The **"Other roads" layer (USGS) includes private driveways and ranch access.**
  There is no parcel data to separate them, so a drawn road is not a road you
  may legally use. This is why that class is styled neutral grey and labelled
  "unclassified — some are private" in the Layers sheet.
- **A closed road may simply be absent.** The USFS extract contains no ML1
  (basic custodial care / closed) roads at all, and USGS lists no closed roads
  in this extent. Absence of a line is not evidence of no road.
- The hotspot model does not account for private-land refuge effect, which is
  documented behaviour for the White River herd under pressure.
