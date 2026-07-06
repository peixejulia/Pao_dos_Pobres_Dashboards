"""
home.py — Página inicial do dashboard Pão dos Pobres.
Executada via st.navigation()/st.Page() a partir de app.py.
"""
import streamlit as st
import plotly.express as px
import pandas as pd

from utils.data import carregar_desdobramentos, carregar_gerencial
from utils.style import CORES_SECAO, ANOS, titulo_com_logo
from utils.insights import resumo_geral

# ── Carregamento de dados ─────────────────────────────────────────────────────
df = carregar_desdobramentos()

# ── Sidebar — filtros globais ─────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/Pao_dos_pobres_logo.png/120px-Pao_dos_pobres_logo.png",
        width=120,
    )
    st.title("Pão dos Pobres")
    st.caption("Levantamento de Estatísticas Mensais (LEM) · 2021–2025")
    st.divider()

    anos_selecionados = st.multiselect(
        "Anos",
        options=ANOS,
        default=ANOS,
    )

    secoes_disponiveis = sorted(df["secao"].unique())
    secoes_selecionadas = st.multiselect(
        "Seções temáticas",
        options=secoes_disponiveis,
        default=secoes_disponiveis,
    )

    st.divider()
    st.caption("Navegue pelas páginas no menu acima para explorar as visualizações.")

# ── Filtrar dados ─────────────────────────────────────────────────────────────
df_filtrado = df[
    df["ano"].isin(anos_selecionados) &
    df["secao"].isin(secoes_selecionadas)
]

# ── Cabeçalho da página ───────────────────────────────────────────────────────
titulo_com_logo("Visão Geral")
st.markdown(
    "Dashboard interativo com os indicadores do **Levantamento de Estatísticas Mensais (LEM)** "
    "da Fundação Pão dos Pobres · período **2021–2025**."
)
st.divider()

# ── Resumo em palavras ────────────────────────────────────────────────────────
st.info("📝 **Resumo em palavras**  \n" + "  \n".join(resumo_geral(df_filtrado)))

# ── Métricas de resumo ────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

total_registros = df_filtrado["valor"].sum(skipna=True)
total_indicadores = df_filtrado["indicador"].nunique()
anos_cobertos = df_filtrado["ano"].nunique()
pct_completo = (df_filtrado["valor"].notna().sum() / len(df_filtrado) * 100) if len(df_filtrado) > 0 else 0

col1.metric("Total de registros", f"{int(total_registros):,}".replace(",", "."))
col2.metric("Indicadores únicos", total_indicadores)
col3.metric("Anos cobertos", anos_cobertos)
col4.metric("Completude dos dados", f"{pct_completo:.1f}%")

st.divider()

# ── Gráfico: volume total por ano ─────────────────────────────────────────────
st.subheader("Volume total por ano")

st.markdown(
    "**📌 O que este gráfico mostra:** aqui somamos **todos** os registros do LEM (todas as "
    "seções e indicadores juntos) por ano, dando uma visão panorâmica de como o volume total "
    "de atendimentos e atividades da Fundação evoluiu de 2021 a 2025. É o ponto de partida "
    "para saber se a instituição está registrando mais ou menos atividade ao longo do tempo, "
    "antes de detalhar por seção, indicador ou mês nas páginas seguintes."
)

df_ano = (
    df_filtrado
    .groupby("ano")["valor"]
    .sum()
    .reset_index(name="Volume Total")
)

fig_ano = px.area(
    df_ano,
    x="ano",
    y="Volume Total",
    markers=True,
    template="plotly_white",
    color_discrete_sequence=["#2E86AB"],
    labels={"ano": "Ano", "Volume Total": "Soma dos valores"},
)
fig_ano.update_traces(
    text=df_ano["Volume Total"].astype(int),
    textposition="top center",
    mode="lines+markers+text",
)
fig_ano.update_xaxes(tickmode="linear", dtick=1)
fig_ano.update_layout(height=360, margin=dict(t=20, b=20))
st.plotly_chart(fig_ano, use_container_width=True)

st.divider()

# ── Gráfico: volume por seção ─────────────────────────────────────────────────
st.subheader("Volume por seção temática")

st.markdown(
    "**📌 O que este gráfico mostra:** aqui os registros de **todo o período** (2021–2025) "
    "são somados e agrupados pelas 4 seções temáticas do LEM (Desdobramentos Técnicos, "
    "Educação, Profissionalização e Saúde). Ele responde à pergunta: qual área da instituição "
    "concentra mais atividade registrada em termos absolutos? É o ponto de partida para "
    "decidir onde vale a pena aprofundar a análise nas páginas de Composição e Evolução."
)

df_secao = (
    df_filtrado
    .groupby("secao")["valor"]
    .sum()
    .reset_index(name="Volume")
    .sort_values("Volume", ascending=False)
)

fig_secao = px.bar(
    df_secao,
    x="Volume",
    y="secao",
    orientation="h",
    color="secao",
    color_discrete_map=CORES_SECAO,
    template="plotly_white",
    labels={"secao": "", "Volume": "Soma dos valores"},
)
fig_secao.update_layout(
    showlegend=False,
    height=260,
    margin=dict(t=20, b=20, l=10),
    yaxis=dict(autorange="reversed"),
)
st.plotly_chart(fig_secao, use_container_width=True)
