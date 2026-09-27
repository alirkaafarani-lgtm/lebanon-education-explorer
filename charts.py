"""The two linked visualizations behind the explorer.

Both are adapted from the MSBA 325 Plotly activity: the peer scatter is the
town-level scatter from that deck, and the profile comparison is the per-level
view that the deck showed as a governorate heatmap, re-cut for one town.
"""

import json
import pathlib
from functools import lru_cache

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from data_prep import LEVEL_ORDER

GEOJSON_PATH = pathlib.Path(__file__).resolve().parent / "lebanon_adm1.geojson"

# geoBoundaries names the governorates in French and reflects the 2017 split of
# Keserwan-Jbeil out of Mount Lebanon. This dataset predates that split and rolls
# those districts into Mount Lebanon, so both shapes take the same value. Beirut
# has no towns in the dataset at all.
SHAPE_TO_GOV = {
    "Aakkâr": "Akkar",
    "Baalbek-Hermel": "Baalbek-Hermel",
    "Béqaa": "Beqaa",
    "Liban-Nord": "North",
    "Liban-Sud": "South",
    "Mont-Liban": "Mount Lebanon",
    "Keserwan-Jbeil": "Mount Lebanon",
    "Nabatîyé": "Nabatieh",
    "Beyrouth": None,
}

# Metric -> (column, aggregation label, colour direction)
MAP_METRICS = {
    "University attainment": ("University", "% of residents", False),
    "Illiteracy": ("Illiterate", "% of residents", True),
    "School dropout": ("Dropout", "% of residents", True),
    "Need score": ("NeedScore", "points", True),
}

# Light-mode tokens, matching the deck so the two deliverables read as one set.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

TOWN_COLOR = "#2a78d6"      # categorical slot 1
GOV_COLOR = "#eb6834"       # slot 2
NATIONAL_COLOR = "#1baf7a"  # slot 3
PEER_SCALE = ["#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def _style(fig, title, subtitle, height=470):
    fig.update_layout(
        template="plotly_white",
        title=dict(
            text=f"<b>{title}</b><br><span style='font-size:13px;color:{INK_2}'>{subtitle}</span>",
            font=dict(size=19, color=INK, family=FONT),
            x=0.01, xanchor="left", y=0.96, yanchor="top",
        ),
        font=dict(family=FONT, size=13, color=INK_2),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        margin=dict(l=62, r=30, t=86, b=56),
        height=height,
        hoverlabel=dict(font=dict(family=FONT, size=13), bgcolor="white"),
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, linecolor=AXIS, ticks="outside",
                     tickcolor=AXIS, tickfont=dict(color=MUTED),
                     title_font=dict(color=INK_2, size=13))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=AXIS,
                     tickfont=dict(color=MUTED), title_font=dict(color=INK_2, size=13))
    return fig


def peer_scatter(peers: pd.DataFrame, town_row: pd.Series) -> go.Figure:
    """Where the chosen town sits among the towns of the selected governorates."""
    others = peers[peers["Town"] != town_row["Town"]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=others["Illiterate"], y=others["University"],
            mode="markers", name="Other towns",
            marker=dict(
                size=9, opacity=0.75,
                color=others["Dropout"], colorscale=PEER_SCALE, cmin=0, cmax=20,
                line=dict(width=1, color=SURFACE),
                colorbar=dict(title="School<br>dropout (%)", thickness=13, len=0.62,
                              y=0.44, outlinewidth=0, tickfont=dict(color=MUTED, size=11),
                              title_font=dict(color=INK_2, size=12)),
            ),
            customdata=np.stack([others["Town"], others["Governorate"],
                                 others["Dropout"]], axis=-1),
            hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]}"
                          "<br>Illiterate: %{x:.0f}%<br>University: %{y:.0f}%"
                          "<br>Dropout: %{customdata[2]:.0f}%<extra></extra>",
        )
    )

    # Least-squares fit, but only where there are enough towns for it to mean
    # something — on a nine-town governorate a trend line is noise.
    fit = peers[["Illiterate", "University"]].dropna()
    if len(fit) >= 30 and fit["Illiterate"].nunique() > 1:
        x, y = fit["Illiterate"], fit["University"]
        try:
            slope, intercept = np.polyfit(x, y, 1)
        except np.linalg.LinAlgError:
            slope = None
        if slope is not None:
            xs = np.linspace(x.min(), x.max(), 60)
            ys = np.clip(slope * xs + intercept, 0, None)
            fig.add_trace(
                go.Scatter(x=xs, y=ys, mode="lines",
                           name=f"Trend (r = {x.corr(y):.2f})",
                           line=dict(color=INK_2, width=2, dash="dash"),
                           hoverinfo="skip"),
            )

    fig.add_trace(
        go.Scatter(
            x=[town_row["Illiterate"]], y=[town_row["University"]],
            mode="markers+text", name=town_row["Town"],
            marker=dict(size=19, color=GOV_COLOR, symbol="circle",
                        line=dict(width=2.5, color=SURFACE)),
            text=[town_row["Town"]], textposition="top center",
            textfont=dict(size=13, color=INK, family=FONT),
            hovertemplate=f"<b>{town_row['Town']}</b><br>Illiterate: "
                          f"{town_row['Illiterate']:.0f}%<br>University: "
                          f"{town_row['University']:.0f}%<extra></extra>",
        )
    )

    _style(
        fig,
        f"{town_row['Town']} among {len(peers) - 1:,} peers",
        "Colour = dropout rate",
    )
    fig.update_xaxes(title="Illiterate residents (%)")
    fig.update_yaxes(title="Residents with a university education (%)")
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.0,
                                  xanchor="right", x=1, font=dict(size=12)))
    return fig


def profile_comparison(town_row: pd.Series, peers: pd.DataFrame,
                       national: pd.Series, scope_label: str) -> go.Figure:
    """The town's education profile against its peer group and the country."""
    peer_mean = peers[LEVEL_ORDER].mean()

    fig = go.Figure()
    for name, values, color in [
        (town_row["Town"], [town_row[c] for c in LEVEL_ORDER], TOWN_COLOR),
        (f"{scope_label} average", peer_mean.tolist(), GOV_COLOR),
        ("National average", national.tolist(), NATIONAL_COLOR),
    ]:
        fig.add_trace(
            go.Bar(
                x=LEVEL_ORDER, y=values, name=name,
                marker=dict(color=color, line=dict(width=0), cornerradius=3),
                hovertemplate=f"<b>{name}</b><br>%{{x}}: %{{y:.1f}}%<extra></extra>",
            )
        )

    gaps = {c: town_row[c] - national[c] for c in LEVEL_ORDER}
    widest = max(gaps, key=lambda c: abs(gaps[c]))
    _style(
        fig,
        f"{town_row['Town']} vs peers and country",
        f"Widest gap vs national: {widest.lower()} {gaps[widest]:+.0f} pts",
    )
    fig.update_xaxes(title=None, showgrid=False)
    fig.update_yaxes(title="Share of residents (%)")
    fig.update_layout(
        barmode="group", bargap=0.28, bargroupgap=0.08,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1,
                    font=dict(size=12)),
    )
    return fig


def _ring_is_ccw(ring) -> bool:
    """Standard shoelace: positive area means counter-clockwise."""
    return sum(ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
               for i in range(len(ring) - 1)) > 0


def _orient_for_plotly(geojson: dict) -> dict:
    """Wind exterior rings clockwise, holes counter-clockwise.

    RFC 7946 asks for the opposite (counter-clockwise exteriors), and
    geoBoundaries follows the spec — but plotly's d3-geo treats a polygon on the
    sphere by its winding, so a spec-compliant ring is read as "everything except
    this shape". The symptom is one region flooding the entire canvas while the
    others punch holes in it. Re-winding here fixes it at the source, and the
    check makes it idempotent whatever orientation the file arrives in.
    """
    for feature in geojson["features"]:
        geom = feature["geometry"]
        polys = (geom["coordinates"] if geom["type"] == "MultiPolygon"
                 else [geom["coordinates"]])
        for poly in polys:
            for index, ring in enumerate(poly):
                exterior = index == 0
                if _ring_is_ccw(ring) == exterior:
                    poly[index] = list(reversed(ring))
        geom["coordinates"] = polys if geom["type"] == "MultiPolygon" else polys[0]
    return geojson


@lru_cache(maxsize=1)
def _load_geojson():
    with open(GEOJSON_PATH, encoding="utf-8") as fh:
        return _orient_for_plotly(json.load(fh))


def governorate_map(df: pd.DataFrame, metric_label: str,
                    highlight: list[str] | None = None) -> go.Figure:
    """National overview: each governorate shaded by the chosen metric.

    Gives the drill-down its geographic context — which corner of the country a
    selection actually refers to — without pretending to town-level precision the
    dataset has no coordinates for.
    """
    column, unit, reverse = MAP_METRICS[metric_label]
    gj = _load_geojson()
    means = df.groupby("Governorate")[column].mean()

    rows = []
    for feature in gj["features"]:
        shape = feature["properties"]["shapeName"]
        gov = SHAPE_TO_GOV.get(shape)
        if gov is None or gov not in means:
            continue
        rows.append({"shapeName": shape, "Governorate": gov,
                     "value": means[gov], "towns": int((df["Governorate"] == gov).sum())})
    mdf = pd.DataFrame(rows)

    scale = list(reversed(PEER_SCALE)) if reverse else PEER_SCALE
    fig = go.Figure(
        go.Choropleth(
            geojson=gj, locations=mdf["shapeName"], featureidkey="properties.shapeName",
            z=mdf["value"], colorscale=scale,
            marker=dict(line=dict(color=SURFACE, width=1.2)),
            customdata=np.stack([mdf["Governorate"], mdf["towns"]], axis=-1),
            hovertemplate="<b>%{customdata[0]}</b><br>" + metric_label +
                          ": %{z:.1f} " + unit + "<br>%{customdata[1]} towns<extra></extra>",
            colorbar=dict(title=unit, thickness=13, len=0.72, outlinewidth=0,
                          tickfont=dict(color=MUTED, size=11),
                          title_font=dict(color=INK_2, size=12)),
        )
    )

    # Ring the governorates currently in scope so the map tracks the sidebar.
    # Drawn as an explicit line trace rather than a second choropleth: two
    # choropleths on one geo subplot can only share a single `geojson`, and the
    # loser stops resolving its locations, which renders as giant rectangles.
    if highlight:
        shapes = {s for s, g in SHAPE_TO_GOV.items() if g in highlight}
        lon, lat = [], []
        for feature in gj["features"]:
            if feature["properties"]["shapeName"] not in shapes:
                continue
            geom = feature["geometry"]
            polys = (geom["coordinates"] if geom["type"] == "MultiPolygon"
                     else [geom["coordinates"]])
            for poly in polys:
                for ring in poly:
                    lon.extend(c[0] for c in ring)
                    lat.extend(c[1] for c in ring)
                    lon.append(None)   # break the line between rings
                    lat.append(None)
        fig.add_trace(
            go.Scattergeo(
                lon=lon, lat=lat, mode="lines",
                line=dict(color=GOV_COLOR, width=2.5),
                hoverinfo="skip", showlegend=False,
            )
        )

    fig.update_geos(fitbounds="locations", visible=False, bgcolor=SURFACE,
                    projection_type="mercator")
    _style(fig, f"{metric_label} by governorate",
           "Outlined = your selection", height=430)
    fig.update_layout(margin=dict(l=10, r=10, t=76, b=10),
                      geo=dict(bgcolor=SURFACE))
    return fig


def need_ranking(peers: pd.DataFrame, town_row: pd.Series, top_n: int = 15) -> go.Figure:
    """The towns currently in scope, ranked by need — the filters made concrete."""
    ranked = peers.nlargest(top_n, "NeedScore").sort_values("NeedScore")
    selected = ranked["Town"] == town_row["Town"]
    colors = [GOV_COLOR if s else TOWN_COLOR for s in selected]

    fig = go.Figure(
        go.Bar(
            x=ranked["NeedScore"], y=ranked["Town"], orientation="h",
            marker=dict(color=colors, line=dict(width=0), cornerradius=3),
            text=[f"{v:+.0f}" for v in ranked["NeedScore"]],
            textposition="outside", textfont=dict(size=12, color=INK_2),
            customdata=ranked["Governorate"],
            hovertemplate="<b>%{y}</b> · %{customdata}"
                          "<br>Need score: %{x:+.0f} points<extra></extra>",
            cliponaxis=False,
        )
    )
    shown = min(top_n, len(peers))
    _style(fig, f"Highest need in scope (top {shown})",
           "Your town in orange", height=470)
    fig.update_xaxes(title="Need score (percentage points)")
    fig.update_yaxes(title=None, showgrid=False)
    fig.update_layout(bargap=0.3)
    return fig
