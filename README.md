# Lebanon Education Explorer

An interactive drill-down through town-level educational attainment in Lebanon,
built with Streamlit and Plotly for **MSBA 325 — Data Visualization**.

**Live app: https://lebanon-education-explorer-ark24.streamlit.app/**

## What it shows

Lebanon's education statistics are normally reported by governorate: seven numbers
standing in for more than a thousand towns. This app uses the town-level figures
behind those averages to ask whether the governorate is a useful guide to any
particular place.

Two findings drive the page:

- **Governorate explains under a tenth of the variation.** Grouping towns by
  governorate accounts for only ~9% of the differences in university attainment
  between them — 91% of the variation is between towns *inside* the same
  governorate.
- **55% of the highest-need towns are outside the two weakest governorates.** Of
  the 120 towns with the largest gap between low attainment and tertiary
  education, 66 fall outside Akkar and Baalbek-Hermel, and all seven governorates
  are represented.

## The linked controls

The controls are deliberately dependent rather than independent filters. Each one
narrows the next, so the page drills down — **region → need band → town**:

1. **Governorate** (multiselect) — sets the peer group.
2. **Need band** (range slider) — **its bounds are recomputed from the governorate
   selection**, so both ends always correspond to real towns on screen rather than
   a fixed scale that would be mostly dead space.
3. **Town** (dropdown) — **its options are whatever survived the two filters
   above**, so it can never offer a town that is not on screen. Selecting Mount
   Lebanon and then a need band of +30 and up takes 910 towns → 273 → 17.

A fourth control, a radio, switches the map between four measures.

Each control has an on-page justification covering the user question it answers,
why that widget was chosen over the alternatives considered, and the course
concept it serves.

## The visualizations

| Chart | Driven by | Shows |
|-------|-----------|-------|
| Peer scatter | all three filters | the selected town among its peers, illiteracy × university attainment, coloured by dropout rate |
| Profile comparison | all three filters | the town's seven education levels against its peer group and the national average |
| Need ranking | governorate + need band | the highest-need towns currently in scope, selected town highlighted |
| Governorate map | selection outline only | national context — always all seven regions, so the drill-down keeps its frame of reference |

## Data

*Educational Level – Lebanon 2023*, from the
[AUB linked-data portal](https://linked.aub.edu.lb:8502/), published from Impact
Open Data. One row per town: the share of residents at each of seven education
levels plus a school-dropout rate.

910 of 1,137 towns are used. 196 report no figures and 31 have shares that do not
sum to 100% (one row sums to 13,200 — a data-entry error), so both groups are
excluded rather than repaired. The source `refArea` column mixes governorate- and
district-level identifiers and double-encodes non-ASCII characters (`Zahlé`
arrives as `ZahlÃ©`); both are handled in `data_prep.py`.

## Running locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Files

| File | Purpose |
|------|---------|
| `streamlit_app.py` | The page: layout, the linked controls, justifications |
| `charts.py` | The four Plotly figures |
| `data_prep.py` | Loading, cleaning, governorate rollup, need index |
| `Educational_Level-Lebanon-2023.csv` | The dataset |
| `lebanon_adm1.geojson` | Governorate boundaries ([geoBoundaries](https://www.geoboundaries.org/), CC BY 4.0) |
| `requirements.txt` | Dependencies |

### A note on the boundary file

geoBoundaries follows RFC 7946, which winds polygon exterior rings
counter-clockwise. Plotly's d3-geo interprets a polygon by its winding *on the
sphere*, so a spec-compliant ring renders as "everything except this shape" — one
region floods the canvas and the rest punch holes in it. `charts.py` re-winds the
rings on load; the check is idempotent, so a re-downloaded file works either way.

The file also reflects the 2017 split of Keserwan-Jbeil from Mount Lebanon, which
postdates this dataset — both shapes therefore carry the Mount Lebanon value.
Beirut is left unfilled, as it has no towns in the data.
