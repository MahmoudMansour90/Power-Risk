# Power Risk Index for Data Center Construction Planning (v3)

MOCCI -- interactive Cost and Reliability pillar explorer, built on real EIA-861
data through 2025. Availability (Capacity) and the Composite Power Risk Index
are shown as honest placeholders -- no synthetic or invented numbers for
either, until those pillars have real, validated results.

One page, one URL, with a tab per pillar (Cost / Reliability / Availability /
Composite) -- no separate page URLs to navigate between.

## What's new in v3 vs. the prior app

- **2025 data included.** Cost now runs 2001-2025 with a 2026-2028 forecast;
  Reliability now runs 2013-2025 with a 2026-2028 projection.
- **Cost now carries `Reporting_Utilities`** (utility names serving each
  county-year, largest first), matching Reliability's existing convention.
- **Contiguous U.S. only** -- Alaska and Hawaii are dropped from the shared
  boundary file at prep time, and the map view is cropped to the contiguous
  window so their inset boxes never show.
- **Thicker, darker state borders.**
- **Every year is marked on the map slider**, not just the endpoints -- the
  map is built as a native Plotly animation (one frame per year) specifically
  so the slider labels every step.
- **No "About this data and methodology" section anywhere** -- removed per
  request; backtest scorecards, disclosures, and the CRI 100-ceiling
  explanation are gone from the UI.
- **No 68%/CI-level/likely-range/probability numbers shown anywhere** -- not
  in the hover tooltip, the click panel, or the search panel. Forecast years
  are tagged "(forecast)" only. The shaded uncertainty band stays on the
  trend chart as a visual, with no numeric label attached to it.
- **No confidence grade shown anywhere**, and the "no data" legend is a
  single short line ("Gray = not available (no reporting).").
- **Map click and county search open the same detail panel.** A map click
  shows whichever year the slider was on when clicked; search always opens
  at the latest actual/observed year. Search additionally shows a couple of
  extra fields (national rank, total volume / years of history) that the
  click panel does not.
- **National comparison stat added for Cost** (`Pct_Counties_MoreExpensive_SameYear`,
  computed once in `data_prep.py`), mirroring Reliability's own pre-computed
  `Pct_Counties_Less_Reliable_SameYear`. Both are scoped to observed years only.

## What's in this folder

- `app.py` -- main entry point: password gate, header, scope banner, tabs
- `cost_pillar.py`, `reliability_pillar.py` -- each real pillar's page, as
  its own module so they stay easy to work on independently
- `availability_pillar.py`, `composite_pillar.py` -- honest "not yet
  available" placeholders
- `map_utils.py` -- shared choropleth styling (contiguous-US framing, thick
  state borders, the animated every-year slider, click-to-FIPS/Year
  resolution) used by both real pillars' maps
- `data_prep.py` -- regenerates the files in `data/` from each pillar's
  notebook outputs (run this again whenever a pillar's underlying data is
  refreshed) -- see the top of that file for the exact input filenames
- `data/` -- the static data snapshot the app actually loads: parquet files
  per pillar, plus `counties_fips.json` (contiguous-US-only county boundary
  file, includes Connecticut's 2022+ planning regions)
- `assets/mocci_logo.png` -- the MOCCI logo (password screen + header)
- `.streamlit/secrets.toml.example` -- template for the password secret
- `requirements.txt`

## Password protection

Gated by a single shared password, checked against `st.secrets["app_password"]`.
The real password is never stored in this folder or in source control --
only `secrets.toml.example` (a template) is included.

**Local run:** copy `.streamlit/secrets.toml.example` to
`.streamlit/secrets.toml` and put a real password in it. That file is
already in `.gitignore`.

**Streamlit Community Cloud:** no `secrets.toml` file needed in the repo.
After deploying, go to the app's **Settings -> Secrets** and paste:
```
app_password = "your real password here"
```

## Deploy to Streamlit Community Cloud

1. Create a new GitHub repository and push everything in this folder to it
   (the `data/` folder and logo included).
2. Go to https://share.streamlit.io/, connect your GitHub account.
3. Select the repository, branch `main`, main file path `app.py`, deploy.
4. Set the password in the app's Secrets before sharing the link.

## Run locally

```
pip install -r requirements.txt
streamlit run app.py
```

## Updating a pillar's data later

Each pillar's notebook is the source of truth; this app never recomputes
anything, only reshapes and displays what the notebook already validated.

1. Rerun the relevant pillar's notebook, producing fresh output files.
2. Place those fresh files alongside `data_prep.py` (see the paths at the
   top of that script).
3. Run `python3 data_prep.py` -- it regenerates every file in `data/`.
4. Commit and push the updated `data/` files. Streamlit Community Cloud
   redeploys automatically.

## A verification note on the maps

Plotly's `scope='usa'` choropleth (used for both pillar maps) loads its base
US geography from `cdn.plot.ly` at runtime, in the browser -- this is how
Plotly's geo module works for every deployment, not something specific to
this app. In the sandboxed environment this app was built in, that CDN host
is blocked by the sandbox's own network policy, so the maps could not be
rendered or visually inspected there. Everything else -- the year slider
(confirmed to mark and label every year), the search box, the click/search
detail panel (confirmed for observed years, forecast years, the "no data
this year" case, and the "not enough history to project" case), and the
comparison table -- was verified directly in a running instance of this app.
Please confirm once deployed (or running locally with real network access)
that: the map itself renders with visible, contiguous-US-only county shapes;
Alaska/Hawaii do not appear, including no empty inset boxes; state borders
read clearly; and a map click opens the correct county's detail panel. None
of these depend on anything unusual -- they use the same `scope='usa'`
technique as the prior version of this app -- but they could not be
confirmed firsthand here.

## Adding the Availability pillar or the Composite index later

Follow the same pattern as Cost and Reliability: once that pillar has a
validated notebook output, extend `data_prep.py` to export it, write a new
`availability_pillar.py` (or replace the composite placeholder) following
`reliability_pillar.py` as the template, and wire it into the matching tab
in `app.py` in place of the current placeholder import.
