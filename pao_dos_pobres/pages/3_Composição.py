"""
Página 3 — Quais áreas concentram mais registros?

Visualizações planejadas:
  • Sunburst Chart — hierarquia radial seção → indicador
  • Treemap        — mosaico de área proporcional
"""
import streamlit as st
import plotly.express as px
import pandas as pd

from utils.data import carregar_desdobramentos
from utils.style import CORES_SECAO, ANOS, PLOTLY_TEMPLATE

st.set_page_config(page_title="Composição · LEM", layout="wide")

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
st.title("🍕 Composição por Área Temática")
st.markdown("**PQ3** · Quais seções e indicadores concentram o maior volume de registros?")
st.divider()

# ── Dados agregados ───────────────────────────────────────────────────────────
df_agg = (
    df_f
    .groupby(["secao", "indicador"])["valor"]
    .sum()
    .reset_index(name="Volume")
)
df_agg = df_agg[df_agg["Volume"] > 0]

# Nome curto para rótulos internos
df_agg["ind_curto"] = df_agg["indicador"].apply(
    lambda s: s[:35] + "…" if len(s) > 35 else s
)

if df_agg.empty:
    st.info("Nenhum dado para os filtros selecionados.")
    st.stop()

# ── Abas: uma para cada tipo de gráfico ───────────────────────────────────────
aba_sun, aba_tree = st.tabs(["☀️ Sunburst", "🗺️ Treemap"])

# ── VIZ 3A: Sunburst ──────────────────────────────────────────────────────────
with aba_sun:
    st.caption("Clique em uma seção para dar zoom nos seus indicadores.")

    fig_sun = px.sunburst(
        df_agg,
        path=["secao", "ind_curto"],
        values="Volume",
        color="secao",
        color_discrete_map=CORES_SECAO,
        hover_data={"indicador": True, "Volume": True},
        template=PLOTLY_TEMPLATE,
    )
    fig_sun.update_traces(
        textinfo="label+percent parent",
        insidetextorientation="radial",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Volume: %{value:,.0f}<br>"
            "% da seção: %{percentParent:.1%}<br>"
            "% do total: %{percentRoot:.1%}"
            "<extra></extra>"
        ),
    )
    fig_sun.update_layout(height=560, margin=dict(t=20, b=10))
    st.plotly_chart(fig_sun, width='stretch')

# ── VIZ 3B: Treemap ───────────────────────────────────────────────────────────
with aba_tree:
    st.caption("Tamanho de cada bloco proporcional ao volume acumulado.")

    fig_tree = px.treemap(
        df_agg,
        path=[px.Constant("LEM"), "secao", "ind_curto"],
        values="Volume",
        color="secao",
        color_discrete_map=CORES_SECAO,
        hover_data={"indicador": True, "Volume": True},
        template=PLOTLY_TEMPLATE,
    )
    fig_tree.update_traces(
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Volume: %{value:,.0f}<br>"
            "% do pai: %{percentParent:.1%}"
            "<extra></extra>"
        ),
        textinfo="label+value",
    )
    fig_tree.update_layout(height=560, margin=dict(t=20, b=10))
    st.plotly_chart(fig_tree, width='stretch')
