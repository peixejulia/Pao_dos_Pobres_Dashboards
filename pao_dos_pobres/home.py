"""
home.py — Página inicial do dashboard Pão dos Pobres.
Executada via st.navigation()/st.Page() a partir de app.py.
"""
import streamlit as st
import plotly.express as px
import pandas as pd

from utils.data import carregar_desdobramentos, carregar_gerencial, anos_disponiveis
from utils.style import CORES_SECAO, titulo_com_logo, explicacao_grafico
from utils.insights import resumo_geral

# ── Carregamento de dados ─────────────────────────────────────────────────────
df = carregar_desdobramentos()
ANOS = anos_disponiveis()  # dinâmico: reflete os anos realmente presentes na base

# ── Sidebar — filtros globais ─────────────────────────────────────────────────
with st.sidebar:
    titulo_com_logo("Pão dos Pobres", nivel=2)
    st.caption(f"Levantamento de Estatísticas Mensais (LEM) · {min(ANOS)}–{max(ANOS)}")
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
    "Este painel reúne os indicadores do **Levantamento de Estatísticas Mensais (LEM)** da "
    f"Fundação Pão dos Pobres, referentes ao período de **{min(ANOS)} a {max(ANOS)}**. Ele acompanha o volume "
    "de atendimentos e atividades em quatro grandes áreas de atuação da instituição — "
    "**Desdobramentos Técnicos, Educação, Profissionalização e Saúde** — e ajuda a responder "
    "perguntas como: os atendimentos estão aumentando ou diminuindo ao longo do tempo? Existem "
    "meses ou épocas do ano com mais demanda? Como as seções e indicadores se comparam entre "
    "si? O que mudou de um ano para o outro? E quão completos estão os registros mensais? Cada "
    "página no menu ao lado explora uma dessas perguntas em profundidade."
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

explicacao_grafico(
    "**📌 O que este gráfico mostra:** aqui somamos **todos** os registros do LEM (todas as "
    "seções e indicadores juntos) por ano, dando uma visão panorâmica de como o volume total "
    f"de atendimentos e atividades da Fundação evoluiu de {min(ANOS)} a {max(ANOS)}. É o ponto de partida "
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
    color_discrete_sequence=[CORES_SECAO["Desdobramentos Técnicos"]],
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

explicacao_grafico(
    f"**📌 O que este gráfico mostra:** aqui os registros de **todo o período** ({min(ANOS)}–{max(ANOS)}) "
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
