# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 10:42:06 2026

@author: Guillermo Ponce Cruz
"""
import pandas as pd
import plotly.express as px
import streamlit as st
import numpy as np
import country_converter as coco

ROSE = "#EE6677"
GREEN = "#338a41"

st.set_page_config(page_title="Strawberries Dashboard", page_icon="🍓", layout="wide")
st.title("🍓 Strawberries Dashboard 🍓")

@st.cache_data
def load_data():
    sp = pd.read_csv("Strawberries_Production.csv")
    dt_trade = pd.read_csv("Strawberries_tradedata.csv", encoding='latin1', index_col=False)
    
    sp = sp[sp['Flag'] != 'M']

    sptable = sp.pivot_table(
        index=['Area Code (M49)', 'Area', 'Year'], 
        columns='Element', 
        values='Value'
    ).reset_index()

    sptable = sptable[sptable['Area Code (M49)'] != 159]
    sptable['Continent'] = coco.convert(names=sptable['Area Code (M49)'], to='continent')

    trade = dt_trade.groupby(['refPeriodId', 'reporterCode', 'reporterISO'])[['fobvalue','qty']].sum().reset_index()

    trade['Price_per_kg'] = trade['fobvalue'] / trade['qty']
    trade = trade.rename(columns={'refPeriodId': 'year', 'reporterCode':'code','reporterISO':'country', 'fobvalue':'Export_value', 'qty': 'Quantity'})
    
    trade['year'] = pd.to_datetime(trade['year'], format='%Y%m%d').dt.year

    strade = pd.merge(
        sptable, 
        trade, 
        left_on=['Area Code (M49)', 'Year'],   
        right_on=['code', 'year'],             
        how='left'                             
    )

    strade = strade.drop(columns=['code','year', 'country','Area Code (M49)'])
    strade = strade.rename(columns={'Area': 'Country'})
    
    return strade

# Sample raw Data
df = load_data()
st.header("Sample of Raw Data")
st.dataframe(df.head())

# Filters
st.sidebar.header("Filters")
selected_year = st.sidebar.multiselect("Select Year:", df["Year"].unique(), default=df["Year"].unique())
selected_country = st.sidebar.multiselect("Select country:", df["Country"].unique(), default=df["Country"].unique())
selected_continent = st.sidebar.multiselect("Select continent:", df["Continent"].unique(), default=df["Continent"].unique())

# Filtered data
boolean_filter = df["Year"].isin(selected_year) & df["Country"].isin(selected_country) & df["Continent"].isin(selected_continent)
strade_filtered = df.loc[boolean_filter]

# Display info
avg_yield = strade_filtered["Yield"].mean()
avg_export_value = strade_filtered["Export_value"].mean()
avg_production = strade_filtered["Production"].mean()
avg_area = strade_filtered["Area harvested"].mean() if "Area harvested" in strade_filtered.columns else None

# Flash cards (Gemini coded, not me)
def create_card(label, value, color):
    return f"""
    <div style="background-color: #1E1E2E; padding: 16px; border-radius: 10px; border-left: 5px solid {color}; margin-bottom: 10px;">
        <p style="margin: 0; font-size: 0.95rem; color: #FFFFFF; font-weight: 600;">{label}</p>
        <p style="margin: 4px 0 0 0; font-size: 1.6rem; color: {color}; font-weight: bold;">{value}</p>
    </div>
    """
    
col1, col2, col3, col4 = st.columns(4)

with col1:
    val = f"{avg_yield:,.0f} kg/ha" if pd.notna(avg_yield) else "0 kg/ha"
    st.markdown(create_card("Avg. Yield", val, GREEN), unsafe_allow_html=True)

with col2:
    val = f"${avg_export_value:,.0f} USD" if pd.notna(avg_export_value) else "$0 USD"
    st.markdown(create_card("Avg. Export Value $", val, ROSE), unsafe_allow_html=True)

with col3:
    val = f"{avg_production:,.2f} t" if pd.notna(avg_production) else "0 t"
    st.markdown(create_card("Avg. Production", val, GREEN), unsafe_allow_html=True)

with col4:
    val = f"{avg_area:,.0f} ha" if pd.notna(avg_area) else "0 ha"
    st.markdown(create_card("Avg. Area harvested", val, ROSE), unsafe_allow_html=True)
    
# First row plots
st.markdown("---")

if not strade_filtered.empty:
    min_year = int(strade_filtered["Year"].min())
    year_label = f"({min_year})"
else:
    year_label = "(No Data)"
    
fig_map = px.choropleth(
    strade_filtered,  
    locations='Country',
    locationmode='country names',
    color='Yield',
    color_continuous_scale='sunset',
    title=f'Strawberries Yield by Country <span style="font-size: 20px; color: {ROSE};">{year_label}</span>',
    hover_name='Country',
    hover_data={'Country': False, 'Year': True},
    custom_data=['Year'],
    height=500
)

fig_map.update_layout(title_font=dict(size=20), margin=dict(l=0, r=0, t=40, b=0), legend=dict(title=''), geo=dict(
                showframe=False,
                showcoastlines=True,
                projection_type='equirectangular',
                fitbounds="locations" 
                )) 
fig_map.update_traces(hovertemplate="<b>%{hovertext}</b><br>Year: %{customdata[0]}<br>Yield: %{z:,.0f} kg/ha<extra></extra>")

st.plotly_chart(fig_map, use_container_width=True)


st.markdown("---")


#Second row
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    boolean_geo = df["Country"].isin(selected_country) & df["Continent"].isin(selected_continent)
    yearly_production = df.loc[boolean_geo].groupby("Year")["Production"].sum().reset_index()

    fig_line = px.line(
        yearly_production,
        x="Year",
        y="Production",
        markers=True,
        title="<b>Production Trend Over Time</b>",
        line_shape="spline"
    )

    fig_line.update_layout(xaxis_title="Year", yaxis_title="Production (t)", height=400, xaxis=dict(dtick=1))
    fig_line.update_traces(line_color=GREEN, line_width=3, hovertemplate="<b>Year: %{x}</b><br>Total Production: %{y:,.0f} t<extra></extra>")

    st.plotly_chart(fig_line, use_container_width=True)

with col_chart2:
    continent_production = (
        strade_filtered.groupby("Continent")["Production"]
        .sum()
        .reset_index()
    )

    fig_pie = px.pie(
        continent_production,
        values="Production",
        names="Continent",
        title="<b>Production Share by Continent</b>",
        hole=0.3,
        color_discrete_sequence=px.colors.sequential.Sunset
    )

    fig_pie.update_layout(height=400)
    fig_pie.update_traces(textposition='inside', textinfo='percent+label', hovertemplate="<b>%{label}</b><br>Production: %{value:,.0f} t<br>Share: %{percent}<extra></extra>")

    st.plotly_chart(fig_pie, use_container_width=True)


top_producers = (
    strade_filtered.groupby("Country")["Production"]
    .mean() 
    .reset_index()
    .sort_values(by="Production", ascending=True)
    .tail(10)
)

fig_bar = px.bar(
    top_producers,
    x="Production",
    y="Country",
    orientation="h",
    title="<b>Top 10 Strawberry Producers (Total)</b>",
    color="Production",
    color_continuous_scale="sunset",
    text_auto=",.0f"
)

fig_bar.update_layout(xaxis_title="Avg. Production (t)", yaxis_title="", coloraxis_showscale=False, height=400)
fig_bar.update_traces(hovertemplate="<b>%{y}</b><br>Avg. Production: %{x:,.0f} t<extra></extra>")

st.plotly_chart(fig_bar, use_container_width=True)


st.markdown("---")


# Price per kg
clean_trade = strade_filtered.copy()
clean_trade["Price_per_kg"] = clean_trade["Price_per_kg"].replace([np.inf, -np.inf], np.nan)

#Third row
col_trade1, col_trade2 = st.columns(2)

with col_trade1:
    top_exporters = (
        clean_trade.groupby("Country")["Export_value"]
        .mean()
        .dropna()
        .reset_index()
        .sort_values(by="Export_value", ascending=True)
        .tail(10)
    )

    fig_export = px.bar(
        top_exporters,
        x="Export_value",
        y="Country",
        orientation="h",
        title="<b>Top 10 Exporters by Value (USD)</b>",
        color="Export_value",
        color_continuous_scale="sunset",
        text_auto="$.2s"
    )

    fig_export.update_layout(xaxis_title="Avg. Export Value (USD)", yaxis_title="", coloraxis_showscale=False, height=400)
    fig_export.update_traces(hovertemplate="<b>%{y}</b><br>Avg. Export Value: $%{x:,.0f} USD<extra></extra>")

    st.plotly_chart(fig_export, use_container_width=True)


with col_trade2:
    clean_trade_filtered = clean_trade[clean_trade["Quantity"] > 1000]

    price_data = (
        clean_trade_filtered.groupby("Country")["Price_per_kg"]
        .mean()
        .dropna()
        .reset_index()
        .sort_values(by="Price_per_kg", ascending=True)
        .tail(10)
    )

    fig_price = px.bar(
        price_data,
        x="Price_per_kg",
        y="Country",
        orientation="h",
        title="<b>Top 10 Highest Price per kg (USD)</b>",
        color="Price_per_kg",
        color_continuous_scale="sunset",
        text_auto="$.2f"
    )

    fig_price.update_layout(xaxis_title="Price per kg (USD)", yaxis_title="", coloraxis_showscale=False, height=400)
    fig_price.update_traces(hovertemplate="<b>%{y}</b><br>Avg. Price/kg: $%{x:,.2f} USD<extra></extra>")

    st.plotly_chart(fig_price, use_container_width=True)
    
st.markdown("---")
