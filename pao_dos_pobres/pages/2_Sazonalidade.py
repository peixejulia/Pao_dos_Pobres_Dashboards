"""
Página 2 — Quais meses têm maior volume de atendimentos?

Visualizações planejadas:
  • Gráfico de Rosa (Polar Bar Chart) — distribuição circular por mês
  • Calendar Heatmap               — mapa de calor estilo GitHub
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from utils.data import carregar_desdobramentos
from utils.style import CORES_SECAO, ANOS, ORDEM_MES, PLOTLY_TEMPLATE

st.set_page_config(page_title="Sazonalidade · LEM", layout="wide")

# ── Dados ─────────────────────────────────────────────────────────────────────
df = carregar_desdobramentos()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Filtros")
    anos = st.multiselect("Anos", ANOS, default=ANOS)
    secoes = st.multiselect(
        "Seções", sorted(df["secao"].unique()), default=sorted(df["secao"].unique())
    )
    indicadores_disp = sorted(
        df[df["secao"].isin(secoes)]["indicador"].unique()
    )
    indicador_sel = st.selectbox(
        "Indicador (Rosa / Heatmap)",
        options=["Todos os indicadores"] + indicadores_disp,
    )

df_f = df[df["ano"].isin(anos) & df["secao"].isin(secoes)]
if indicador_sel != "Todos os indicadores":
    df_viz = df_f[df_f["indicador"] == indicador_sel]
else:
    df_viz = df_f

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
st.title("🌹 Sazonalidade dos Registros")
st.markdown("**PQ2** · Quais meses concentram maior volume de atendimentos e atividades?")
st.divider()

# ── VIZ 2A: Gráfico de Rosa ───────────────────────────────────────────────────
st.subheader("Gráfico de Rosa — Distribuição circular por mês")
st.caption("Barras radiais representam o volume de cada mês. Linha pontilhada vermelha = média mensal.")

df_mes = (
    df_viz
    .groupby("mes")["valor"]
    .sum()
    .reindex(ORDEM_MES)
    .reset_index(name="Volume")
)
df_mes["Volume"] = df_mes["Volume"].fillna(0)

media = df_mes["Volume"].mean()

fig_rosa = go.Figure()

fig_rosa.add_trace(go.Barpolar(
    r=df_mes["Volume"],
    theta=df_mes["mes"],
    marker_color=df_mes["Volume"],
    marker_colorscale=[
        [0,   "#b3d9f2"],
        [0.5, "#2E86AB"],
        [1,   "#1a3a52"],
    ],
    marker_line_color="white",
    marker_line_width=1.5,
    opacity=0.92,
    hovertemplate="<b>%{theta}</b><br>Volume: %{r:,.0f}<extra></extra>",
    showlegend=False,
))

# Linha de média (círculo pontilhado)
theta_circ = list(range(0, 361, 5))
fig_rosa.add_trace(go.Scatterpolar(
    r=[media] * len(theta_circ),
    theta=theta_circ,
    mode="lines",
    line=dict(color="#E63946", width=1.5, dash="dot"),
    name=f"Média: {media:,.0f}".replace(",", "."),
))

fig_rosa.update_layout(
    polar=dict(
        radialaxis=dict(visible=True, showticklabels=True, gridcolor="#DDDDDD"),
        angularaxis=dict(direction="clockwise", rotation=90),
        bgcolor="white",
    ),
    legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center"),
    template=PLOTLY_TEMPLATE,
    height=500,
    margin=dict(t=20, b=60),
)
st.plotly_chart(fig_rosa, width='stretch')

st.divider()

# ── VIZ 2B: Calendar Heatmap ──────────────────────────────────────────────────
st.subheader("Calendar Heatmap — Volume por ano e mês")
st.caption("Intensidade da cor = volume registrado. Células cinzas = meses sem dado.")

df_cal = (
    df_viz
    .groupby(["ano", "mes"])["valor"]
    .sum()
    .reset_index(name="Volume")
)

# Pivot: linhas = ano, colunas = mês
pivot_cal = df_cal.pivot(index="ano", columns="mes", values="Volume").reindex(
    columns=ORDEM_MES
)

anos_disp = sorted(pivot_cal.index)
z = pivot_cal.values
text_z = np.where(
    np.isnan(z),
    "—",
    np.vectorize(lambda v: f"{int(v):,}".replace(",", "."))(np.nan_to_num(z))
)

fig_cal = go.Figure(data=go.Heatmap(
    z=z,
    x=ORDEM_MES,
    y=anos_disp,
    text=text_z,
    texttemplate="%{text}",
    textfont=dict(size=11),
    colorscale=[
        [0,   "#eaf4fb"],
        [0.4, "#2E86AB"],
        [1,   "#1a3a52"],
    ],
    colorbar=dict(title="Volume"),
    hovertemplate="<b>%{y} — %{x}</b><br>Volume: %{z:,.0f}<extra></extra>",
))

fig_cal.update_layout(
    template=PLOTLY_TEMPLATE,
    height=max(250, len(anos_disp) * 60 + 100),
    margin=dict(t=20, b=20),
    xaxis=dict(title="Mês"),
    yaxis=dict(title="Ano", tickmode="linear", dtick=1),
)
st.plotly_chart(fig_cal, width='stretch')
