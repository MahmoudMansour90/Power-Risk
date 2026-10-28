"""
Shared choropleth-map styling for every pillar's page, so the maps look and
behave consistently app-wide (same state-border treatment, same "no data"
convention, same contiguous-US-only framing, same year-slider behavior).

Interface refinements applied here (v3, confirmed with the user):
  - Contiguous US only -- no Alaska/Hawaii. The geojson passed in already
    has AK/HI boundary features dropped (see data_prep.py), so no shapes
    for them are ever drawn; here we additionally crop the Albers-USA view
    window, which is what actually suppresses Plotly's built-in AK/HI
    inset boxes (those are a fixed feature of scope='usa' and are NOT
    removed just by leaving geojson data out of them).
  - State boundaries thickened and darkened so they read clearly at a
    glance, not just on close zoom.
  - The year slider marks and labels EVERY year, not just the endpoints.
    Streamlit's own st.slider/st.select_slider only label the current
    value and the two ends -- to literally mark every year, the map is
    built as a Plotly animation (one frame per year) with Plotly's native
    figure-level slider, which labels every step by construction. This
    also puts the slider directly under the map, as requested.
  - Because the slider then lives entirely client-side (dragging it does
    not round-trip to Streamlit), each frame's hover/click payload carries
    that frame's own Year in customdata alongside FIPS, so a map click
    can still recover "which year was showing when clicked" purely from
    the click event itself -- see get_clicked_fips_and_year().
"""
import streamlit as st
import plotly.graph_objects as go

NO_DATA_COLOR = '#d9d9d9'  # distinct, visible gray -- not white/background

# Crops the Albers-USA composite projection to just the contiguous states'
# true lat/lon window. This is what hides the AK/HI inset boxes that
# scope='usa' draws by default, regardless of whether data/geometry exists
# there -- confirmed visually, not a documented Plotly guarantee.
CONTIGUOUS_LAT_RANGE = [23.5, 50.5]
CONTIGUOUS_LON_RANGE = [-126, -65]


def _frame_trace(d, color_col, color_scale, vmin, vmax, hover_text, geojson=None):
    kwargs = dict(
        locations=d['FIPS'], z=d[color_col],
        colorscale=color_scale, zmin=vmin, zmax=vmax,
        customdata=d[['FIPS', 'Year']].values,
        hovertext=hover_text, hoverinfo='text',
        marker_line_width=0.3, marker_line_color='rgba(80,80,80,0.5)',
    )
    if geojson is not None:
        kwargs['geojson'] = geojson
        kwargs['colorbar'] = dict(thickness=16, len=0.75)
    return go.Choropleth(**kwargs)


def build_animated_choropleth(frames_df_by_year, geojson, color_col, color_scale,
                               vmin, vmax, hover_text_fn, colorbar_title,
                               default_year, step_label_fn=None):
    """Build a contiguous-US-only county choropleth that animates across
    every year via a native Plotly slider (every step labeled). Each
    per-year dataframe in frames_df_by_year needs at least
    ['FIPS', 'Year', color_col]; hover_text_fn(df_for_year) returns the
    per-row hover text array for that year."""
    years = sorted(frames_df_by_year.keys())
    step_label_fn = step_label_fn or (lambda y: str(y))
    default_year = default_year if default_year in years else years[-1]
    default_idx = years.index(default_year)

    first_df = frames_df_by_year[default_year]
    base_trace = _frame_trace(
        first_df, color_col, color_scale, vmin, vmax,
        hover_text_fn(first_df), geojson=geojson,
    )
    base_trace.colorbar.title = colorbar_title

    frames = []
    for y in years:
        d = frames_df_by_year[y]
        frames.append(go.Frame(
            data=[_frame_trace(d, color_col, color_scale, vmin, vmax, hover_text_fn(d))],
            name=str(y),
        ))

    fig = go.Figure(data=[base_trace], frames=frames)
    fig.update_geos(
        scope='usa',
        showsubunits=True, subunitcolor='rgba(20,20,20,0.95)', subunitwidth=2.0,
        landcolor=NO_DATA_COLOR, showland=True,
        showcountries=False, showcoastlines=False, showlakes=False,
        lataxis_range=CONTIGUOUS_LAT_RANGE, lonaxis_range=CONTIGUOUS_LON_RANGE,
    )
    fig.update_layout(
        height=560, margin=dict(l=0, r=0, t=10, b=70),
        sliders=[dict(
            active=default_idx,
            x=0.05, y=0.02, len=0.9, pad=dict(t=20, b=10),
            currentvalue=dict(prefix='Year: ', font=dict(size=14)),
            steps=[
                dict(
                    method='animate',
                    args=[[str(y)], dict(mode='immediate',
                                          frame=dict(duration=0, redraw=True),
                                          transition=dict(duration=0))],
                    label=step_label_fn(y),
                )
                for y in years
            ],
        )],
    )
    return fig


def get_clicked_fips_and_year(selection_state):
    """Pull (FIPS, Year) out of a Streamlit plotly_chart on_select event
    payload (st.session_state[key] when the chart was built with
    on_select='rerun'). Returns (None, None) if nothing was clicked.
    Year comes from the clicked point's own customdata, which reflects
    whichever frame/year the slider was showing at click-time -- not
    from any server-side slider state, since the slider is client-only."""
    if not selection_state:
        return None, None
    points = selection_state.get('selection', {}).get('points', [])
    if not points:
        return None, None
    cd = points[0].get('customdata')
    if not cd or len(cd) < 2:
        return None, None
    return str(cd[0]).zfill(5), int(cd[1])


def render_map_legend_note(no_data_note):
    """Small explicit legend strip under a map: a gray swatch + a short
    explanation, since Plotly's own colorbar can't show a 'no data' entry.
    Kept short and simple per the confirmed interface refinement (no
    verbose confidence-grade legend text)."""
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:8px; margin-top:4px;
                    margin-bottom:10px; font-size:0.85rem; color:#555;">
            <div style="width:14px; height:14px; background:{NO_DATA_COLOR};
                        border:1px solid rgba(80,80,80,0.5); flex-shrink:0;"></div>
            <span>{no_data_note}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
