# Lebanon Education Explorer

An interactive drill-down through town-level educational attainment in Lebanon,
built with Streamlit and Plotly for **MSBA 325 — Data Visualization**.

**Live app:** _(deployment pending — link goes here)_

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

## The two linked controls

The controls are deliberately dependent rather than independent filters:

1. **Governorate** (multiselect) — sets the peer group.
2. **Town** (dropdown) — **its options are rebuilt from the governorate
   selection.** Choosing Akkar narrows roughly 910 towns to 139, so the reader
   drills down from a region into one place inside it rather than filtering two
   things separately.

Both charts respond: the scatter shows the selected town among its peers, and the
profile chart compares that town against its peer group and the national average.
Each control has an on-page expander explaining the user question it answers, why
that widget was chosen over alternatives considered, and the course concept it
serves.

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
| `streamlit_app.py` | The page: layout, the two linked controls, justifications |
| `charts.py` | The two Plotly figures |
| `data_prep.py` | Loading, cleaning, governorate rollup, need index |
| `Educational_Level-Lebanon-2023.csv` | The dataset |
| `requirements.txt` | Dependencies |
