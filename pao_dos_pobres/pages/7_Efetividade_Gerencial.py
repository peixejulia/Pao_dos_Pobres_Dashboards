"""
Página 7 — Efetividade Gerencial

Explora um conjunto de dados diferente do principal (lem_gerencial_2025.csv):
indicadores de efetividade social levantados pela Fundação, complementares
aos indicadores de volume do LEM Desdobramentos usados nas demais páginas.

Todo texto que menciona ano, período de meses ou nº de indicadores é
calculado a partir do próprio arquivo (ver utils.data.periodo_gerencial) —
não há nada fixo em "2025" ou "jan–nov" no código, para que a página
continue correta se a planilha for atualizada no futuro (ex.: dezembro
preenchido, ou um novo ano adicionado).

Visualizações:
  • KPIs de efetividade — nível mais recente e variação no ano
  • Gráfico de Linha — evolução mensal de um indicador
  • Gráfico de Barras — comparação entre indicadores (valor médio mensal)
"""
import streamlit as st
import plotly.express as px
import pandas as pd

from utils.data import carregar_gerencial, periodo_gerencial, nome_mes
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
info = periodo_gerencial(df)

_periodo_texto = info["periodo_label"]
if info["faltantes_label"]:
    _periodo_texto += f" — {info['faltantes_label']} ainda não preenchido(s)"

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
    f"Esta página explora um conjunto de dados diferente das demais: os "
    f"**{info['n_indicadores']} indicadores de efetividade social** "
    f"levantados pela Fundação em **{info['ano_label']}** ({_periodo_texto}), "
    "separados do LEM principal por terem uma estrutura própria. Diferente "
    "das outras páginas, aqui o foco é a evolução *dentro* do período "
    "disponível, não a comparação entre anos."
)
st.caption(
    "📌 Os indicadores foram agrupados em 3 categorias — **Atendimento e "
    "Permanência**, **Inserção e Efetividade** e **Equipe e Atividades** — "
    "para facilitar a leitura. Além disso, alguns indicadores são um "
    "**retrato do mês** (ex.: quantos apadrinhamentos afetivos estão "
    "ativos agora) e outros contam **eventos ocorridos no mês** (ex.: "
    "quantas crianças foram atendidas, quantos desligamentos "
    "aconteceram); por isso os KPIs abaixo mostram o nível mais recente "
    "para os primeiros, e o total acumulado no período para os segundos "
    "— passe o mouse sobre o ícone **(?)** de cada indicador para ver "
    "exatamente o que o número e a variação significam."
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
st.subheader(f"Panorama de {info['ano_label']}")
explicacao_grafico(
    f"Os números principais resumem o ano todo ({info['ano_label']}): total "
    "acumulado no período para indicadores de evento (ex.: crianças "
    "atendidas, desligamentos), ou o valor do mês mais recente para "
    "indicadores de retrato/nível (ex.: apadrinhamentos ativos agora). A "
    "variação (▲/▼) abaixo do número compara o primeiro mês disponível "
    "com o mês mais recente, só para indicar se a tendência é de alta ou "
    "queda — não é uma média nem uma medida de oscilação mês a mês. "
    "Passe o mouse no ícone **(?)** de cada card para o detalhe exato."
)


def _serie(indicador: str) -> pd.DataFrame:
    return (
        df[df["indicador"] == indicador]
        .dropna(subset=["valor"])
        .sort_values("mes_num")
    )


def _kpi_nivel(col, indicador: str, rotulo: str):
    """
    Indicadores tipo 'nível' são um retrato de um momento (ex.: quantas
    crianças estão sendo atendidas), então o número mostrado é o valor do
    MÊS MAIS RECENTE com dado — não uma média nem uma soma. A variação
    (delta) compara esse valor mais recente com o do primeiro mês
    disponível no período, e o texto do delta já deixa os dois meses
    explícitos para não depender de "adivinhar" o que "+1 no ano" significa.
    """
    s = _serie(indicador)
    if s.empty:
        col.metric(rotulo, "—")
        return
    atual = s["valor"].iloc[-1]
    inicial = s["valor"].iloc[0]
    mes_atual_nome = nome_mes(int(s["mes_num"].iloc[-1]))
    mes_inicial_nome = nome_mes(int(s["mes_num"].iloc[0]))
    delta = atual - inicial

    ajuda = (
        f"**{atual:.0f}** é o valor de **{mes_atual_nome}**, o mês mais "
        f"recente com dado — este indicador é um retrato do mês (nível), "
        f"então o número não é uma média nem um total, é a contagem "
        f"naquele mês específico."
    )
    delta_label = None
    if len(s) > 1:
        ajuda += (
            f"\n\nA variação **{delta:+.0f}** compara {mes_inicial_nome} "
            f"({inicial:.0f}) com {mes_atual_nome} ({atual:.0f})."
        )
        delta_label = f"{delta:+.0f} vs. {mes_inicial_nome}"

    col.metric(rotulo, f"{atual:.0f}", delta=delta_label, help=ajuda)


def _kpi_total(col, indicadores: list, rotulo: str, mostrar_variacao: bool = False):
    """
    Indicadores tipo 'evento' contam ocorrências no mês (ex.: desligamentos,
    crianças atendidas), então somar os meses do período é uma soma válida.
    O número mostrado aqui é o TOTAL ACUMULADO no período disponível — não
    uma média.

    Se `mostrar_variacao=True`, o delta abaixo do total compara o mês mais
    recente com o primeiro mês disponível (soma de todos os indicadores
    daquele mês) — indica se o RITMO mensal está subindo ou caindo, mesmo
    com o valor principal sendo um total acumulado.
    """
    total = 0.0
    por_mes = None
    for ind in indicadores:
        s = _serie(ind)
        total += s["valor"].sum()
        agrupado = s.groupby("mes_num")["valor"].sum()
        por_mes = agrupado if por_mes is None else por_mes.add(agrupado, fill_value=0)

    ajuda = (
        f"**{total:.0f}** é a soma de todos os meses com dado em "
        f"{info['ano_label']} ({_periodo_texto}) — este indicador conta "
        f"eventos ocorridos no mês, então somar os meses faz sentido: é o "
        f"total acumulado no período, não uma média mensal."
    )

    delta_label = None
    if mostrar_variacao and por_mes is not None and len(por_mes) > 1:
        por_mes = por_mes.sort_index()
        mes_ini_num, mes_fim_num = int(por_mes.index[0]), int(por_mes.index[-1])
        valor_ini, valor_fim = por_mes.iloc[0], por_mes.iloc[-1]
        mes_ini_nome, mes_fim_nome = nome_mes(mes_ini_num), nome_mes(mes_fim_num)
        delta = valor_fim - valor_ini
        delta_label = f"{delta:+.0f} vs. {mes_ini_nome}"
        ajuda += (
            f"\n\nA variação **{delta:+.0f}** compara o ritmo mensal de "
            f"{mes_ini_nome} ({valor_ini:.0f}) com {mes_fim_nome} "
            f"({valor_fim:.0f}) — não altera o total, só indica se o "
            f"número de casos por mês está subindo ou caindo."
        )

    col.metric(rotulo, f"{total:.0f}", delta=delta_label, help=ajuda)


linha1 = st.columns(3)
linha2 = st.columns(2)
_kpi_total(linha1[0], ["Número De Crianças E Adolescentes Atendidos"], "Jovens atendidos", mostrar_variacao=True)
_kpi_nivel(linha1[1], "Adolescentes Inseridos Em Cursos Profissionalizantes", "Cursos profissionalizantes")
_kpi_nivel(linha1[2], "Adolescentes Inseridos No Mercado De Trabalho", "Mercado de trabalho")
_kpi_nivel(linha2[0], "Apadrinhamentos Afetivos Efetivados", "Apadrinhamentos ativos")
_kpi_total(linha2[1], ["Crianças E Adolescentes/Desligamentos", "Crianças E Adolescentes/Evasões"], "Desligamentos + evasões")

if _serie("Adolescentes Inseridos No Mercado De Trabalho")["valor"].sum() == 0:
    st.caption(f"⚠️ Nenhuma inserção no mercado de trabalho registrada em {info['ano_label']} até o momento.")

st.divider()

# ── Gráfico de Linha — evolução mensal de um indicador ────────────────────────
st.subheader("Evolução mensal de um indicador")
st.caption("Técnica: gráfico de linha")
explicacao_grafico(
    f"**📌 O que este gráfico mostra:** escolha um indicador e veja como ele "
    f"variou mês a mês em {info['ano_label']}. Como só há um ano disponível, "
    "esse é o principal recurso desta página para acompanhar tendências — "
    "por exemplo, se as inserções em cursos estão subindo ou caindo ao "
    "longo do período."
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
st.subheader(f"Comparação entre indicadores: valor médio mensal em {info['ano_label']}")
st.caption("Técnica: gráfico de barras horizontais")
explicacao_grafico(
    "**📌 O que este gráfico mostra:** compara todos os indicadores "
    "selecionados pela **média mensal** do período. Usamos a média (em vez "
    "do total) porque ela é comparável entre indicadores de naturezas "
    "diferentes — tanto para um indicador de retrato do mês (ex.: "
    "apadrinhamentos ativos) quanto para um de eventos (ex.: crianças "
    "atendidas, desligamentos), a média responde à mesma pergunta: "
    "\"quanto isso representa, tipicamente, em um mês do período?\""
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
        f"Os dados desta página vêm de um arquivo separado do LEM principal "
        f"(planilha *LEM anual completo.xlsx*), com estrutura própria e "
        f"cobertura de **{info['ano_label']}** — por isso os filtros de ano "
        "e as comparações entre anos das demais páginas não se aplicam "
        "aqui. Se a Fundação enviar mais meses ou um novo ano para este "
        "arquivo, os textos e gráficos desta página se atualizam sozinhos "
        "para refletir o período disponível. A planilha original também "
        "continha abas de detalhamento de capacitações de equipe e de "
        "coordenações (tema, local, carga horária), mas essas abas estavam "
        "preenchidas de forma muito incompleta (2 registros cada) para "
        "gerar uma visualização própria — os totais mensais de "
        "capacitações seguem representados nos gráficos acima."
    )
