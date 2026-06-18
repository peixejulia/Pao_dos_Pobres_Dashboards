"""
Página 1 — Como os indicadores evoluíram de 2021 a 2025?

Visualizações planejadas:
  • Streamgraph — fluxo de volume por seção ao longo do tempo
  • Bump Chart  — ranking de indicadores por ano dentro de cada seção
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from utils.data import carregar_desdobramentos
from utils.style import CORES_SECAO, ANOS, ORDEM_MES, PLOTLY_TEMPLATE

st.set_page_config(page_title="Evolução · LEM", layout="wide")

# ── Dados ─────────────────────────────────────────────────────────────────────
df = carregar_desdobramentos()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Filtros")
    anos = st.multiselect("Anos", ANOS, default=ANOS)
    secoes = st.multiselect(
        "Seções", sorted(df["secao"].unique()), default=sorted(df["secao"].unique())
    )

df_f = df[df["ano"].isin(anos) & df["secao"].isin(secoes)]

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
st.title("📈 Como os indicadores evoluíram?")
st.markdown("**PQ1** · Análise da evolução temporal dos registros de 2021 a 2025.")
st.divider()

# ── VIZ 1A: Streamgraph ───────────────────────────────────────────────────────
st.subheader("Streamgraph — Fluxo de volume por seção")
st.caption("Cada faixa representa uma seção temática. A largura indica o volume registrado em cada mês.")

# Pivot: data × secao → soma de valores
df_stream = (
    df_f
    .groupby(["data", "secao"])["valor"]
    .sum()
    .reset_index()
    .pivot(index="data", columns="secao", values="valor")
    .fillna(0)
    .reset_index()
    .sort_values("data")
)

if df_stream.empty:
    st.info("Nenhum dado para os filtros selecionados.")
else:
    fig_stream = go.Figure()

    for secao in [s for s in CORES_SECAO if s in df_stream.columns]:
        fig_stream.add_trace(go.Scatter(
            x=df_stream["data"],
            y=df_stream[secao],
            name=secao,
            mode="lines",
            stackgroup="one",        # empilhamento
            groupnorm="",            # valores absolutos (não %)
            line=dict(width=0.5),
            fillcolor=CORES_SECAO[secao],
            line_color=CORES_SECAO[secao],
            hovertemplate="%{fullData.name}<br>%{x|%b %Y}: <b>%{y:,.0f}</b><extra></extra>",
        ))

    fig_stream.update_layout(
        template=PLOTLY_TEMPLATE,
        height=400,
        margin=dict(t=20, b=20),
        xaxis=dict(title="Mês/Ano"),
        yaxis=dict(title="Volume (soma dos valores)"),
        legend=dict(orientation="h", y=-0.18),
        hovermode="x unified",
    )
    st.plotly_chart(fig_stream, width='stretch')

st.divider()

# ── VIZ 1B: Bump Chart ────────────────────────────────────────────────────────
st.subheader("Bump Chart — Ranking de indicadores por ano")
st.caption("A posição vertical indica o ranking do indicador dentro da seção selecionada. Linhas que sobem = crescimento relativo.")

secao_bump = st.selectbox(
    "Seção para o Bump Chart",
    options=[s for s in CORES_SECAO if s in df_f["secao"].values],
    key="bump_secao",
)

df_bump_raw = df_f[df_f["secao"] == secao_bump]

if df_bump_raw.empty:
    st.info("Nenhum dado para a seção selecionada.")
else:
    # Volume anual por indicador
    df_bump = (
        df_bump_raw
        .groupby(["ano", "indicador"])["valor"]
        .sum()
        .reset_index(name="Volume")
    )
    # Rank dentro de cada ano (1 = maior)
    df_bump["Ranking"] = df_bump.groupby("ano")["Volume"].rank(
        ascending=False, method="first"
    ).astype(int)

    indicadores = df_bump["indicador"].unique()
    n_cores = len(indicadores)
    paleta = px.colors.qualitative.Safe[:n_cores] if n_cores <= 11 else px.colors.qualitative.Alphabet[:n_cores]
    cor_ind = dict(zip(indicadores, paleta))

    fig_bump = go.Figure()

    for ind in indicadores:
        df_ind = df_bump[df_bump["indicador"] == ind].sort_values("ano")
        fig_bump.add_trace(go.Scatter(
            x=df_ind["ano"],
            y=df_ind["Ranking"],
            name=ind,
            mode="lines+markers+text",
            text=df_ind["Ranking"],
            textposition="middle right",
            textfont=dict(size=10),
            line=dict(color=cor_ind[ind], width=2),
            marker=dict(size=10, color=cor_ind[ind]),
            hovertemplate=f"<b>{ind}</b><br>Ano: %{{x}}<br>Rank: %{{y}}<br>Volume: %{{customdata:,.0f}}<extra></extra>",
            customdata=df_ind["Volume"],
        ))

    fig_bump.update_layout(
        template=PLOTLY_TEMPLATE,
        height=max(350, len(indicadores) * 40),
        margin=dict(t=20, b=20, r=180),
        xaxis=dict(title="Ano", tickmode="linear", dtick=1),
        yaxis=dict(
            title="Ranking (1 = maior volume)",
            autorange="reversed",
            tickmode="linear",
            dtick=1,
        ),
        legend=dict(orientation="v", x=1.02, y=1),
    )
    st.plotly_chart(fig_bump, width='stretch')
