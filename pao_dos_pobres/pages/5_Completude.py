"""
Página 5 — Existem dados ausentes ou inconsistentes?

Visualizações:
  • Heatmap de Completude Anotado — ausências por indicador e ano
  • Strip Plot com Jitter          — distribuição dos valores por indicador e ano
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from utils.data import carregar_desdobramentos
from utils.style import CORES_SECAO, ANOS, PLOTLY_TEMPLATE
from utils.insights import resumo_completude

st.set_page_config(page_title="Completude · LEM", layout="wide")

# ── Dados ─────────────────────────────────────────────────────────────────────
df = carregar_desdobramentos()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Filtros")
    secoes = st.multiselect(
        "Seções", sorted(df["secao"].unique()), default=sorted(df["secao"].unique())
    )
    anos = st.multiselect("Anos", ANOS, default=ANOS)

df_f = df[df["secao"].isin(secoes) & df["ano"].isin(anos)]

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
st.title("🔍 Qualidade e Completude")
st.markdown("**PQ5** · Existem indicadores com registros ausentes, inconsistentes ou muito diferentes entre os anos?")
st.divider()

# Guarda: sem Anos/Seções selecionados não há o que mostrar
if not anos or not secoes or df_f.empty:
    st.warning(
        "⚠️ Nenhum dado para os filtros selecionados. "
        "Marque pelo menos um **Ano** e uma **Seção** na barra lateral."
    )
    st.stop()

# ── VIZ 5A: Heatmap de Completude ─────────────────────────────────────────────
st.subheader("Heatmap de Completude — % de meses preenchidos por indicador e ano")
st.caption("Verde escuro = 100% dos meses preenchidos · Amarelo = parcial · Vermelho = ausência.")

pivot_comp = df_f.pivot_table(
    index="indicador",
    columns="ano",
    values="valor",
    aggfunc=lambda x: round(x.notna().mean() * 100, 1),
)
# Ordenar: piores no topo
pivot_comp = pivot_comp.loc[pivot_comp.mean(axis=1).sort_values().index]

# ── Resumo em palavras ────────────────────────────────────────────────────────
st.info("📝 **Resumo em palavras**  \n" + "  \n".join(resumo_completude(pivot_comp)))

anos_disp = [str(c) for c in pivot_comp.columns]
inds = list(pivot_comp.index)
z = pivot_comp.values
text_z = np.where(np.isnan(z), "—", np.vectorize(lambda v: f"{v:.0f}%")(z))

fig_comp = go.Figure(data=go.Heatmap(
    z=z,
    x=anos_disp,
    y=inds,
    text=text_z,
    texttemplate="%{text}",
    textfont=dict(size=11),
    colorscale=[
        [0.0,  "#d73027"],
        [0.5,  "#fee08b"],
        [0.83, "#91cf60"],
        [1.0,  "#1a9850"],
    ],
    zmin=0, zmax=100,
    colorbar=dict(
        title="Completude",
        tickvals=[0, 25, 50, 75, 100],
        ticktext=["0%", "25%", "50%", "75%", "100%"],
    ),
    hovertemplate="<b>%{y}</b><br>Ano: %{x}<br>Completude: %{z:.1f}%<extra></extra>",
))

fig_comp.update_layout(
    template=PLOTLY_TEMPLATE,
    height=max(400, len(inds) * 26 + 120),
    margin=dict(l=280, t=40, b=20, r=20),
    xaxis=dict(title="Ano", side="top"),
    yaxis=dict(title="", autorange="reversed", tickfont=dict(size=10)),
)
st.plotly_chart(fig_comp, use_container_width=True)

st.divider()

# ── VIZ 5B: Strip Plot com Jitter ─────────────────────────────────────────────
st.subheader("Strip Plot — Distribuição dos valores por indicador")
st.caption("Cada ponto = um mês. Pontos afastados = outliers. Meses sem dado não aparecem.")

secao_strip = st.selectbox(
    "Filtrar por seção",
    options=["Todas"] + sorted(df_f["secao"].unique()),
    key="strip_secao",
)

df_strip = df_f.copy() if secao_strip == "Todas" else df_f[df_f["secao"] == secao_strip]
df_strip = df_strip.dropna(subset=["valor"])

if df_strip.empty:
    st.info("Nenhum dado para os filtros selecionados.")
else:
    fig_strip = px.strip(
        df_strip,
        x="ano",
        y="valor",
        color="secao",
        color_discrete_map=CORES_SECAO,
        facet_row="indicador",
        stripmode="overlay",
        template=PLOTLY_TEMPLATE,
        hover_data=["mes", "indicador", "secao"],
        labels={"ano": "Ano", "valor": "Valor", "secao": "Seção"},
    )
    fig_strip.update_traces(marker=dict(size=6, opacity=0.7))
    fig_strip.update_layout(
        height=max(600, df_strip["indicador"].nunique() * 80),
        margin=dict(t=40, b=40, l=20, r=20),
        showlegend=True,
    )
    # Limpar rótulos repetidos do facet
    fig_strip.for_each_annotation(
        lambda a: a.update(text=a.text.split("=")[-1], font=dict(size=9))
    )
    st.plotly_chart(fig_strip, use_container_width=True)
