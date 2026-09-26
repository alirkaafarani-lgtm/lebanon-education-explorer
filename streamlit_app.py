"""Lebanon Education Explorer — MSBA 325.

A drill-down from governorate to town over the Educational Level – Lebanon 2023
dataset. The two controls are deliberately dependent: the governorate selection
rebuilds the town list, so the reader narrows a region and then inspects one
place inside it, rather than filtering two things independently.
"""

import pandas as pd
import streamlit as st

from charts import peer_scatter, profile_comparison
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
    scored = add_need_index(analysis_frame(full))
    return full, scored, quality_report(full)


full, df, quality = get_data()
national = df[LEVEL_ORDER].mean()
within = variance_within_governorate(df)

# --------------------------------------------------------------------- context
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
    f"education levels plus a school-dropout rate. "
    f"**Scope:** {quality['towns_analysed']:,} of {quality['towns_total']:,} towns across "
    f"{quality['governorates']} governorates — {quality['towns_no_data']} towns report no "
    f"figures and {quality['towns_inconsistent']} have shares that do not sum to 100%, "
    f"so both groups are excluded throughout."
)

st.subheader("Two things the town-level data shows")
c1, c2 = st.columns(2)
with c1:
    st.metric("Variation the governorate does NOT explain", f"{within:.0f}%")
    st.markdown(
        "Grouping towns by governorate accounts for under a tenth of the differences "
        "in university attainment between them. **Knowing a town's governorate tells "
        "you very little about the town** — which is what the scatter below makes "
        "visible: the dots spread far wider than any regional average suggests."
    )
with c2:
    top = df.nlargest(120, "NeedScore")
    outside = int((~top["Governorate"].isin(["Akkar", "Baalbek-Hermel"])).sum())
    st.metric("Highest-need towns outside the two weakest governorates",
              f"{outside / 120 * 100:.0f}%")
    st.markdown(
        f"Of the 120 towns with the largest gap between low attainment and tertiary "
        f"education, **{outside} sit outside Akkar and Baalbek-Hermel**, and all seven "
        f"governorates are represented. Targeting the two weakest regions would miss "
        f"most of the places that score worst."
    )

st.divider()

# ------------------------------------------------------- the two linked controls
st.sidebar.header("Drill down")
st.sidebar.markdown("Pick a region, then a town inside it.")

all_govs = sorted(df["Governorate"].unique())
selected_govs = st.sidebar.multiselect(
    "1 · Governorate",
    options=all_govs,
    default=["Akkar", "Baalbek-Hermel"],
    help="Sets the peer group. The town list below is rebuilt from this selection.",
)

if not selected_govs:
    st.warning("Select at least one governorate in the sidebar to continue.")
    st.stop()

# The link between the two controls: the town options exist only for the
# governorates chosen above.
peers = df[df["Governorate"].isin(selected_govs)].copy()
town_options = peers.sort_values("NeedScore", ascending=False)["Town"].tolist()

selected_town = st.sidebar.selectbox(
    f"2 · Town  ({len(town_options):,} available)",
    options=town_options,
    help="Only towns in the governorates selected above. Ordered by need score, "
         "highest first.",
)
town_row = peers.loc[peers["Town"] == selected_town].iloc[0]

scope_label = (
    selected_govs[0] if len(selected_govs) == 1 else f"{len(selected_govs)} governorates"
)

st.sidebar.divider()
st.sidebar.caption(
    f"Showing **{len(peers):,} towns** across "
    f"{len(selected_govs)} governorate{'s' if len(selected_govs) > 1 else ''}."
)

# ----------------------------------------------------------------- live readout
lo, hi = peers["University"].min(), peers["University"].max()
st.markdown(
    f"**In your selection:** university attainment across these {len(peers):,} towns "
    f"runs from **{lo:.0f}%** to **{hi:.0f}%** — a spread of {hi - lo:.0f} points, "
    f"against a peer-group average of {peers['University'].mean():.1f}% and a national "
    f"average of {national['University']:.1f}%. **{selected_town}** sits at "
    f"**{town_row['University']:.0f}%**."
)

# ------------------------------------------------------------------- the charts
left, right = st.columns(2)
with left:
    st.plotly_chart(peer_scatter(peers, town_row), width="stretch")
with right:
    st.plotly_chart(
        profile_comparison(town_row, peers, national, scope_label),
        width="stretch",
    )

# ------------------------------------------------------- design justifications
st.divider()
st.subheader("Why these two controls")

j1, j2 = st.columns(2)

with j1:
    with st.expander("1 · Governorate — multiselect", expanded=True):
        st.markdown(
            """
**Which user question it answers.** *"Which part of the country am I looking at,
and how do its towns compare with one another?"* It sets the peer group that
every number and both charts are measured against.

**Why a multiselect rather than an alternative.** I considered a single-choice
dropdown and a radio group. Both were rejected because the central finding here
is a *comparison* — the reader needs to put Akkar beside Mount Lebanon to see
that their town-level distributions overlap far more than the regional averages
imply, and a single-select makes that impossible without flipping back and
forth and holding the first view in memory. A radio group would also have pinned
seven options permanently on screen. The multiselect keeps the default narrow
(the two weakest governorates) while letting the reader widen to all seven.

**Course concept — providing context.** A single town's 12% university
attainment means nothing in isolation. This control is what supplies the frame
of reference: it decides which towns count as "comparable" and therefore what
the scatter's cloud and the orange benchmark bar actually represent.
"""
        )

with j2:
    with st.expander("2 · Town — dependent dropdown", expanded=True):
        st.markdown(
            """
**Which user question it answers.** *"Within this region, what is going on in one
specific place — and is it typical of its neighbours or an outlier?"*

**Why a dependent dropdown rather than an alternative.** Its options are built
from the governorate selection above, so it never offers a town that is not on
screen — selecting Akkar reduces roughly 910 choices to 139. I considered a free
-text search box over all towns, which would have broken the drill-down: a
reader could summon a town from a governorate they had filtered out, leaving the
highlight stranded outside the scatter's own cloud. I also considered a
need-score slider, but a range filter answers "how many towns are this bad?"
rather than "what about *this* town?", and it cannot drive the profile chart,
which needs exactly one town. Ordering the list by need score puts the most
interesting cases first instead of burying them alphabetically.

**Course concept — reducing clutter and focusing attention.** Rather than
labelling hundreds of points, the scatter stays clean and this control moves a
single highlight through it, while the second chart renders the detail for just
the selected town. The dependency is what keeps the two views describing the
same population.
"""
        )

# -------------------------------------------------------------------- appendix
with st.expander("Data quality and method"):
    st.markdown(
        f"""
The seven education levels are shares of one population and should sum to 100%.
They do for **{quality['towns_analysed']:,}** of {quality['towns_total']:,} towns.
**{quality['towns_no_data']}** towns report nothing at all and
**{quality['towns_inconsistent']}** are internally inconsistent — one row sums to
13,200, a data-entry error — so both groups are dropped rather than repaired.

The source `refArea` column mixes governorate- and district-level identifiers and
double-encodes non-ASCII characters (`Zahlé` arrives as `ZahlÃ©`); districts are
rolled up to their governorate and the encoding is repaired in `data_prep.py`.

**Need score** = (illiterate % + elementary %) − (university % + higher-education %).
Both halves are shares of the same population, so the difference is already in
comparable percentage points. Positive means more residents stopped at or below
elementary school than reached tertiary education.

Most source values are recorded as round integers (0, 5, 10, 20), which is why the
scatter shows vertical banding and why the need score should be read in bands
rather than as an exact town-by-town ranking.
"""
    )
    st.dataframe(
        peers[["Town", "Governorate"] + LEVEL_ORDER + ["Dropout", "NeedScore"]]
        .sort_values("NeedScore", ascending=False)
        .reset_index(drop=True),
        width="stretch",
        height=300,
    )
