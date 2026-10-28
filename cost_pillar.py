"""Cost pillar page: county-level industrial electricity price, 2001-2025
actual (EIA Form 861, now including final 2025 data) + 2026-2028 theta
forecast. Real data only -- see data_prep.py for how data/actual.parquet,
data/forecast.parquet and data/county_lookup.parquet are produced from the
notebook's outputs.

Interface refinements applied on this page (v3, confirmed with the user):
  - Contiguous US only, thicker state borders, every year marked on the
    map slider -- all handled in map_utils.build_animated_choropleth().
  - No "About this data and methodology" section anywhere.
  - No 68%/CI-level/likely-range numbers shown anywhere (hover, click
    panel, or search panel) -- forecast years are tagged "(forecast)"
    only. The shaded band stays on the trend chart as a visual only, with
    no numeric label.
  - No confidence grade anywhere; legend text kept short.
  - Map click and county search open the same detail panel. Search
    always shows the latest actual year (2025); a map click shows
    whichever year the slider was on when clicked. Search additionally
    shows a couple of extra fields (national rank, total reported volume)
    beyond what the click panel shows.
"""
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from map_utils import build_animated_choropleth, get_clicked_fips_and_year, render_map_legend_note

KEY = 'cost'


@st.cache_data
def load_data():
    actual = pd.read_parquet('data/actual.parquet')
    forecast = pd.read_parquet('data/forecast.parquet')
    county_lookup = pd.read_parquet('data/county_lookup.parquet')
    return actual, forecast, county_lookup


def _hover_text(df, last_actual_year):
    tag = df['Year'].apply(lambda y: '' if y <= last_actual_year else ' (forecast)')
    return (
        df['County_Name'] + ', ' + df['State'] + '<br>'
        + df['Price_cents_kWh'].round(2).astype(str) + ' ¢/kWh' + tag
    )


def render(geo):
    actual, forecast, county_lookup = load_data()
    last_actual_year = int(actual['Year'].max())

    st.info(
        'County-level **industrial** electricity price (not retail, since data '
        f'centers are industrial loads): 2001-{last_actual_year} actual data, EIA Form 861, '
        f'with a theta-model 3-year forecast ({last_actual_year + 1}-{last_actual_year + 3}).'
    )

    # -------------------------------------------------- search (contiguous US)
    search_options = [
        f"{r.County_Name}, {r.State} ({r.FIPS})"
        for r in county_lookup.sort_values(['County_Name', 'State']).itertuples()
    ]
    sel_search_label = st.selectbox(
        'Search for a county', search_options, index=None,
        placeholder='Type a county name...', key=f'{KEY}_search',
    )

    # ---------------------------------------------------------------- map
    st.subheader("County-level industrial electricity price")

    _all_prices = pd.concat([actual['Price_cents_kWh'], forecast['Price_cents_kWh']])
    vmin, vmax = _all_prices.quantile(0.02), _all_prices.max()

    frames_df_by_year = {}
    for y, g in actual.groupby('Year'):
        frames_df_by_year[int(y)] = g[['FIPS', 'Year', 'Price_cents_kWh', 'County_Name', 'State']]
    for y, g in forecast.groupby('Year'):
        frames_df_by_year[int(y)] = g[['FIPS', 'Year', 'Price_cents_kWh', 'County_Name', 'State']]

    fig_map = build_animated_choropleth(
        frames_df_by_year, geo, 'Price_cents_kWh', 'YlOrRd', vmin, vmax,
        hover_text_fn=lambda d: _hover_text(d, last_actual_year),
        colorbar_title='¢/kWh', default_year=last_actual_year,
    )
    event = st.plotly_chart(
        fig_map, width='stretch', key=f'{KEY}_map',
        on_select='rerun', selection_mode='points',
    )
    render_map_legend_note('Gray = not available (no reporting).')
    st.caption(
        f"Drag the slider to any year 2001-{last_actual_year + 3}. "
        f"{last_actual_year + 1}-{last_actual_year + 3} are theta-model forecast years, not measured actuals. "
        "Click any county for details."
    )

    # ---------------------------------------- resolve click vs. search intent
    click_fips, click_year = get_clicked_fips_and_year(event)
    prev_click = st.session_state.get(f'{KEY}_prev_click')
    prev_search = st.session_state.get(f'{KEY}_prev_search_val')

    sel_fips, sel_year, sel_source = (
        st.session_state.get(f'{KEY}_sel_fips'),
        st.session_state.get(f'{KEY}_sel_year'),
        st.session_state.get(f'{KEY}_sel_source'),
    )

    if click_fips is not None and (click_fips, click_year) != prev_click:
        sel_fips, sel_year, sel_source = click_fips, click_year, 'click'
        st.session_state[f'{KEY}_prev_click'] = (click_fips, click_year)
    if sel_search_label is not None and sel_search_label != prev_search:
        sel_fips = sel_search_label.split('(')[-1].rstrip(')')
        sel_year, sel_source = last_actual_year, 'search'
        st.session_state[f'{KEY}_prev_search_val'] = sel_search_label

    st.session_state[f'{KEY}_sel_fips'] = sel_fips
    st.session_state[f'{KEY}_sel_year'] = sel_year
    st.session_state[f'{KEY}_sel_source'] = sel_source

    # ============================================================ county detail
    st.divider()
    if sel_fips is None:
        st.caption('Click a county on the map, or search for one above, to see its detail.')
    else:
        _render_detail(actual, forecast, sel_fips, sel_year, sel_source, last_actual_year)

    # ======================================================== comparison table
    st.divider()
    _render_comparison(actual, forecast, last_actual_year)


def _render_detail(actual, forecast, sel_fips, sel_year, sel_source, last_actual_year):
    a_sel = actual[actual['FIPS'] == sel_fips].sort_values('Year')
    f_sel = forecast[forecast['FIPS'] == sel_fips].sort_values('Year')
    if a_sel.empty and f_sel.empty:
        st.warning('No data for this county.')
        return
    name_row = (a_sel.iloc[-1] if not a_sel.empty else f_sel.iloc[-1])
    st.subheader(f"{name_row['County_Name']}, {name_row['State']}")

    is_forecast_year = sel_year > last_actual_year
    row = (f_sel[f_sel['Year'] == sel_year] if is_forecast_year else a_sel[a_sel['Year'] == sel_year])

    m1, m2, m3 = st.columns(3)
    if row.empty:
        m1.metric(f'Price ({sel_year})', 'n/a')
    else:
        r = row.iloc[0]
        tag = ' (forecast)' if is_forecast_year else ''
        m1.metric(f'Price ({sel_year}){tag}', f"{r['Price_cents_kWh']:.2f} ¢/kWh")
        if not is_forecast_year:
            m2.metric(
                f'National standing ({sel_year})',
                f"cheaper than {r['Pct_Counties_MoreExpensive_SameYear']:.0f}% of U.S. counties",
            )
            m3.metric('vs. national median', f"{r['National_Median_Price_cents_kWh_SameYear']:.2f} ¢/kWh median")
        reporting = r.get('Reporting_Utilities')
        if isinstance(reporting, str) and reporting:
            st.caption(f"Reporting utilities: {reporting}")

    if sel_source == 'search':
        _render_search_extra(actual, sel_fips, sel_year, last_actual_year)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=a_sel['Year'], y=a_sel['Price_cents_kWh'], mode='lines+markers',
                              name='Actual', line=dict(color='#1f77b4', width=2)))
    if not f_sel.empty:
        bridge_year = pd.concat([a_sel['Year'].tail(1), f_sel['Year']])
        bridge_price = pd.concat([a_sel['Price_cents_kWh'].tail(1), f_sel['Price_cents_kWh']])
        has_ci = f_sel['Upper_CI_cents_kWh'].notna().all() and f_sel['Lower_CI_cents_kWh'].notna().all()
        if has_ci:
            upper = pd.concat([a_sel['Price_cents_kWh'].tail(1), f_sel['Upper_CI_cents_kWh']])
            lower = pd.concat([a_sel['Price_cents_kWh'].tail(1), f_sel['Lower_CI_cents_kWh']])
            fig.add_trace(go.Scatter(
                x=pd.concat([bridge_year, bridge_year[::-1]]),
                y=pd.concat([upper, lower[::-1]]),
                fill='toself', fillcolor='rgba(255,127,14,0.18)',
                line=dict(color='rgba(255,255,255,0)'), hoverinfo='skip',
                name='Forecast range', showlegend=False,
            ))
        fig.add_trace(go.Scatter(x=bridge_year, y=bridge_price, mode='lines+markers',
                                  name='Forecast', line=dict(color='#ff7f0e', width=2, dash='dash'),
                                  hovertemplate='%{x}: %{y:.2f} ¢/kWh (forecast)<extra></extra>'))
    fig.update_layout(
        xaxis_title='Year', yaxis_title='Price (cents/kWh)',
        xaxis=dict(tickformat='d', dtick=1),  # a narrow year range otherwise gets fractional/comma'd ticks
        height=380, margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation='h', y=1.12), hovermode='x unified',
    )
    st.plotly_chart(fig, width='stretch', key=f'{KEY}_trend_{sel_fips}')


def _render_search_extra(actual, sel_fips, sel_year, last_actual_year):
    """Extra fields shown only when the detail panel was opened via search
    (per the user's request for 'more details' specifically for search)."""
    year_slice = actual[actual['Year'] == last_actual_year].copy()
    year_slice = year_slice.sort_values('Price_cents_kWh').reset_index(drop=True)
    row = year_slice[year_slice['FIPS'] == sel_fips]
    if row.empty:
        return
    rank = int(row.index[0]) + 1  # 1 = cheapest
    n_total = len(year_slice)
    total_mwh = row['Total_MWh'].iloc[0]
    e1, e2 = st.columns(2)
    e1.caption(f"National rank ({last_actual_year}): **#{rank} cheapest** of {n_total:,} U.S. counties")
    e2.caption(f"Total reported industrial volume ({last_actual_year}): **{total_mwh:,.0f} MWh**")


def _render_comparison(actual, forecast, last_actual_year):
    st.subheader('Compare counties')
    latest_actual = (
        actual.sort_values('Year').drop_duplicates('FIPS', keep='last')
        .set_index('FIPS')
    )
    forecast_horizon_year = last_actual_year + 3
    fc_last = forecast[forecast['Year'] == forecast_horizon_year][
        ['FIPS', 'Price_cents_kWh']
    ].rename(columns={'Price_cents_kWh': 'Price_cents_kWh_forecast'})

    states = sorted(actual['State'].dropna().unique())
    c1, c2, c3 = st.columns(3)
    scope = c1.radio('Scope', ['All contiguous U.S.', 'One state'], horizontal=True, key=f'{KEY}_scope')
    sort_options = {
        f'Last reported price ({last_actual_year}, highest)': ('Price_cents_kWh_actual', False),
        f'Last reported price ({last_actual_year}, lowest)': ('Price_cents_kWh_actual', True),
        f'{forecast_horizon_year} forecast (highest)': ('Price_cents_kWh_forecast', False),
        f'{forecast_horizon_year} forecast (lowest)': ('Price_cents_kWh_forecast', True),
    }
    sort_choice = c2.selectbox('Sort by', list(sort_options.keys()), index=2, key=f'{KEY}_sort')
    n_show = c3.slider('Counties to show', 5, 50, 15, key=f'{KEY}_n')

    la = latest_actual.reset_index().rename(
        columns={'Price_cents_kWh': 'Price_cents_kWh_actual', 'Year': 'Last_Year'})
    table = la.merge(fc_last, on='FIPS', how='left')

    if scope == 'One state':
        sel_state = st.selectbox('State', states, index=states.index('MO') if 'MO' in states else 0, key=f'{KEY}_cmp_state')
        table = table[table['State'] == sel_state]

    col, asc = sort_options[sort_choice]
    table = table.sort_values(col, ascending=asc, na_position='last').head(n_show)

    st.dataframe(
        table[['FIPS', 'State', 'County_Name', 'Last_Year', 'Price_cents_kWh_actual',
               'Pct_Counties_MoreExpensive_SameYear', 'Price_cents_kWh_forecast']]
        .rename(columns={
            'Last_Year': 'Last reported year',
            'Price_cents_kWh_actual': f'Last reported price (¢/kWh)',
            'Pct_Counties_MoreExpensive_SameYear': 'Cheaper than % of U.S. counties',
            'Price_cents_kWh_forecast': f'{forecast_horizon_year} Forecast (¢/kWh)',
        }).round(2),
        width='stretch', hide_index=True,
    )
