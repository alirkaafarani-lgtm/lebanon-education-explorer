"""Lebanon Education Explorer — MSBA 325.

Region → need band → town. Each control narrows the next: the governorate
selection sets the slider's range, and the two together decide which towns the
dropdown can offer.
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

st.set_page_config(page_title="Lebanon Education Explorer", page_icon="📚",
                   layout="wide")

st.markdown(
    """
<style>
  .block-container { padding-top: 2.2rem; max-width: 1500px; }
  .eyebrow { font-size:.72rem; letter-spacing:.16em; font-weight:700;
             color:#2a78d6; text-transform:uppercase; }
  .hero { font-size:2.9rem; line-height:1.06; font-weight:800; color:#0b0b0b;
          margin:.35rem 0 .5rem; letter-spacing:-.02em; }
  .hero em { font-style:normal; color:#eb6834; }
  .deck { font-size:1.04rem; color:#52514e; max-width:62ch; margin-bottom:.2rem; }
  .cards { display:flex; gap:.7rem; margin:1.4rem 0 .4rem; flex-wrap:wrap; }
  .card { flex:1 1 170px; background:#f6f6f3; border-radius:12px;
          padding:.85rem .95rem; border-left:3px solid #2a78d6; }
  .card .n { font-size:1.85rem; font-weight:800; color:#0b0b0b; line-height:1.05; }
  .card .k { font-size:.78rem; color:#52514e; margin-top:.25rem; line-height:1.3; }
  .card.warn { border-left-color:#eb6834; }
  .chips { display:flex; gap:.4rem; flex-wrap:wrap; margin:.1rem 0 .9rem; }
  .chip { background:#eef4fd; color:#1c5cab; border-radius:999px;
          padding:.22rem .7rem; font-size:.82rem; font-weight:600; }
  .chip.hot { background:#fdefe9; color:#b2431c; }
  .note { font-size:.86rem; color:#898781; line-height:1.5; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def get_data():
    full = load()
    return add_need_index(analysis_frame(full)), quality_report(full)


df, quality = get_data()
national = df[LEVEL_ORDER].mean()
within = variance_within_governorate(df)

# ============================================================ sidebar controls
st.sidebar.markdown('<p class="eyebrow">Drill down</p>', unsafe_allow_html=True)
st.sidebar.caption("Region → need band → town")

all_govs = sorted(df["Governorate"].unique())
selected_govs = st.sidebar.multiselect(
    "1 · Governorate", options=all_govs, default=["Akkar", "Baalbek-Hermel"],
)
if not selected_govs:
    st.warning("Pick at least one governorate.")
    st.stop()

# Link 1 — the slider's range is rebuilt from the region selection.
in_govs = df[df["Governorate"].isin(selected_govs)].copy()
lo_need, hi_need = float(in_govs["NeedScore"].min()), float(in_govs["NeedScore"].max())
need_band = st.sidebar.slider(
    "2 · Need band", min_value=lo_need, max_value=hi_need,
    value=(lo_need, hi_need), step=1.0,
)

peers = in_govs[in_govs["NeedScore"].between(*need_band)].copy()
if peers.empty:
    st.warning("No towns in that band — widen the slider.")
    st.stop()

# Link 2 — the town list is whatever survived both filters.
town_options = peers.sort_values("NeedScore", ascending=False)["Town"].tolist()
selected_town = st.sidebar.selectbox(
    f"3 · Town ({len(town_options):,})", options=town_options,
)
town_row = peers.loc[peers["Town"] == selected_town].iloc[0]
scope_label = (selected_govs[0] if len(selected_govs) == 1
               else f"{len(selected_govs)} governorates")

st.sidebar.divider()
st.sidebar.caption(f"**{len(peers):,}** of {len(in_govs):,} towns in scope")

# ===================================================================== hero
top120 = df.nlargest(120, "NeedScore")
outside = int((~top120["Governorate"].isin(["Akkar", "Baalbek-Hermel"])).sum())
below_national = (df["University"] < national["University"]).mean() * 100
corr_illit = df["Illiterate"].corr(df["University"])

st.markdown('<p class="eyebrow">Lebanon · town-level education</p>',
            unsafe_allow_html=True)
st.markdown(
    f'<p class="hero">The regional average is a <em>bad map</em>.</p>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p class="deck">Lebanon reports education by governorate — seven numbers for '
    f'{quality["towns_analysed"]:,} towns. Almost everything that separates one town '
    f'from the next disappears at that level.</p>',
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div class="cards">
  <div class="card"><div class="n">{within:.0f}%</div>
    <div class="k">of the gap between towns is <b>inside</b> a governorate, not between them</div></div>
  <div class="card warn"><div class="n">{outside}/120</div>
    <div class="k">highest-need towns sit <b>outside</b> the two weakest regions</div></div>
  <div class="card"><div class="n">{below_national:.0f}%</div>
    <div class="k">of towns fall below the national average of {national['University']:.0f}%</div></div>
  <div class="card"><div class="n">r = {corr_illit:.2f}</div>
    <div class="k">illiteracy vs university — real, but explains only {corr_illit ** 2 * 100:.0f}%</div></div>
</div>
""",
    unsafe_allow_html=True,
)

tab_map, tab_drill, tab_why, tab_method = st.tabs(
    ["🗺️  Map", "🔍  Drill-down", "🎛️  Controls", "📋  Method"]
)

# ====================================================================== map
with tab_map:
    map_metric = st.radio("Colour by", options=list(MAP_METRICS.keys()),
                          horizontal=True, label_visibility="collapsed")
    c1, c2 = st.columns([3, 1])
    with c1:
        st.plotly_chart(governorate_map(df, map_metric, selected_govs),
                        width="stretch")
    with c2:
        st.markdown(
            '<p class="note">The map never filters — all seven regions stay on '
            'screen so the drill-down keeps its context. Your selection is '
            'outlined.<br><br>Switch the measure: the ranking barely moves. That '
            'consistency is what makes the regional story look convincing — and '
            'why the town-level views break it.<br><br>'
            'Boundaries: geoBoundaries (CC BY 4.0). Keserwan-Jbeil was split from '
            'Mount Lebanon in 2017, after this data, so both carry one value. '
            'Beirut is unfilled — no towns in the dataset.</p>',
            unsafe_allow_html=True,
        )

# =============================================================== drill-down
with tab_drill:
    pct = (peers["NeedScore"] < town_row["NeedScore"]).mean() * 100
    lo, hi = peers["University"].min(), peers["University"].max()
    hot = "hot" if town_row["NeedScore"] > 0 else ""
    st.markdown(
        f"""
<div class="chips">
  <span class="chip">📍 {selected_town}</span>
  <span class="chip">{town_row['Governorate']}</span>
  <span class="chip {hot}">need {town_row['NeedScore']:+.0f} · worse than {pct:.0f}% in scope</span>
  <span class="chip">university {town_row['University']:.0f}%</span>
  <span class="chip">illiterate {town_row['Illiterate']:.0f}%</span>
  <span class="chip">{len(peers):,} towns in scope · spread {lo:.0f}–{hi:.0f}%</span>
</div>
""",
        unsafe_allow_html=True,
    )
    left, right = st.columns(2)
    with left:
        st.plotly_chart(peer_scatter(peers, town_row), width="stretch")
    with right:
        st.plotly_chart(
            profile_comparison(town_row, peers, national, scope_label), width="stretch"
        )
    st.plotly_chart(need_ranking(peers, town_row), width="stretch")

# ================================================================= controls
with tab_why:
    st.markdown(
        '<p class="note">Each control narrows the next, so the page drills down '
        'rather than filtering three things independently.</p>',
        unsafe_allow_html=True,
    )
    w1, w2, w3 = st.columns(3)
    with w1:
        st.markdown("**1 · Governorate** — multiselect")
        st.markdown(
            """
*Answers:* which part of the country, and how do its towns compare?

Multi- not single-select, because the finding **is** the comparison: you need Akkar
beside Mount Lebanon to see their distributions overlap. A radio would pin seven
options on screen permanently.

**Concept — context.** A town's 12% means nothing alone; this decides what counts
as comparable.
"""
        )
    with w2:
        st.markdown("**2 · Need band** — range slider")
        st.markdown(
            """
*Answers:* which towns are in real difficulty, and how many?

**Its bounds are rebuilt from the region above**, so both ends are always real towns.
A fixed −100…+90 scale would be mostly dead space; a "top N" box would answer *how
many* rather than *how bad*.

**Concept — reducing clutter.** This is what cuts 910 towns to a readable set.
"""
        )
    with w3:
        st.markdown("**3 · Town** — dependent dropdown")
        st.markdown(
            """
*Answers:* is this one place typical of its neighbours, or an outlier?

**Its options are whatever survived the two filters**, so it can never offer a town
that isn't on screen. A free-text search would let you summon a town you'd filtered
out, stranding the highlight off-cloud.

**Concept — focusing attention.** One highlight moves through a clean scatter
instead of hundreds of labels.
"""
        )

# =================================================================== method
with tab_method:
    a, b = st.columns([1, 1])
    with a:
        st.markdown(
            f"""
**Source.** *Educational Level – Lebanon 2023*, [AUB linked-data portal](https://linked.aub.edu.lb:8502/),
published from Impact Open Data. One row per town: share of residents at seven
education levels, plus a dropout rate.

**Scope.** {quality['towns_analysed']:,} of {quality['towns_total']:,} towns.
Dropped: {quality['towns_no_data']} reporting nothing, {quality['towns_inconsistent']}
whose shares don't sum to 100% (one sums to 13,200 — a data-entry error).

**Need score** = (illiterate + elementary) − (university + higher education).
Both halves share a denominator, so the difference is already in percentage points.
"""
        )
    with b:
        st.markdown(
            """
**Fixes applied.** `refArea` mixes governorate and district identifiers — districts
are rolled up. It also double-encodes non-ASCII (`Zahlé` → `ZahlÃ©`) — repaired on load.
Where one level is blank but the other six sum to ~100, the blank is read as zero.

**Limits.** Most values are recorded as round integers (0, 5, 10, 20) — hence the
vertical banding in the scatter, and why the need score should be read in bands, not
as an exact ranking.
"""
        )
    st.dataframe(
        peers[["Town", "Governorate"] + LEVEL_ORDER + ["Dropout", "NeedScore"]]
        .sort_values("NeedScore", ascending=False)
        .reset_index(drop=True),
        width="stretch", height=260,
    )
