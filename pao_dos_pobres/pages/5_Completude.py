"""
Página 5 — Existem dados ausentes ou inconsistentes?

Visualizações:
  • Heatmap de Completude Anotado — ausências por indicador e ano
  • Gráfico de Linha              — evolução mensal de um indicador (lacunas e picos)
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from utils.data import carregar_desdobramentos
from utils.style import CORES_SECAO, ANOS, PLOTLY_TEMPLATE, titulo_com_logo
from utils.insights import resumo_completude

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
titulo_com_logo("Qualidade e Completude")
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
st.markdown(
    "**📌 O que este gráfico mostra:** ele mede a **qualidade/completude dos dados** — "
    "para cada indicador e ano, calcula o percentual de meses que realmente têm um valor "
    "registrado (em vez de estarem em branco). É essencial para interpretar corretamente os "
    "outros gráficos do dashboard: um indicador com baixa completude pode parecer ter "
    "\"caído\" em algum ano só porque **faltam registros**, não porque a atividade real da "
    "instituição realmente diminuiu."
)

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

# ── VIZ 5B: Gráfico de Linha — evolução mensal de um indicador ────────────────
st.subheader("Evolução mensal de um indicador")
st.markdown(
    "**📌 O que este gráfico mostra:** ele foca em **um único indicador por vez** e "
    "mostra sua série histórica mês a mês. Serve tanto para inspecionar visualmente a "
    "completude (lacunas na linha = meses sem registro) quanto para identificar possíveis "
    "**inconsistências** nos dados (valores muito fora do padrão dos meses vizinhos), "
    "complementando a visão agregada por percentual do Heatmap de Completude acima."
)

with st.expander("ℹ️ Como ler este gráfico"):
    st.markdown(
        "**A ideia geral:** escolha um indicador na caixa abaixo e veja como o valor dele "
        "mudou **mês a mês**, ao longo de todo o período (2021–2025).\n\n"
        "**O que procurar:** uma **lacuna** (espaço em branco) na linha significa que aquele "
        "mês não teve registro. Uma **queda ou subida muito brusca** em relação aos meses "
        "vizinhos pode indicar um valor inconsistente (erro de digitação, mudança na forma "
        "de contar, etc.) e vale a pena investigar com a equipe."
    )

indicadores_disp_5 = sorted(df_f["indicador"].unique())
indicador_linha = st.selectbox(
    "Escolha um indicador",
    options=indicadores_disp_5,
    key="indicador_linha",
)

df_linha = (
    df_f[df_f["indicador"] == indicador_linha]
    .dropna(subset=["valor"])
    .sort_values("data")
)

if df_linha.empty:
    st.info("Nenhum dado para os filtros selecionados.")
else:
    secao_do_indicador = df_linha["secao"].iloc[0]
    fig_linha = px.line(
        df_linha,
        x="data",
        y="valor",
        markers=True,
        template=PLOTLY_TEMPLATE,
        color_discrete_sequence=[CORES_SECAO.get(secao_do_indicador, "#2E86AB")],
        labels={"data": "Mês", "valor": "Valor"},
        hover_data={"mes": True, "ano": True},
    )
    fig_linha.update_traces(
        hovertemplate="<b>%{x|%b/%Y}</b><br>Valor: %{y:,.0f}<extra></extra>",
    )
    fig_linha.update_layout(
        height=380,
        margin=dict(t=20, b=20),
        xaxis=dict(title="Mês"),
        yaxis=dict(title="Valor"),
    )
    st.plotly_chart(fig_linha, use_container_width=True)
