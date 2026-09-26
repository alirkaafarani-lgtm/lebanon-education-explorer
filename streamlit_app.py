"""Lebanon Education Explorer — MSBA 325.

A drill-down from governorate to need band to town over the Educational Level –
Lebanon 2023 dataset. The controls are deliberately dependent rather than
independent filters: the governorate selection sets the need slider's range, and
the two together decide which towns the dropdown can offer.
"""

import streamlit as st

from charts import (
    MAP_METRICS,
    governorate_map,
    need_ranking,
    peer_scatter,
    profile_comparison,
)
from data_prep import (
    LEVEL_ORDER,
    add_need_index,
    analysis_frame,
    load,
    quality_report,
    variance_within_governorate,
)

st.set_page_config(
    page_title="Lebanon Education Explorer",
    page_icon="📚",
    layout="wide",
)


@st.cache_data
def get_data():
    full = load()
    return add_need_index(analysis_frame(full)), quality_report(full)


df, quality = get_data()
national = df[LEVEL_ORDER].mean()
within = variance_within_governorate(df)

# ============================================================ sidebar controls
# Defined before the body because the map and every chart depend on them.
st.sidebar.header("Drill down")
st.sidebar.markdown("Region → need band → town.")

all_govs = sorted(df["Governorate"].unique())
selected_govs = st.sidebar.multiselect(
    "1 · Governorate",
    options=all_govs,
    default=["Akkar", "Baalbek-Hermel"],
    help="Sets the peer group. Everything below is rebuilt from this selection.",
)

if not selected_govs:
    st.title("Where is educational need concentrated in Lebanon?")
    st.warning("Select at least one governorate in the sidebar to continue.")
    st.stop()

# First link: the slider's range is recomputed from the governorates chosen
# above, so it always spans exactly what is on screen.
in_govs = df[df["Governorate"].isin(selected_govs)].copy()
lo_need, hi_need = float(in_govs["NeedScore"].min()), float(in_govs["NeedScore"].max())

need_band = st.sidebar.slider(
    "2 · Need score band",
    min_value=lo_need, max_value=hi_need,
    value=(lo_need, hi_need), step=1.0,
    help=f"Range across the {len(in_govs):,} towns in your regions: "
         f"{lo_need:.0f} to {hi_need:.0f}. Narrowing it shortens the town list below.",
)

peers = in_govs[in_govs["NeedScore"].between(*need_band)].copy()
if peers.empty:
    st.title("Where is educational need concentrated in Lebanon?")
    st.warning("No towns fall in that need band. Widen the slider in the sidebar.")
    st.stop()

# Second link: the town options are whatever survived both filters above.
town_options = peers.sort_values("NeedScore", ascending=False)["Town"].tolist()
selected_town = st.sidebar.selectbox(
    f"3 · Town  ({len(town_options):,} available)",
    options=town_options,
    help="Only towns inside the regions and need band above, ordered by need score.",
)
town_row = peers.loc[peers["Town"] == selected_town].iloc[0]

scope_label = (
    selected_govs[0] if len(selected_govs) == 1 else f"{len(selected_govs)} governorates"
)

st.sidebar.divider()
st.sidebar.caption(
    f"**{len(peers):,}** of {len(in_govs):,} towns in scope across "
    f"{len(selected_govs)} governorate{'s' if len(selected_govs) > 1 else ''}."
)

# =================================================================== context
st.title("Where is educational need concentrated in Lebanon?")
st.markdown(
    "Lebanon's education statistics are usually reported by **governorate** — seven "
    "numbers standing in for more than a thousand towns. This page uses the "
    "town-level figures behind those averages to ask whether the governorate is "
    "actually a good guide to any particular place."
)
st.caption(
    f"**Data:** *Educational Level – Lebanon 2023*, from the "
    f"[AUB linked-data portal](https://linked.aub.edu.lb:8502/), published from Impact "
    f"Open Data. One row per town, giving the share of residents at each of seven "
    f"education levels plus a school-dropout rate. **Boundaries:** "
    f"[geoBoundaries](https://www.geoboundaries.org/) (CC BY 4.0). "
    f"**Scope:** {quality['towns_analysed']:,} of {quality['towns_total']:,} towns across "
    f"{quality['governorates']} governorates — {quality['towns_no_data']} report no figures "
    f"and {quality['towns_inconsistent']} have shares that do not sum to 100%, so both "
    f"groups are excluded throughout."
)

# ================================================================== insights
st.subheader("What the town-level data shows")

top120 = df.nlargest(120, "NeedScore")
outside = int((~top120["Governorate"].isin(["Akkar", "Baalbek-Hermel"])).sum())
gov_means = df.groupby("Governorate")["University"].mean()
below_national = (df["University"] < national["University"]).mean() * 100
voc_gap = max(abs(df.groupby("Governorate")["Vocational"].mean() - national["Vocational"]))
corr_illit = df["Illiterate"].corr(df["University"])

m1, m2, m3, m4 = st.columns(4)
m1.metric("Variation NOT explained by governorate", f"{within:.0f}%")
m2.metric("Top-need towns outside the 2 weakest regions", f"{outside / 120 * 100:.0f}%")
m3.metric("Towns below the national average", f"{below_national:.0f}%")
m4.metric("Illiteracy ↔ university attainment", f"r = {corr_illit:.2f}")

i1, i2 = st.columns(2)
with i1:
    st.markdown(
        f"""
**The governorate is a weak guide to any town.** Grouping towns by governorate
explains under a tenth of the differences in university attainment —
**{within:.0f}% of the variation sits between towns inside the same governorate**.
Regional averages span just {gov_means.min():.0f}–{gov_means.max():.0f}%, while
individual towns run from {df['University'].min():.0f}% to {df['University'].max():.0f}%.

**Targeting the weakest regions misses most of the need.** Of the 120 towns with the
largest gap between low attainment and tertiary education, **{outside} fall outside
Akkar and Baalbek-Hermel** — and all seven governorates are represented.
"""
    )
with i2:
    st.markdown(
        f"""
**The average describes almost nobody.** {below_national:.0f}% of towns sit below the
national average of {national['University']:.1f}%, which is pulled upward by a minority
of high-attainment towns rather than describing a typical place.

**Illiteracy points the right way but explains little** — r = {corr_illit:.2f}, roughly
{corr_illit ** 2 * 100:.0f}% of the variation. No single cheap indicator substitutes for
measuring towns directly.

**Vocational training is the exception to the regional pattern**, staying within
{voc_gap:.0f} points of the national average in every governorate while every other
level shifts with the region.
"""
    )

st.divider()

# ======================================================================= map
st.subheader("Where those differences sit")
map_metric = st.radio(
    "Colour the map by",
    options=list(MAP_METRICS.keys()),
    horizontal=True,
    help="Switches the measure shown. Regions selected in the sidebar are outlined.",
)
map_col, note_col = st.columns([3, 2])
with map_col:
    st.plotly_chart(governorate_map(df, map_metric, selected_govs), width="stretch")
with note_col:
    st.markdown(
        f"""
The map is the one view here that is **not** filtered — it always shows all seven
governorates so the selection keeps its national context, with the regions you have
chosen outlined in orange.

Switching between the four measures shows how consistently they move together: the
regions that are dark on *university attainment* are light on *illiteracy* and
*need score*, and the ordering barely changes. That consistency is exactly what makes
the regional story look convincing — and why the town-level charts below, which break
it, matter.

Boundaries come from geoBoundaries. Lebanon split **Keserwan-Jbeil** out of Mount
Lebanon in 2017; this dataset predates that, so both shapes carry the Mount Lebanon
value. **Beirut** is shown unfilled — it has no towns in this dataset.
"""
    )

st.divider()

# =========================================================== live drill-down
st.subheader(f"Drill-down: {selected_town}")
lo, hi = peers["University"].min(), peers["University"].max()
pct = (peers["NeedScore"] < town_row["NeedScore"]).mean() * 100
st.markdown(
    f"**In scope:** university attainment across these {len(peers):,} towns runs from "
    f"**{lo:.0f}%** to **{hi:.0f}%** — a spread of {hi - lo:.0f} points, against a "
    f"peer-group average of {peers['University'].mean():.1f}% and a national average of "
    f"{national['University']:.1f}%. **{selected_town}** sits at "
    f"**{town_row['University']:.0f}%**, with a need score of "
    f"**{town_row['NeedScore']:+.0f}** — higher than {pct:.0f}% of the towns in scope."
)

left, right = st.columns(2)
with left:
    st.plotly_chart(peer_scatter(peers, town_row), width="stretch")
with right:
    st.plotly_chart(
        profile_comparison(town_row, peers, national, scope_label), width="stretch"
    )

st.plotly_chart(need_ranking(peers, town_row), width="stretch")

# ========================================================== justifications
st.divider()
st.subheader("Why these controls")

j1, j2 = st.columns(2)

with j1:
    with st.expander("1 · Governorate — multiselect", expanded=True):
        st.markdown(
            """
**User question.** *"Which part of the country am I looking at, and how do its towns
compare with one another?"* It sets the peer group that every number and every chart
is measured against.

**Why a multiselect.** I considered a single-choice dropdown and a radio group. Both
were rejected because the central finding is a *comparison* — the reader needs Akkar
beside Mount Lebanon to see that their town-level distributions overlap far more than
the regional averages imply, and a single-select makes that impossible without
flipping back and forth from memory. A radio group would also pin seven options
permanently on screen. The multiselect keeps the default narrow while letting the
reader widen to all seven.

**Course concept — providing context.** A town's 12% university attainment means
nothing in isolation. This control supplies the frame of reference: it decides which
towns count as comparable, and therefore what the scatter's cloud and the orange
benchmark bar actually represent.
"""
        )

    with st.expander("3 · Town — dependent dropdown", expanded=False):
        st.markdown(
            """
**User question.** *"Within this group, what is going on in one specific place — and
is it typical of its neighbours or an outlier?"*

**Why a dependent dropdown.** Its options are whatever survived the two filters above,
so it can never offer a town that is not on screen. I considered a free-text search
over all towns, which would break the drill-down: a reader could summon a town from a
region they had filtered out, stranding the highlight outside the scatter's own cloud.
Ordering by need score puts the most interesting cases first rather than burying them
alphabetically.

**Course concept — focusing attention.** Rather than labelling hundreds of points, the
scatter stays clean and this control moves a single highlight through it, while the
profile chart renders detail for exactly one town.
"""
        )

with j2:
    with st.expander("2 · Need score band — range slider", expanded=True):
        st.markdown(
            """
**User question.** *"Within these regions, which towns are in real difficulty — and how
many of them are there?"* It turns a vague "high need" into an explicit threshold the
reader chooses.

**Why a range slider, and how it is linked.** Its bounds are **recomputed from the
governorate selection**: pick Akkar and it spans that region's actual range, not a
fixed −100…+90 scale, so the two ends always correspond to real towns on screen. I
considered a fixed-bound slider and a "top N" number input. The fixed slider was
rejected because most of its travel would be dead space for any single region; "top N"
was rejected because it answers *how many* rather than *how bad*, and hides whether the
tenth town is nearly as bad as the first or nothing like it.

**Course concept — reducing clutter.** It is the control that cuts 910 towns down to a
readable set, and it feeds the town dropdown directly: narrowing the band shortens that
list, which is the middle step of the drill-down.
"""
        )

    with st.expander("Map metric — radio", expanded=False):
        st.markdown(
            """
**User question.** *"Does the regional picture depend on which measure I look at?"*

**Why a radio rather than a dropdown.** There are only four options and the point is to
compare them, so they should all be visible at once; a dropdown would hide the
alternatives behind a click and make switching feel like navigation rather than
comparison. The map deliberately ignores the sidebar filters and always shows all seven
governorates — it is the control that keeps national context on screen while the rest of
the page narrows.

**Course concept — providing context.** It establishes the regional story the
town-level charts then complicate.
"""
        )

# ================================================================== appendix
with st.expander("Data quality and method"):
    st.markdown(
        f"""
The seven education levels are shares of one population and should sum to 100%. They do
for **{quality['towns_analysed']:,}** of {quality['towns_total']:,} towns.
**{quality['towns_no_data']}** report nothing at all and **{quality['towns_inconsistent']}**
are internally inconsistent — one row sums to 13,200, a data-entry error — so both groups
are dropped rather than repaired. A handful of surviving rows leave one level blank while
the other six still sum to ~100; there the blank is treated as a zero share.

The source `refArea` column mixes governorate- and district-level identifiers and
double-encodes non-ASCII characters (`Zahlé` arrives as `ZahlÃ©`); districts are rolled up
to their governorate and the encoding is repaired in `data_prep.py`.

**Need score** = (illiterate % + elementary %) − (university % + higher-education %). Both
halves are shares of the same population, so the difference is already in comparable
percentage points. Positive means more residents stopped at or below elementary school
than reached tertiary education.

Most source values are recorded as round integers (0, 5, 10, 20), which is why the scatter
shows vertical banding and why the need score should be read in bands rather than as an
exact town-by-town ranking.
"""
    )
    st.dataframe(
        peers[["Town", "Governorate"] + LEVEL_ORDER + ["Dropout", "NeedScore"]]
        .sort_values("NeedScore", ascending=False)
        .reset_index(drop=True),
        width="stretch",
        height=300,
    )
