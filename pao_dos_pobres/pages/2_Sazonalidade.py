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
from utils.insights import resumo_sazonalidade

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

# Guarda: sem Anos/Seções selecionados (ou combinação sem dados) não há o que mostrar
if not anos or not secoes or df_viz.empty:
    st.warning(
        "⚠️ Nenhum dado para os filtros selecionados. "
        "Marque pelo menos um **Ano** e uma **Seção** na barra lateral."
    )
    st.stop()

df_mes = (
    df_viz
    .groupby("mes")["valor"]
    .sum()
    .reindex(ORDEM_MES)
    .reset_index(name="Volume")
)
df_mes["Volume"] = df_mes["Volume"].fillna(0)
media = df_mes["Volume"].mean()

# ── Resumo em palavras ────────────────────────────────────────────────────────
st.info("📝 **Resumo em palavras**  \n" + "  \n".join(resumo_sazonalidade(df_mes)))

# ── VIZ 2A: Gráfico de Rosa ───────────────────────────────────────────────────
st.subheader("Gráfico de Rosa — Distribuição circular por mês e ano")
st.caption("Uma cor por ano. Barras radiais representam o volume de cada mês. Linha pontilhada vermelha = média geral.")
with st.expander("ℹ️ Como ler este gráfico"):
    st.markdown(
        "Pense em um relógio: cada 'fatia' é um mês, começando em **Janeiro no topo** e "
        "girando no sentido horário até Dezembro. Dentro de cada fatia, há uma **barra por "
        "ano** (cores diferentes) — compare as cores para ver se aquele mês cresceu ou caiu "
        "de um ano para o outro. Quanto **mais a barra se estende para fora** do centro, "
        "**mais registros** houve. A linha vermelha pontilhada marca a **média geral** "
        "(todos os meses e anos)."
    )

# Volume por ano e mês (uma série/cor por ano)
df_ano_mes = (
    df_viz
    .groupby(["ano", "mes"])["valor"]
    .sum()
    .reset_index(name="Volume")
)

PALETA_ANOS = ["#b3d9f2", "#7fb8e0", "#4a90c4", "#2E86AB", "#1a3a52"]
anos_presentes = sorted(df_ano_mes["ano"].unique())
cor_ano = {a: PALETA_ANOS[i % len(PALETA_ANOS)] for i, a in enumerate(anos_presentes)}

fig_rosa = go.Figure()

for ano_i in anos_presentes:
    serie = (
        df_ano_mes[df_ano_mes["ano"] == ano_i]
        .set_index("mes")
        .reindex(ORDEM_MES)["Volume"]
        .fillna(0)
    )
    fig_rosa.add_trace(go.Barpolar(
        r=serie.values,
        theta=ORDEM_MES,
        name=str(ano_i),
        marker_color=cor_ano[ano_i],
        marker_line_color="white",
        marker_line_width=1,
        opacity=0.9,
        hovertemplate=f"<b>%{{theta}} {ano_i}</b><br>Volume: %{{r:,.0f}}<extra></extra>",
    ))

# Linha de média geral (círculo pontilhado)
# Usa os mesmos rótulos categóricos do eixo (meses) para não misturar com
# valores numéricos de grau, que quebrariam o eixo angular categórico.
theta_circ = ORDEM_MES + [ORDEM_MES[0]]
fig_rosa.add_trace(go.Scatterpolar(
    r=[media] * len(theta_circ),
    theta=theta_circ,
    mode="lines",
    line=dict(color="#E63946", width=1.5, dash="dot"),
    name=f"Média geral: {media:,.0f}".replace(",", "."),
))

fig_rosa.update_layout(
    barmode="group",
    polar=dict(
        radialaxis=dict(visible=True, showticklabels=True, gridcolor="#DDDDDD"),
        angularaxis=dict(
            type="category",
            categoryarray=ORDEM_MES,
            direction="clockwise",
            rotation=90,
        ),
        bgcolor="white",
    ),
    legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"),
    template=PLOTLY_TEMPLATE,
    height=560,
    margin=dict(t=20, b=80),
)
st.plotly_chart(fig_rosa, use_container_width=True)

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
# Reindexado pelos ANOS selecionados na barra lateral (não só pelos anos com dado),
# assim um indicador que só existe em parte do período não derruba o gráfico.
anos_disp = sorted(anos)
pivot_cal = (
    df_cal.pivot(index="ano", columns="mes", values="Volume")
    .reindex(index=anos_disp, columns=ORDEM_MES)
)

z = pivot_cal.values
if z.size == 0:
    text_z = z
else:
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
st.plotly_chart(fig_cal, use_container_width=True)
