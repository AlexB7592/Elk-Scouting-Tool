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
| `app.html` | MapLibre GL JS rebuild, 165 KB, **build C43** | Active development. |
| `sw.js` | Service worker for offline | Active. `CACHE_VERSION = 'gmu44-v32'` |

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
/data/vectors/       roads_all, trails, streams, water as GeoJSON (2.1 MB, C23)
/fonts/              self-hosted SDF glyph ranges, 204 KB (C41)
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

**Scent-aware routing is a route type, not a switch (C22).** "Route type —
Easiest | Scent-aware" is now the *first* control in the Route sheet, above Start
from, with a plain-language explainer and the time-of-day control revealed only
when it is selected. The action button relabels to "Find scent-safe route" so
what you are about to get is unambiguous. C21 had it as a small toggle under the
start options, which was still too buried for the one feature nothing else has.

**Scent-aware routing is reachable from the Route sheet (C21).** Until C21 it
was **not** — `goRoute` used plain `costAt`, and the only path to a scent-aware
line was generating a full Guide plan. The headline differentiator was
unreachable from the routing screen. There is now a "Scent-aware routing" toggle
in the Route sheet which reveals a time-of-day control; `goRoute` builds the mask
and swaps in `makeScentCostFn`. The route note reports how many cells were
blocked, so you can tell it did something.

Time of day is shared with the Guide (`guideTod`, mirrored by `syncTodSegs`) —
it is a fact about when you are hunting, not about which sheet you are on. The
per-flow choice is only whether to apply the model. The Route toggle defaults
**off** so "easiest route" keeps meaning what it always did.

Verified: same destination, 970 cells blocked under morning thermals, route went
from 12 points to 34 and took a different line.

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

**Main access is emphasis, not a class (C20).** Two bugs made Brush Creek Road
invisible as an artery:

1. Road length was measured *inside the map extent*. Brush Creek runs down from
   Eagle, which sits at ~39.65 N — north of the map's 39.50 edge — so only 1.45
   of its miles were in view and it failed the threshold. True lengths are now
   measured over a wider box (`-107.15,39.05,-106.25,39.80`) and cached in
   `road_true_miles.json`.
2. The C18 dedup **deleted** it. Brush Creek is a Forest Service road inside the
   map, so its USGS copy was dropped — it drew only in its ML colour, never as
   an artery. Eagle-Thomasville lost 80% of its length the same way.

The conceptual error was forcing two independent facts into one class list.
**Maintenance level is how drivable a road is; main access is how you find your
way in.** Brush Creek is both. So arteries now get a **wide dark halo** beneath
whichever class colour they carry (`artery-usfs`, `artery-ntd`, both filtered on
`main`), driven by the same toggle. Tune with `line-opacity` (0.5) and
`line-width` (4.5 -> 12) on those two layers.

Names are seeded by true length >= 6 mi plus explicit Brush Creek spellings —
USGS splits that road across `EAST BRUSH CREEK`, `Brush Creek Rd`,
`Old Brush Creek Rd` and `BRUSH-GYPSUM`, which no single threshold catches.
**This list needs local knowledge to prune; length is a proxy, not the truth.**

**Place names from GNIS (C43).** `data/vectors/places.geojson`, 87 features,
11 KB, behind a "Place names" toggle: 24 summits with elevation, 6 towns,
48 gulches/ridges/basins/flats, 2 ranges, 7 springs. All are point features so
all stay upright on screen. Lakes and reservoirs from GNIS were dropped — NHD
polygons already label those.

Source: `carto.nationalmap.gov/.../geonames/MapServer`, layers 2, 3, 5, 7.
**Its layers are inconsistent:** Landforms and Places return **MultiPoint**
holding one point, Other Hydrographic returns **Point**. Handle both.

**Elevations are sampled, not published.** GNIS no longer carries an elevation
column — the current `DomesticNames_CO.txt` schema dropped `elev_in_ft` — so
onX's figures must be sampled too. Ours come from `elev_grid.png` at the GNIS
coordinate, which means **a summit label always matches what the app reports when
you tap that spot**. They differ from onX by 0–21 ft (Eagle Peak exact, Mount
Thomas +17, Crowley Point −21) because the GNIS point marks the *named place*,
not always the true high point.

**Taking the local maximum instead makes it worse, and was tried:** a 150 m
search put Crowley Point 63 ft high by catching a neighbouring rise. Point
sampling is closer. Do not "improve" this by widening the search.

**Labels follow their layer (C42).** C41 created the label layers and never
wired them to anything, so they ignored the toggles and defaulted to visible —
turn Streams & lakes off and the lake names stayed, floating over hidden water.
Road names follow the Roads master, trail names the trail switch, stream and
lake names the water switch, and all of them now start hidden like the lines
they belong to.

**Rotation threshold raised 1.8 → 2.6.** onX leaves a mildly elongated lake
level — Woods Lake (elongation 1.9) is horizontal in their north-up view — and
only turns the genuinely long ones. At 1.8 we were tilting far more labels than
they do, which reads as busier. **15 of 68 named lakes now rotate**, led by Ruedi
(4.7) and New York Lake (4.2).

**Still missing versus onX, and it is data not styling:** named places. They
label peaks with elevations, towns, trailheads, huts, campgrounds, gulches and
basins, county boundaries along the boundary, mountain ranges along their axis,
private parcels, and contour elevations. We label roads, trails, streams, lakes
and waypoints — nothing else, because we have no other named data. **GNIS (the
USGS Geographic Names Information System) is the single biggest addition**; it
would bring peaks, towns, gulches, basins and summits in one download.

**Labels (C41).** Symbol layers need a `glyphs` URL. There is now one, served
from `/fonts/` in this repo — **204 KB of Noto Sans Regular and Open Sans
Semibold SDF ranges (0-255 and 8192-8447)**, self-hosted because a font CDN
would break offline. Both faces are SIL OFL; `fonts/LICENSE.txt` records that.

**Two label behaviours, which is the whole trick:**

- **Linear features follow their line and turn with the map** —
  `symbol-placement:'line'`, `text-rotation-alignment:'map'`. Road names bend
  along the road, stream names along the stream.
- **Point labels stay upright on screen** —
  `text-rotation-alignment:'viewport'`. Waypoint names are always readable
  however the map is rotated.

A long lake is the middle case. Named waterbodies carry `rot` (their long axis,
by SVD of the outline in metres) and `elong`, computed at build time. Elongated
ones (`elong >= 1.8`) use the axis so the name lies along the water; round ones
stay upright, because an axis through a circle means nothing. Verified: at
bearing 0 "Ruedi Reservoir" (rot 12.1, elong 4.7) is near-horizontal and at
bearing 60 it has turned with the lake, while a waypoint label stays level.

**Bug this surfaced:** NHD returns **uppercase** field names for waterbodies
(`GNIS_NAME`) and **lowercase** for streams (`gnis_name`). The processing kept
lowercase, so every waterbody property was silently dropped — 562 features with
no properties at all, and no lake could be labelled. 68 are named. **Check field
casing per layer, not per service.**

**Row exports confirm where you are (C40).** C39 scrolled the sheet to a status
line at the very bottom, which is worse than no feedback — you press GPX on a
folder and get yanked away from it. Row exports now use a **toast** at the top of
the screen, solid rather than translucent, which covers no control (a sheet can
be 94vh tall, so anything near the bottom lands on a button). The sheet only
scrolls if the copy-out fallback is what actually happened.

**Unnamed waypoints are numbered in GPX.** Names are optional, so three unnamed
camps all exported as "Camp" and nothing importing them could tell them apart.
They now come out as "Camp 1", "Camp 2", "Camp 3" — per type, per export.

**Export had no visible result, and only worked on everything (C39).**

The C37 buttons did produce a file; there was just no way to tell. The status
note sat *below* the buttons, off-screen, and on a phone a blob download often
saves silently. **Getting a file out of a browser fails differently on every
platform, so say which path was taken and never succeed silently.** Now: share
sheet if available, then a download link, and if neither works the text is put
on screen in a textarea with a Copy button. The note moved above the buttons and
scrolls itself into view.

**Export is per-folder and per-type as well as everything.** A `GPX` chip on each
folder row exports that folder's waypoints and routes; one on each type row
exports that type. `gpxBlob(pins, routes)` takes a subset. Verified: folder
export 2 waypoints + 1 route, Glassing export 2 waypoints + 0 routes, everything
3 + 1.

**Not reproducible here:** the original failure was on a device this harness
cannot emulate. The fix is to make the outcome legible rather than to guess at
the cause — if it still does nothing, the on-screen message will now say which
path it tried.

**Pin hit-testing (C38).** C34 used a 28x36 px box offset upward, on the theory
that the teardrop is tall and anchored at its tip. That was over-correcting:
MapLibre already hit-tests against the icon's rendered shape, so the whole
teardrop is a target and the extra box only stole taps meant for the ground
beside a pin. Now ±4 px of finger slop around the tap.

The marker is **34 x 63 CSS px**, which is a large but honest target. Measured:
tapping the tip, the head, or 15 px either side opens the pin; 30 px to the side
or 20 px below the tip gives a dropped point. If it still feels grabby the fix
is a smaller marker, not a smaller hit box.

**Backup, GPX export and restore (C37).** Everything saved lived only in one
phone's `localStorage` — no server, no copy. Organising it well made that worse,
not better. Three buttons at the foot of the Saved sheet:

- **Back up everything** → `gmu44-backup-YYYY-MM-DD.json`, an exact round trip:
  waypoints, folders, routes, and the hidden state of each.
- **Export GPX** → waypoints as `<wpt>`, routes as `<trk>`, for onX, Garmin,
  CalTopo. Folders survive only as a `<desc>` line; hidden state does not survive
  at all, which the UI says.
- **Restore from a backup** → validates the file, then states exactly what will
  be replaced before doing it.

Sharing goes through `navigator.share` with a File where available, falling back
to a download link — on iOS a plain download link often opens the file rather
than saving it.

Verified: backup round-trips exactly through a full wipe (2 waypoints, 1 route,
1 folder, hidden flags and folder references all restored); GPX is well-formed
and escapes `"` and `&` in names; a non-JSON file, a JSON file of the wrong
shape, and a declined confirm all leave the data untouched.

**Still missing:** no sync between devices, and no automatic backup. This is a
manual habit, not a safety net.

**Visibility is a hierarchy, not three switches ANDed (C36).** C30-C35 required
all three switches to agree, which meant a folder you built on purpose could be
overruled by a broad type filter — turn "Camp" off and camps inside a visible
folder vanished. Wrong way round. Now, most specific wins:

1. the waypoint's own switch beats everything
2. if it is in a folder, **that folder decides** — type toggles do not apply
3. only loose waypoints answer to the type toggles

Type rows say "3 saved · 2 in folders · 2 hidden" so it is clear why their
switch does not govern the foldered ones, and row subtitles name whichever
switch is actually hiding a waypoint. Verified: Camp type off leaves the two
foldered camps visible and hides the loose one; folder off hides its contents
regardless; individual hide still wins over both.

**Sheet space and the tab bar (C35).** `.sheet` used to reserve 74px of bottom
padding so content cleared the tab bar, which rendered as a block of empty paper
at the bottom of every sheet. It now sits **above** the tab bar
(`bottom: safe-area + 62px`) with 6px of padding, so no space is wasted.
Coordinates and elevation share one row in the point card. Tab icons went 17px
to 23px with brighter labels.

**Dropping a point now drops a visible marker (C35).** Tapping the map opened
the card but drew nothing, so you could not see where the point had landed. A
dark marker is drawn while the card is open and removed when it closes.

**Folders open to show their contents (C35).** Tapping a folder row expands it to
list its waypoints and its routes; a route gets a Show/Hide chip that draws it.
Rename, delete and the visibility switch all `stopPropagation` so they do not
also open or close the folder.

**Known rough edge:** the sheet drag is functional but a little janky — the
rubber-band divisor and the snap timing have not been tuned.

**Tapping a pin opens that pin (C34).** The map click handler never checked
whether the tap landed on a saved waypoint — it always built a fresh "Dropped
point" at the tap coordinate, so a saved waypoint was unreachable from the map.
It now queries `pts-icon` first. The hit box is deliberately offset upward
(-30/+6 px) because the teardrop is tall and its **tip**, not its middle, is the
position.

The point card has two faces: a dropped point offers "Save as waypoint"; an
existing waypoint shows its type, folder and hidden state, with Rename, Hide/Show
and Delete. Showing a waypoint again clears whatever was hiding it — its own
flag, its type, or its folder — so the button never lies about what it will do.
Verified: rename, hide (2 pins on map → 1), show (→ 2), delete (2 → 1, sheet
closes).

**Waypoint pins are teardrops anchored at the tip (C33).** A circle centred on
the position has to stay small or the location goes vague. A teardrop can be
large — the head carries the symbol, the tip marks the spot — so the marker is
far more visible without losing precision. `icon-anchor` is `bottom`.

**Sheet dragging was broken until C33.** The handler listened for touch events
on the whole sheet, which fought the scrolling body: the browser claimed the
gesture before enough of it had been seen. It now uses **pointer events bound to
the header** (grab handle + title), which is also why it works with a mouse.
Tapping the handle still toggles, guarded so a drag does not also fire the tap.
A downward flick on the list still closes the sheet when it is scrolled to the
top. Verified: drag up → tall, drag down → normal, drag on the title → tall,
tap → toggles.

**Type rows expand (C32).** Each waypoint type in the Saved sheet opens to show
its own waypoints. The flat list of every waypoint underneath is gone — with
types expandable it was a second copy of everything to scroll past. The
visibility switch calls `stopPropagation` so it does not also open the list.

**One Saved surface, folders across both kinds (C31).** The Waypoints tab is now
**Saved** and holds waypoints *and* routes; the saved-routes list moved out of
the Route sheet, which now only builds a route. This is how onX keeps the UI
from bloating: **folders do not live inside each type's screen — there is one
content screen** with folders and type categories side by side.

A folder holds both, because the real grouping is by day or drainage: "Day 3" is
a route plus the glassing points off it. Folder rows read "2 waypoints · 1
route". Both waypoint rows and route rows carry a folder dropdown.

**Folder visibility applies to waypoints only** — a route is drawn one at a time
by loading it, so there is nothing to hide. The row says "waypoints hidden"
rather than implying otherwise.

Deleting a folder still never deletes contents; it now frees routes as well as
waypoints and counts both in the warning. Verified: a folder with 2 waypoints
and 1 route warns "3 items will be kept", and afterwards all 4 pins and both
routes survive with no orphaned folder ids.

**Sheets have two heights (C30).** Normal is `--sheet-max` (62vh); dragging up,
or tapping the grab handle, adds `.tall` (94vh) so a long list is readable.
Dragging down shrinks a tall sheet back, and dragging down again closes it.
Sheets always open at the normal height. Measured 446.4px vs 676.8px on a 720px
viewport.

**Folders (C30).** Waypoints group by folder, which cuts across type — a
drainage, a season, a buddy's spots. `folders` is `[{id,name}]`; a waypoint's
`folder` holds an id, absent means loose. Create, rename and delete from the
Waypoints sheet; **deleting a folder never deletes waypoints**, it moves them
out. Assign from a dropdown on each waypoint row.

**Three independent visibility switches** now, any one of which hides a
waypoint: its folder, its type, or the waypoint itself (`pinVisible`). Tapping a
waypoint row clears whichever one is hiding it rather than appearing dead.
"Show all" clears all three. Verified: 18 pins, hide a 2-pin folder → 16,
assign another pin into that hidden folder → 15, Show all → 18.

Routes do not have folders yet — only waypoints.

**Waypoint symbols are drawn shapes, not font glyphs (C29).** `drawPinSymbol`
paints each type with canvas paths in a -1..1 box. Font glyphs were tried first
and Deadfall's `≠` was nearly invisible at pin size — a character that looks fine
in a chip is not a symbol. Shapes give consistent stroke weight and do not depend
on what the device font contains.

Two rules the set follows: **no two types share a shape** (Deadfall was briefly a
cross, which collided with Location's X, and is now a stack of logs), and Wallow
keeps a basin around its ripple so it does not read as Water. onX was looked at
for convention only — note they use filled silhouettes, which read better at pin
size than strokes if any of these turn out weak on a phone.

**Wallow added** as a 9th type (`#455a64`, basin with a ripple).

**Two independent visibility switches**, matching how onX behaves: `hiddenTypes`
turns a whole type off, `pin.hidden` turns one waypoint off, and a pin draws only
if neither is hiding it (`pinVisible`). The Waypoints sheet lists each type that
has waypoints with a count and its own switch; tapping a row whose type is off
turns the type back on rather than doing nothing. Verified: 18 pins, type off
→ 16, one pin off → 15, Show all → 18 with both kinds of hiding cleared.

**Waypoint symbols on the map, and per-pin visibility (C28).** Each of the 8
types now draws its own symbol on the pin. They are **canvas images registered
with `map.addImage`**, not symbol text: `text-field` needs a `glyphs` URL, this
style has none, and a remote glyph server would break offline.

**The old `pts-label` layer was never added at all** — MapLibre silently
dropped it because of the missing glyphs, so waypoint names have never shown on
the map. Removed. `icon-image` has no glyph dependency, so the browser's own
font draws the character.

Each waypoint carries `hidden`. Tap a row in the Waypoints sheet to show or hide
it (dimmed, swatch hollow, "· hidden" in the subtitle); a master button above the
list flips them all. Go and ✕ call `stopPropagation` so they do not also toggle
visibility, and ✕ now confirms before deleting.

**Still missing: names on the map.** That needs either a self-hosted glyph set
(which would also unlock road and stream labels) or drawing each pin's name into
its own canvas image. Not attempted.

**Entering 3D: tilt before enabling terrain (C27).** Turning terrain on and
easing the pitch in the same breath means MapLibre's collision check runs while
`transform.elevation` is still 0 — it decides the camera is underground and
rewrites the pitch, so the first entry landed at ~53 degrees and only the second
looked right. C19 made this worse by gating the tilt behind `whenTerrainReady`,
which polls for up to six seconds: the control simply looked dead. **Now: relief
on, ease to pitch 62 with terrain still off, then enable terrain 470 ms later.**
Measured 62 degrees at 150 ms, identical on first and second entry.

`terrainExag` lets navigation override the exaggeration slider without the two
fighting over `setTerrain` — the deferred call reads it, and the slider ignores
input while an override is active.

**C23 shipped with a broken Layers sheet.** A slicing edit left a stray
`</div>`, which closed the sheet body early: the road sub-toggles never revealed
and everything below them fell outside the scroll container. It reached the live
site because the check was "do the toggle elements exist?" — they did — and never
"are they visible?". **Verify rendering, not just presence.** Fixed in C25; the
layers sheet now balances 47 `<div>` against 47 `</div>`.

**Auto-start now says what you are being asked to drive (C25).** Access points
carry a 4th field — 0 car, 1 4WD, 2 high clearance, 3 unrated — snapped from
`roads_all.geojson` (99% matched within 60 m). **28% of road access points in
this unit need high clearance.** The route note names the road and its class, and
if it is rougher than a passenger car it adds: park where you stop and recompute
from My position. Filtering candidates by vehicle was built and then removed —
it hid real options, and it failed closed (zero candidates) if a phone still had
an older 3-field access_points.json cached. A missing 4th field now degrades to
"unrated", never to "no candidates".

**C23 threw out the invented classes.** Everything before this described roads
with a vocabulary I made up — "main access roads", promoted by name length.
Nobody had ever measured that, so it could only be checked by someone who had
driven the ground. That does not scale to a unit no one on the team has visited,
which is the whole point of the product.

**Roads are now classified by what you can drive, from surveyed data only:**

| Class | Source of truth | Count |
|---|---|---|
| `car` — passenger car | USFS `oper_maint_level` 3/4/5, or OSM `surface` paved/gravel | 159 |
| `low4wd` — 4WD | OSM `surface` dirt/ground, or the USGS 4WD layer | 217 |
| `high4wd` — high clearance | USFS ML2, or OSM `4wd_only` / `tracktype` grade 4-5 | 94 |
| `unknown` — condition unknown | nobody has rated it | 165 |

Coverage that made this possible: **USFS carries `oper_maint_level` and
`surface_type` on 100% of its 89 roads**; USGS NTD carries **zero** drivability
attributes; OpenStreetMap has a road class on 100% of ways here and a usable
condition tag on about 65% once matched. So USFS is authoritative on its own
roads, OSM fills in the county and public roads, and anything neither has rated
is **labelled unknown rather than guessed**.

That last rule is the important one. *A claim nobody made is a claim nobody has
to verify.* It is what lets this ship for ground the team has never seen.

The three road files were merged into one `roads_all.geojson` (635 features,
0.31 MB) carrying `cls`, `name`, and `ml`/`surf` where the USFS knows them.
Frying Pan Road classifies as `car` from OSM surface tags — derived, not
asserted.

**Rebuild path:** `~/gmu44-scratch/vectors/osm_class.py` pulls OSM via Overpass
and matches it to the shipped geometry; Overpass needs a `User-Agent` header or
it returns 406.

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

**Main access is emphasis, not a class (C20).** Two bugs made Brush Creek Road
invisible as an artery:

1. Road length was measured *inside the map extent*. Brush Creek runs down from
   Eagle, which sits at ~39.65 N — north of the map's 39.50 edge — so only 1.45
   of its miles were in view and it failed the threshold. True lengths are now
   measured over a wider box (`-107.15,39.05,-106.25,39.80`) and cached in
   `road_true_miles.json`.
2. The C18 dedup **deleted** it. Brush Creek is a Forest Service road inside the
   map, so its USGS copy was dropped — it drew only in its ML colour, never as
   an artery. Eagle-Thomasville lost 80% of its length the same way.

The conceptual error was forcing two independent facts into one class list.
**Maintenance level is how drivable a road is; main access is how you find your
way in.** Brush Creek is both. So arteries now get a **wide dark halo** beneath
whichever class colour they carry (`artery-usfs`, `artery-ntd`, both filtered on
`main`), driven by the same toggle. Tune with `line-opacity` (0.5) and
`line-width` (4.5 -> 12) on those two layers.

Names are seeded by true length >= 6 mi plus explicit Brush Creek spellings —
USGS splits that road across `EAST BRUSH CREEK`, `Brush Creek Rd`,
`Old Brush Creek Rd` and `BRUSH-GYPSUM`, which no single threshold catches.
**This list needs local knowledge to prune; length is a proxy, not the truth.**

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

**Saved routes (reworked C19).** Tap a row to draw the route on the map, tap it
again to hide it — there is no Load button, the row is the control. The showing
row is tinted and its subtitle says "showing". Delete asks for confirmation
first. localStorage.

**Route sheet flow (C19).** "Find easiest route" belongs to step 2 only: it is
hidden once a route exists and comes back when the destination, start point or
start mode changes. Note the trap — `refreshPoints()` runs *after* the route is
computed and updates `ptSummary`, so an unconditional show there silently undid
the hide. The show is now conditional on there being no route drawn.

**3D toggle (C19).** Turning 3D on now enables shaded relief by default, and
waits for real terrain elevation before tilting. Previously the first 3D toggle
dropped the camera below the surface for the same reason the nav camera did —
terrain had just been switched on, `transform.elevation` was still 0. Going
2D -> 3D -> 2D -> 3D appeared to fix it only because the second pass had warm
terrain.

**Offline.** Service worker caches app shell, grids, data and libraries on
install. Tools ▸ Offline maps downloads the 7 archives (~140 MB). Range requests
are sliced from the cached full copy into proper 206 responses — this is subtle
and was a real bug.

---

## 5. Open items

| # | Item | Notes |
|---|---|---|
| 1 | Guide stops not tappable | prompts exist in the data, no click handler |
| 1b | Remove **My position** from the dropped-point card | It exists so a tapped point can stand in for a fix. Once live GPS is trusted it is redundant and misleading. Flagged 2026-09-07; kept for now because the simulator still needs it. |
| 2 | Are stops the right idea at all? | they land at 35%/65% of route — a percentage with a hunting word on it |
| 3 | Access points have no road class | **Data now in hand** — `data/vectors/roads.geojson` carries `oper_maint_level`. Drawn in C13; the router does not read it yet. |
| 4 | Line distance tool | stubbed, says "not built yet" |
| 5 | Firebase sync / buddy location | in old build, not ported |
| 6 | ~~GPX export~~ | **Done C37**, plus a full JSON backup and restore |
| 7 | Contours from DEM | would replace scanned-map look |
| 8 | GMU 45 north half | needs quads + DEM for new bounds |
| 9 | Multi-select pins → bulk move to folder | **Alex's idea, 2026-09-08.** Long-press a pin to enter a selection mode (banner appears, selected pins get a ring), tap others to add, then one action files the whole set into a folder. Same gesture Photos/Files use, so it needs no teaching. Deferred until the basemap block is done. Two things to get right: long-press must not fire on a map pan, and the mode needs an obvious exit. |

---

## 5b. The terrain basemap (C44) — how it is generated

`tiles/gmu44_terrain_base.pmtiles`, 15.1 MB, 1489 tiles z8–15, JPEG 512 px.
Replaces nothing: it is a **second** basemap alongside the scanned topo.

Built from NAIP aerial imagery, softened and hillshaded. The whole pipeline is
`~/gmu44-scratch/` + the scratch scripts; the settled parameters are:

```
blur            40 m (ground metres, not pixels)
haze floor      subtract R16 G26 B30, then rescale   <- dark-object subtraction
threshold       0.55      lift everything below this
amount          0.50      gamma applied below the threshold
chroma          1.05      colour re-applied as a RATIO of the new brightness
trust floor     0.22      fade colour out below this brightness
ratio clamp     0.60 .. 1.55
tone            L = 0.18 + L*0.84,  then L *= (0.55 + 0.62*hillshade)
outside extent  #e8e4d9 (the app background)
```

Master mosaic is built on the **z13 tile grid** (5120x4096, 7.39 ground m/px) and
z14/z15 upsample from it. That is not a shortcut: the imagery is deliberately
blurred to ~40 m features and the DEM is 10 m native, so there is no detail below
that to lose.

### Things that were got wrong once, here

- **Lifting brightness additively destroys colour.** Dark conifer is genuinely
  low-chroma in absolute terms (~R40 G55 B45). Adding a constant to lift it keeps
  the colour *difference* fixed while raising the base, so relative saturation
  collapses and everything reads grey. Do the tonal work on **luminance only**,
  then re-apply colour as a ratio of the new luminance. Measured: green-above-grey
  +0.032 additive vs +0.101 ratio, same chroma setting.
- **NAIP has a blue haze floor.** Measured over 21M pixels, blue sits 14 counts
  above red at the dark end (path radiance). Lifting shadows amplifies it into a
  cyan cast. Dark-object subtraction fixes it: blue-above-red +0.082 -> -0.015.
- **Ratio colour explodes on near-black pixels.** After haze removal the darkest
  pixels have near-zero luminance, so colour/luminance is unstable and the lift
  amplifies it into false magenta. Hence the ratio clamp and the trust floor.
  At trust 0.22 strong violet is 0.000%; at 0.10 it is 0.354%.
- **Do not measure violet as `(R+B)/2 - G`.** That flags red rock just as readily
  as violet, and 14% of this unit is red rock. It reported 0.293% "violet" when
  the true figure was 0.0005%. Violet needs **blue above green** as well as red.
- **The green weight must come from the blurred image**, not the raw one, or
  sharp speckle comes back into a basemap whose whole point is softness.
  (Moot now — the green-targeted lift was dropped for a plain brightness
  threshold — but the same trap applies to any masked adjustment.)

### What it does not have

**No contour lines.** They live in the scanned topo raster and nothing in the
imagery reproduces them. Vector contours are the next task; until they land the
topo remains the basemap to pick when you need contours.

### Verification done

- Georeferencing: 77,352 pixels inside the Ruedi Reservoir polygon average
  blue-minus-red **+15.0** and are much darker than land, vs **-0.8** over land.
- Tile coverage is identical to `gmu44_topo.pmtiles` at every zoom, tile for tile.
- Water/land separation **improved**, 0.052 -> 0.107, because the gamma curve
  expands the dark range. Lakes read more distinctly, not less.
- Rendered in the browser: terrain visible, topo hidden, basemaps mutually
  exclusive, relief auto-off over terrain. All five state transitions checked.

**Browser-pane caveat:** the pane renders the map into a 400x300 canvas inside a
1280x720 container, so only a corner of the map appears. Both basemaps do it
identically — it is the harness, not the tiles. Do not chase it.

---

## 5c. The basemap: imagery was the wrong idea (C44 → C46)

C44 built a basemap by softening NAIP aerial imagery, on the theory that onX
does the same. **That theory was wrong**, and it cost two builds.

What disproved it: a zoomed onX screenshot where the canopy has **hard straight
edges and angular corners**. Blurred photography cannot produce a straight edge.
Those are vector landcover polygons.

Chasing it through imagery failed in a specific, instructive way. The complaint
was "too dark", so brightness went 0.40 → 0.80 — and saturation went *up*
(0.091 → 0.156) and it turned acid-green and mottled. Lightness was never the
variable. A photograph carries per-pixel variation and real-world oddities (the
red rock band is genuinely that red); cartography carries flat classified fills.
No amount of tone mapping converts one into the other.

**What actually reproduces it** (C46):

| Ingredient | Source | Size |
|---|---|---|
| landcover class → pale tint | NLCD 2021 via MRLC WMS | 0.8 MB for the unit |
| canopy density → deepens green | NLCD TCC, **palette index IS the percent** | in the same fetch |
| relief | our own DEM, baked at image resolution | free |
| contours | already built in C45 | — |

Two traps worth keeping:

- MRLC's layer lives at the **root** WMS endpoint, not the `mrlc_display`
  workspace. `mrlc_display:mrlc_NLCD_Land_Cover` returns LayerNotDefined; the
  working layer is `NLCD_2021_Land_Cover_L48` at `/geoserver/wms`.
- The tree-canopy PNG is mode `P`, and the **palette index is the canopy
  percent** (correlation −0.99 against palette luminance, index 0 = white =
  bare). Read indices. Do not invert the rendered colours.

Verified before shipping: 99.67% of the unit matched a known NLCD class. A wrong
palette decode would silently paint plausible-but-meaningless colours, so this
assert stays in the build script.

**Canopy density is ours, not theirs.** onX paints forest as one flat polygon.
C46 varies the green with actual canopy percent, so thick timber reads
differently from open park stands on the basemap itself. For an elk map that is
the information, not decoration.

The imagery build was not wasted — it became the **Satellite** basemap, which is
where photography belongs.

---

## 5d. Water had labels but no geometry (found C47)

From C41 until C47 the map drew lake and creek **names** with nothing underneath
them. Only the label layers were ever built; `water-fill`, `water-line` and
`streams` were referenced by the `lWater` toggle but never created.

It stayed hidden because `vis()` is defensive:

```js
function vis(id,on){ if(map.getLayer(id)) map.setLayoutProperty(...); }
```

A missing layer id is silently skipped. The toggle appeared to work, the labels
obeyed it, and nothing ever threw.

This is also the true cause of the "there is a lake on onX that does not exist on
ours" report. That was diagnosed at the time as a rendering, toggle or cache
question, and the data was confirmed present — which was correct but not the
answer. The data was always there. Nothing was drawing it.

**Lesson, and it is the same one as C23:** confirming that an id is referenced is
not confirming that it renders. `queryRenderedFeatures` on the layer is the check
that would have caught this on day one.

---

## 5e. Contours were traced on a grid, and it showed past z15 (C49)

Zoomed well in, the contours had a regular sawtooth. It is in the source
geometry, not the styling and not the tiler (MVT extent is 4096, quantisation
0.23 m). USGS traces contours across DEM cells and the staircase survives:
**6.2% of vertices turned sharper than 35 degrees at a median segment length of
7.8 m.** A smooth curve sampled every ~14 m should essentially never do that.

A first diagnostic tested whether vertices snapped to a 1/3 arc-second lat/lon
graticule. It came back negative, which proved nothing — USGS derives contours
in a projected CRS, so that test could not have detected grid snapping either
way. Turn-angle distribution is the diagnostic that works.

Fixed with **one pass of Chaikin corner cutting, no simplification**:

| | turns >35 deg | mean deviation | worst | vertices |
|---|---|---|---|---|
| original | 5.31% | — | — | 1.00x |
| **1 pass, no simplify** | **0.09%** | **0.098 m** | 5.98 m | 2.00x |
| 1.5 m simplify, 2 pass | 0.07% | — | 4.8 m | 2.27x |
| 4 m simplify, 2 pass | 0.68% | — | 14.1 m | 1.26x |

Chaikin alone is nearly free in accuracy because its new points are placed *on*
the original segments; only the corners round. Every variant that simplified
first moved the line 5–14 m, which on moderate slope approaches half a contour
interval. Do not add a simplify step to save file size — 6 MB is not worth it.

Measure deviation with Hausdorff distance, not point-to-line: the vertices lie
on the original line by construction, so a point-to-line check reports 0.0 m and
tells you nothing.

---

## 5f. Trailheads that look misplaced are not (C51)

Three trailheads sit well off their trail: Mount Thomas 283 m, Tellurium Lake
116 m, Lake Charles 66 m. They read as a projection bug. They are not.

Two measurements settle it:

- **Bearings from trailhead to trail are scattered**, sd 98 degrees. A projection
  or datum error offsets every point in a consistent direction.
- **13 of 15 trailheads sit within 40 m of a road**, including all three
  outliers — Mount Thomas is 7 m from a road and 283 m from its trail.

That is what a parking area looks like. The Forest Service records the
recreation *site*; the trail line is digitised from where the tread begins. The
gap is real ground you walk. The remaining two trailheads are over a kilometre
from any road but 0 m and 25 m from their own trail — backcountry junctions,
not drive-to trailheads. All 15 are anchored to either a road or their trail.

**Do not snap trailheads onto trails.** It would look tidier and would move a
surveyed location to somewhere nobody surveyed. `data/vectors/trail_links.geojson`
draws a connector instead, generated only where the gap exceeds 40 m.

---

## 5g. Habitat layers are live grids, not band pyramids (C52)

Canopy, forage, road distance and elevation ranges ship as three small grids
plus the DEM already in memory, drawn into one canvas overlay that is redrawn
whenever a control moves. **1.3 MB total**, against tens of MB had they been
pre-rendered band pyramids the way the old build did it — and being live, the
bands are adjustable instead of fixed.

MapLibre 5.6 has **no `raster-color`** (that is a Mapbox GL feature), so a
single raster cannot be recoloured by expression. Do not plan around it.

Sources, which are better than the old build had:

- canopy: NLCD tree canopy percent, real per-cell values, 0–77% here
- forage: NLCD land cover crossed with canopy percent. The old model inferred
  "open vs dense conifer"; that split IS canopy density, so now it is measured
- road distance: chamfer transform over the road network

**Road distance must be computed on a buffered extent.** Computed from
in-extent roads only, the farthest cell landed exactly ON the map boundary at
13.2 km, and 21% of the unit was farther from a road than from the edge — a
road just outside would have been nearer. Refetching roads over a 7 km buffer
(2,656 features against 635) and cropping fixes it: worst case 13.2 km -> 9.5
km. Aggregate effect is modest (beyond-2,760 m went 19.2% -> 17.8%) but the
extremes were badly wrong, and those are exactly the cells a security-cover
layer is consulted for.

The grids are a linear lat/lon grid and the map is Web Mercator, so each output
row is resampled from the source row at that row's true latitude. Stretching
straight on misplaces ground by up to 12.4 m mid-extent, 0.6 of a cell.

Redraw costs 24 ms for 2.34M cells, so sliders can be dragged live.

---

## 5h. The forage class names were claims the data never made (C53)

The first cut labelled the classes "prime meadow/riparian", "aspen/shrub",
"open conifer", "dense conifer". Two of those were invented. NLCD says
**grassland/herbaceous** and **deciduous forest**; "meadow" and "aspen" were
species and habitat claims added on top.

Checked against elevation and it mattered:

- **32.5% of "prime meadow" was above 11,500 ft** — alpine tundra, not meadow
- 17.9% of "aspen/shrub" was above 11,500 ft — willow and krummholz

Treeline was **measured, not assumed**: cells with >=25% canopy fall 61% ->
32% -> 9% across the 11,250-11,750 ft bands, so the break is ~11,500 ft.

Meadows do exist at 11,000 ft in Colorado and they are kept. Confirmed with a
neighbourhood test — a meadow is open ground surrounded by timber, tundra is
open ground surrounded by more open ground:

| elevation | trees within 500 m |
|---|---|
| 11,000-11,500 ft | 47% — still park |
| 11,500-12,000 ft | 23% — transitional |
| 12,000 ft+ | 7% — tundra |

Now: Meadow & park, Deciduous & shrub, Open conifer, Dense conifer, Alpine.
"Open conifer" and "dense conifer" were always honest because they are defined
by measured canopy percent.

**LANDFIRE EVT is not usable for names via the map service.** The ImageServer
has no raster attribute table, `identify` needs EPSG:5070 geometry, and the
legend carries labels with no codes. Matching legend swatch colours to the
rendered raster looks like it works — 99.7% coverage — but the palette reuses
colours across 334 classes, so it returned "Southern California Coast Ranges
Cliff and Canyon" for 11% of a Colorado unit. The raw S16 codes from
`format=tiff` ARE authoritative; only the names are missing.

---

## 5i. Four out of five streams on this map are dry in September (C56)

The original NHD fetch kept `ftype` but not `fcode`. FTYPE 460 just means
"StreamRiver". Perennial vs intermittent vs ephemeral lives in **FCODE**:

| fcode | | share of GMU 44 flowlines |
|---|---|---|
| 46007 | ephemeral | 36.6% |
| 46003 | intermittent | 27.9% |
| **46006** | **perennial** | **21.7%** |
| 55800 | artificial path | 12.6% |

Every one of them drew identically from C47 to C55, so the map showed water in
roughly four times as many places as September actually has.

The consequence, measured:

| | median distance |
|---|---|
| to any mapped water | 133 m |
| to **perennial** water | **437 m** |

Ground more than 800 m from real water is **23.3%** of the unit. By the old
all-streams layer it was **1.0%** — a twenty-fold understatement, in a unit both
research documents describe as dry in September, where isolated water
concentrates elk.

**When fetching NHD flowlines, always request `fcode`.** `ftype` alone cannot
tell you whether a creek holds water.

Also added `isolated_water.geojson`: perennial sources ranked by distance to the
next perennial water, the most isolated being 1.6 km from anything else. That
isolation figure is the metric the research points at, and it is not the same as
distance-to-water.

---

## 5j. The router could not tell uphill from downhill (C58)

`stepCost = costFn(nx,ny) * neighbors[n][2]` — cost was a property of the
DESTINATION CELL, so climbing a face and descending it cost exactly the same.
Slope was in there (log cost correlates with slope at **+0.927**) but direction
was not.

Three separate defects, all in that one line:

1. **No direction.** Fixed with Tobler's hiking function on the edge:
   `6*exp(-3.5*|S+0.05|)` km/h. Peak speed is at a **2.9 degree descent**, not on
   the flat. 98.8% of steps are now asymmetric, worst measured ratio **5.94x**.
2. **Cells treated as square.** They are 17.2 m east-west by 22.1 m north-south —
   29% taller than wide. The old `1` and `1.4142` undercharged north-south travel
   and put the diagonal at 24.3 m instead of 28.0 m.
3. **Inadmissible heuristic.** `HEURISTIC_PER_CELL = 0.30` against a 1st
   percentile cell cost of 0.218, so 3.2% of the unit was cheaper than the
   heuristic charged. Measured against Dijkstra, the old router returned routes
   **0.4% above optimal** in both directions — and its in/out difference was that
   noise, not directional intelligence. The new heuristic is
   `(min cell dimension / 1000) / 6.0` = 0.002869 and returns provably optimal
   routes (matches Dijkstra to 4 decimal places).

**Cost is now time in hours**, so routes report "3h 56m" instead of 285
arbitrary units. Measured on one real route: 5.62 mi in climbing 4,119 ft
(3h 56m), 5.60 mi out climbing **9 ft** (2h 55m). The old router made you climb
148 ft on the way out.

`terrain_mult_grid.png` carries ruggedness x brush/deadfall x perennial water
crossings — things the single cost grid folded together. Perennial only, per
HANDOFF 5i.

`cost_grid.png` is still shipped and `costAt` still decodes it; nothing reads it
for routing now. Safe to remove once nothing else references it.

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

> **First: Alex asked (2026-09-07) to be reminded to line up legal protections.**
> The time-sensitive piece is the patent clock — a demo video of an earlier build
> is public on YouTube, US allows ~1 year from first disclosure to file, and most
> other countries have absolute novelty. Find out how long it has been up. Also
> LLC, terms of service with a "planning aid, not a safety device" disclaimer,
> and insurance. He said this is already in progress, so ask what is done first.
> The larger risk is liability, not theft — see section 9.
>
> **Still open from the folders work:** no bulk select / export / import the way
> onX offers — export matters most, since it is also the backup story for data
> that currently lives only in one phone's localStorage. Waypoint symbols are
> strokes; onX uses filled silhouettes, which read better at pin size. Folders
> do not nest.
>
> **Also open: what to do about Guide mode.** Alex is undecided. Note that C22
> moved scent-aware routing into the Route sheet, so removing the Guide would
> no longer cost the feature he actually values.


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
