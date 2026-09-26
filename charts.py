"""The two linked visualizations behind the explorer.

Both are adapted from the MSBA 325 Plotly activity: the peer scatter is the
town-level scatter from that deck, and the profile comparison is the per-level
view that the deck showed as a governorate heatmap, re-cut for one town.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from data_prep import LEVEL_ORDER

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
        f"{town_row['Town']} among its {len(peers) - 1:,} peer towns",
        "Each dot is one town; colour shows the school-dropout rate",
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
        f"{town_row['Town']} vs its peer group and the country",
        f"Biggest gap to the national average: {widest.lower()} "
        f"({gaps[widest]:+.0f} points)",
    )
    fig.update_xaxes(title=None, showgrid=False)
    fig.update_yaxes(title="Share of residents (%)")
    fig.update_layout(
        barmode="group", bargap=0.28, bargroupgap=0.08,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1,
                    font=dict(size=12)),
    )
    return fig
