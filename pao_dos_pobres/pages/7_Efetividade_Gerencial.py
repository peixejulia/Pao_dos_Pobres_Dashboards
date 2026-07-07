"""
Página 7 — Efetividade Gerencial

Explora um conjunto de dados diferente do principal (lem_gerencial_2025.csv):
13 indicadores de efetividade social levantados pela Fundação em 2025
(jan–nov), complementares aos indicadores de volume do LEM Desdobramentos
usados nas demais páginas.

Visualizações:
  • KPIs de efetividade — nível mais recente e variação no ano
  • Gráfico de Linha — evolução mensal de um indicador
  • Gráfico de Barras — comparação entre indicadores (valor médio mensal)
"""
import streamlit as st
import plotly.express as px
import pandas as pd

from utils.data import carregar_gerencial
from utils.style import (
    titulo_com_logo,
    explicacao_grafico,
    CATEGORIAS_GERENCIAL,
    CORES_CATEGORIA_GERENCIAL,
    TIPO_INDICADOR_GERENCIAL,
    categoria_do_indicador_gerencial,
)
from utils.insights import resumo_efetividade

# ── Dados ─────────────────────────────────────────────────────────────────────
df = carregar_gerencial()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Filtros")
    categorias_sel = st.multiselect(
        "Categorias",
        options=list(CATEGORIAS_GERENCIAL.keys()),
        default=list(CATEGORIAS_GERENCIAL.keys()),
    )

indicadores_permitidos = [
    ind for cat in categorias_sel for ind in CATEGORIAS_GERENCIAL[cat]
]
df_f = df[df["indicador"].isin(indicadores_permitidos)]

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
titulo_com_logo("Efetividade Gerencial")
st.markdown(
    "Esta página explora um conjunto de dados diferente das demais: os **13 "
    "indicadores de efetividade social** levantados pela Fundação em 2025 "
    "(janeiro a novembro — dezembro ainda não foi preenchido), separados do "
    "LEM principal por terem uma estrutura própria. Diferente das outras "
    "páginas, aqui só há **um ano** disponível, então o foco é a evolução "
    "*dentro* de 2025, não a comparação entre anos."
)
st.caption(
    "📌 Os indicadores foram agrupados em 3 categorias — **Atendimento e "
    "Permanência**, **Inserção e Efetividade** e **Equipe e Atividades** — "
    "para facilitar a leitura. Além disso, alguns indicadores são um "
    "**retrato do mês** (ex.: quantas crianças estão atualmente atendidas) "
    "e outros contam **eventos ocorridos no mês** (ex.: quantos "
    "desligamentos aconteceram); por isso os KPIs abaixo mostram o nível "
    "mais recente para os primeiros, e o total acumulado no ano para os "
    "segundos."
)
st.divider()

if not categorias_sel or df_f.empty:
    st.warning(
        "⚠️ Nenhum dado para os filtros selecionados. "
        "Marque pelo menos uma **Categoria** na barra lateral."
    )
    st.stop()

# ── Resumo em palavras ────────────────────────────────────────────────────────
st.info("📝 **Resumo em palavras**  \n" + "  \n".join(resumo_efetividade(df_f)))

# ── KPIs ────────────────────────────────────────────────────────────────────
st.subheader("Panorama de 2025")


def _serie(indicador: str) -> pd.DataFrame:
    return (
        df[df["indicador"] == indicador]
        .dropna(subset=["valor"])
        .sort_values("mes_num")
    )


def _kpi_nivel(col, indicador: str, rotulo: str):
    s = _serie(indicador)
    if s.empty:
        col.metric(rotulo, "—")
        return
    atual = s["valor"].iloc[-1]
    inicial = s["valor"].iloc[0]
    delta = atual - inicial
    col.metric(rotulo, f"{atual:.0f}", delta=f"{delta:+.0f} no ano" if len(s) > 1 else None)


def _kpi_total(col, indicadores: list, rotulo: str):
    total = 0.0
    for ind in indicadores:
        s = _serie(ind)
        total += s["valor"].sum()
    col.metric(rotulo, f"{total:.0f}")


c1, c2, c3, c4, c5 = st.columns(5)
_kpi_nivel(c1, "Número De Crianças E Adolescentes Atendidos", "Crianças e adolescentes atendidos")
_kpi_nivel(c2, "Adolescentes Inseridos Em Cursos Profissionalizantes", "Inseridos em cursos profissionalizantes")
_kpi_nivel(c3, "Adolescentes Inseridos No Mercado De Trabalho", "Inseridos no mercado de trabalho")
_kpi_nivel(c4, "Apadrinhamentos Afetivos Efetivados", "Apadrinhamentos afetivos ativos")
_kpi_total(c5, ["Crianças E Adolescentes/Desligamentos", "Crianças E Adolescentes/Evasões"], "Desligamentos + evasões no ano")

if _serie("Adolescentes Inseridos No Mercado De Trabalho")["valor"].sum() == 0:
    st.caption("⚠️ Nenhuma inserção no mercado de trabalho registrada em 2025 até o momento.")

st.divider()

# ── Gráfico de Linha — evolução mensal de um indicador ────────────────────────
st.subheader("Evolução mensal de um indicador")
st.caption("Técnica: gráfico de linha")
explicacao_grafico(
    "**📌 O que este gráfico mostra:** escolha um indicador e veja como ele "
    "variou mês a mês em 2025. Como só há um ano disponível, esse é o "
    "principal recurso desta página para acompanhar tendências — por "
    "exemplo, se as inserções em cursos estão subindo ou caindo ao longo "
    "do ano."
)

indicadores_disp = sorted(df_f["indicador"].unique())
indicador_sel = st.selectbox("Escolha um indicador", options=indicadores_disp, key="indicador_gerencial")

df_linha = (
    df_f[df_f["indicador"] == indicador_sel]
    .dropna(subset=["valor"])
    .sort_values("data")
)

if df_linha.empty:
    st.info("Nenhum dado para os filtros selecionados.")
else:
    categoria = categoria_do_indicador_gerencial(indicador_sel)
    tipo = TIPO_INDICADOR_GERENCIAL.get(indicador_sel, "evento")
    tipo_label = "retrato do mês" if tipo == "nivel" else "eventos no mês"
    st.caption(f"Categoria: {categoria} · Natureza do valor: {tipo_label}")

    fig_linha = px.line(
        df_linha,
        x="data",
        y="valor",
        markers=True,
        template="plotly_white",
        color_discrete_sequence=[CORES_CATEGORIA_GERENCIAL.get(categoria, "#2E86AB")],
        labels={"data": "Mês", "valor": "Valor"},
        hover_data={"mes": True},
    )
    fig_linha.update_traces(hovertemplate="<b>%{x|%b/%Y}</b><br>Valor: %{y:,.0f}<extra></extra>")
    fig_linha.update_layout(height=380, margin=dict(t=20, b=20), xaxis=dict(title="Mês"), yaxis=dict(title="Valor"))
    st.plotly_chart(fig_linha, use_container_width=True)

st.divider()

# ── Gráfico de Barras — comparação entre indicadores ──────────────────────────
st.subheader("Comparação entre indicadores: valor médio mensal em 2025")
st.caption("Técnica: gráfico de barras horizontais")
explicacao_grafico(
    "**📌 O que este gráfico mostra:** compara todos os indicadores "
    "selecionados pela **média mensal** de 2025. Usamos a média (em vez do "
    "total) porque ela é comparável entre indicadores de naturezas "
    "diferentes — tanto para um indicador de retrato do mês (ex.: crianças "
    "atendidas) quanto para um de eventos (ex.: desligamentos), a média "
    "responde à mesma pergunta: \"quanto isso representa, tipicamente, em "
    "um mês de 2025?\""
)

media_por_indicador = (
    df_f.dropna(subset=["valor"])
    .groupby("indicador")["valor"]
    .mean()
    .reset_index(name="media_mensal")
)
media_por_indicador["categoria"] = media_por_indicador["indicador"].apply(categoria_do_indicador_gerencial)
media_por_indicador = media_por_indicador.sort_values("media_mensal", ascending=True)

fig_barras = px.bar(
    media_por_indicador,
    x="media_mensal",
    y="indicador",
    orientation="h",
    color="categoria",
    color_discrete_map=CORES_CATEGORIA_GERENCIAL,
    template="plotly_white",
    labels={"media_mensal": "Valor médio mensal", "indicador": "", "categoria": "Categoria"},
)
fig_barras.update_layout(
    height=max(400, len(media_por_indicador) * 32 + 100),
    margin=dict(t=20, b=20, l=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)
st.plotly_chart(fig_barras, use_container_width=True)

st.divider()

with st.expander("ℹ️ Sobre estes dados"):
    st.markdown(
        "Os dados desta página vêm de um arquivo separado do LEM principal "
        "(planilha *LEM anual 2025 completo.xlsx*), com estrutura própria e "
        "cobertura de **apenas 2025** — por isso não aparecem filtros de ano "
        "ou comparações entre anos como nas demais páginas. A planilha "
        "original também continha abas de detalhamento de capacitações de "
        "equipe e de coordenações (tema, local, carga horária), mas essas "
        "abas estavam preenchidas de forma muito incompleta (2 registros "
        "cada) para gerar uma visualização própria — os totais mensais de "
        "capacitações seguem representados nos gráficos acima."
    )
