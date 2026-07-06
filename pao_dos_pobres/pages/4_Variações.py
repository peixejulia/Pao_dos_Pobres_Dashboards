"""
Página 4 — Quais indicadores variaram mais entre anos?

Visualizações:
  • Dumbbell Chart         — comparação direta entre dois anos
  • Evolução multianual    — todos os anos simultaneamente, com seletor para
                             ver agregado por seção ou detalhado por indicador
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from utils.data import carregar_desdobramentos
from utils.style import CORES_SECAO, ANOS, PLOTLY_TEMPLATE, titulo_com_logo, explicacao_grafico, paleta_institucional
from utils.insights import resumo_variacoes

# ── Dados ─────────────────────────────────────────────────────────────────────
df = carregar_desdobramentos()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Filtros")
    secoes = st.multiselect(
        "Seções", sorted(df["secao"].unique()), default=sorted(df["secao"].unique())
    )
    st.divider()
    st.markdown("**Dumbbell — escolha os anos**")
    ano_a = st.selectbox("Ano inicial", ANOS, index=0)
    ano_b = st.selectbox("Ano final",   ANOS, index=len(ANOS) - 1)

df_f = df[df["secao"].isin(secoes)]

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
titulo_com_logo("Variações entre Anos")
st.markdown("**PQ4** · Quais indicadores apresentaram maiores variações entre os anos?")
st.divider()

# ── Dados anuais por indicador ────────────────────────────────────────────────
df_anual = (
    df_f
    .groupby(["ano", "secao", "indicador"])["valor"]
    .sum()
    .reset_index(name="Volume")
)

# ── VIZ 4A: Dumbbell Chart ────────────────────────────────────────────────────
st.subheader(f"Comparação direta entre {ano_a} e {ano_b}")
st.caption("Técnica: Dumbbell Chart")
explicacao_grafico(
    "**📌 O que este gráfico mostra:** ele compara, indicador por indicador, o volume "
    "registrado nos **dois anos específicos** escolhidos na barra lateral. Responde "
    "diretamente à pergunta: quais indicadores mais **cresceram ou caíram** entre esses "
    "dois anos, e qual foi a magnitude dessa mudança? É a forma mais direta de medir "
    "variação entre dois pontos no tempo, sem o \"ruído\" dos anos intermediários."
)

if ano_a == ano_b:
    st.warning("Selecione anos diferentes para comparar.")
else:
    df_a = df_anual[df_anual["ano"] == ano_a][["indicador", "secao", "Volume"]].rename(columns={"Volume": "vol_a"})
    df_b = df_anual[df_anual["ano"] == ano_b][["indicador", "Volume"]].rename(columns={"Volume": "vol_b"})
    df_db = df_a.merge(df_b, on="indicador", how="inner")
    df_db["variacao"] = df_db["vol_b"] - df_db["vol_a"]
    df_db["cor"] = df_db["variacao"].apply(lambda v: "#27ae60" if v >= 0 else "#c0392b")
    df_db = df_db.sort_values("variacao")

    # ── Resumo em palavras ────────────────────────────────────────────────────
    st.info("📝 **Resumo em palavras**  \n" + "  \n".join(resumo_variacoes(df_db, ano_a, ano_b)))

    fig_db = go.Figure()

    for _, row in df_db.iterrows():
        fig_db.add_shape(
            type="line",
            x0=row["vol_a"], x1=row["vol_b"],
            y0=row["indicador"], y1=row["indicador"],
            line=dict(color=row["cor"], width=2),
        )

    # Ponto ano A
    fig_db.add_trace(go.Scatter(
        x=df_db["vol_a"], y=df_db["indicador"],
        mode="markers",
        name=str(ano_a),
        marker=dict(size=10, color="#2E86AB", symbol="circle"),
        hovertemplate=f"<b>%{{y}}</b><br>{ano_a}: %{{x:,.0f}}<extra></extra>",
    ))
    # Ponto ano B
    fig_db.add_trace(go.Scatter(
        x=df_db["vol_b"], y=df_db["indicador"],
        mode="markers",
        name=str(ano_b),
        marker=dict(size=10, color="#e67e22", symbol="diamond"),
        hovertemplate=f"<b>%{{y}}</b><br>{ano_b}: %{{x:,.0f}}<extra></extra>",
    ))

    fig_db.update_layout(
        template=PLOTLY_TEMPLATE,
        height=max(400, len(df_db) * 28 + 100),
        margin=dict(l=260, r=40, t=20, b=40),
        xaxis=dict(title="Volume anual"),
        yaxis=dict(title="", tickfont=dict(size=10)),
        legend=dict(orientation="h", y=-0.08),
    )
    st.plotly_chart(fig_db, use_container_width=True)

st.divider()

# ── VIZ 4B: Evolução multianual por indicador ─────────────────────────────────
st.subheader("Trajetória de cada indicador ao longo dos 5 anos")
st.caption("Técnica: gráfico de linhas multianual")
explicacao_grafico(
    "**📌 O que este gráfico mostra:** ele expande a análise do Dumbbell Chart acima para "
    "**todos os 5 anos ao mesmo tempo**, permitindo ver a trajetória completa de cada "
    "indicador, não só o ponto de partida e o de chegada. É útil para identificar **padrões "
    "de crescimento consistente**, **quedas pontuais isoladas** (que passariam despercebidas "
    "numa comparação de só dois anos) ou **instabilidade** ao longo de todo o período "
    "analisado. Use o seletor **\"Ver por\"** abaixo para alternar entre uma visão "
    "agregada por seção ou o detalhe de cada indicador dentro de uma seção específica."
)

with st.expander("ℹ️ Como ler este gráfico"):
    st.markdown(
        "**A ideia geral:** enquanto o Dumbbell Chart acima compara só dois anos, este "
        "gráfico mostra **todos os anos ao mesmo tempo**, um indicador de cada vez, como um "
        "conjunto de linhas.\n\n"
        "**Os eixos:** o eixo horizontal é o **ano** (2021 a 2025) e o eixo vertical é o "
        "**volume de registros**. Todos os anos compartilham a mesma escala vertical, "
        "então **subir de verdade significa mais volume** — diferente de um Parallel "
        "Coordinates \"clássico\", que reescala cada ano de forma independente e pode "
        "distorcer essa leitura.\n\n"
        "**O seletor \"Ver por\":**\n"
        "- **Todas as seções** — mostra uma cor por **seção** (4 cores), útil pra comparar "
        "o comportamento geral das 4 grandes áreas.\n"
        "- **Uma seção específica** (ex.: \"Educação\") — mostra só os indicadores daquela "
        "seção, cada um com sua **própria cor e entrada na legenda**, útil pra investigar "
        "o comportamento de cada indicador individualmente sem competir visualmente com "
        "as outras seções.\n\n"
        "**Dica de interação:** clique num nome na legenda à direita para **esconder ou "
        "mostrar aquela linha (ou seção, no modo agregado) individualmente**. Para filtrar "
        "quais seções entram no gráfico desde o início, use a caixa **\"Seções\"** na "
        "barra lateral."
    )

# Pivot: indicador × ano → volume
df_pivot = df_anual.pivot_table(
    index=["indicador", "secao"], columns="ano", values="Volume", aggfunc="sum"
).reset_index()
df_pivot.columns.name = None
df_pivot.columns = [str(c) for c in df_pivot.columns]

anos_cols = [str(a) for a in ANOS if str(a) in df_pivot.columns]

VISAO_AGREGADA = "Todas as seções (comparar por seção)"
opcoes_visao = [VISAO_AGREGADA] + sorted(df_pivot["secao"].unique())

col_visao, col_escala = st.columns([2, 1])
with col_visao:
    visao_selecionada = st.selectbox(
        "Ver por:",
        opcoes_visao,
        index=0,
        help="Escolha uma seção específica para colorir e nomear cada indicador individualmente.",
    )
with col_escala:
    escala_log = st.checkbox(
        "Escala logarítmica",
        value=False,
        help="Ajuda a ver indicadores de baixo volume que ficam \"achatados\" perto do "
        "zero ao lado de indicadores muito maiores.",
    )

fig_pc = go.Figure()

if visao_selecionada == VISAO_AGREGADA:
    st.caption("Mostrando: comparação agregada por seção (uma cor por seção).")
    secoes_ja_na_legenda = set()
    for _, row in df_pivot.sort_values("secao").iterrows():
        secao = row["secao"]
        y_vals = [row[a] for a in anos_cols]
        primeira_da_secao = secao not in secoes_ja_na_legenda
        secoes_ja_na_legenda.add(secao)

        fig_pc.add_trace(go.Scatter(
            x=anos_cols,
            y=y_vals,
            mode="lines+markers",
            line=dict(color=CORES_SECAO.get(secao, "#888888"), width=3),
            marker=dict(size=6),
            opacity=0.65,
            name=secao,
            legendgroup=secao,
            showlegend=primeira_da_secao,
            text=[row["indicador"]] * len(anos_cols),
            hovertemplate="<b>%{text}</b><br>%{x}: %{y:,.0f}<extra></extra>",
        ))
    titulo_legenda = "Seção"
else:
    df_secao_sel = df_pivot[df_pivot["secao"] == visao_selecionada].sort_values("indicador")
    st.caption(
        f"Mostrando: {len(df_secao_sel)} indicador(es) da seção **{visao_selecionada}**, "
        "cada um com sua própria cor."
    )
    paleta_indicadores = paleta_institucional(len(df_secao_sel))

    for i, (_, row) in enumerate(df_secao_sel.iterrows()):
        indicador = row["indicador"]
        y_vals = [row[a] for a in anos_cols]
        cor = paleta_indicadores[i]

        fig_pc.add_trace(go.Scatter(
            x=anos_cols,
            y=y_vals,
            mode="lines+markers",
            line=dict(color=cor, width=3),
            marker=dict(size=6),
            opacity=0.85,
            name=indicador,
            legendgroup=indicador,
            showlegend=True,
            text=[indicador] * len(anos_cols),
            hovertemplate="<b>%{text}</b><br>%{x}: %{y:,.0f}<extra></extra>",
        ))
    titulo_legenda = "Indicador"

fig_pc.update_layout(
    template=PLOTLY_TEMPLATE,
    height=520,
    margin=dict(t=40, b=40, l=60, r=40),
    xaxis=dict(title="Ano", type="category"),
    yaxis=dict(title="Volume anual", type="log" if escala_log else "linear"),
    legend=dict(title=titulo_legenda, groupclick="togglegroup"),
)
st.plotly_chart(fig_pc, use_container_width=True)

# Tabela auxiliar com variação absoluta
with st.expander("Ver tabela de variações"):
    if ano_a != ano_b and "df_db" in dir():
        tbl = df_db[["secao", "indicador", "vol_a", "vol_b", "variacao"]].copy()
        tbl.columns = ["Seção", "Indicador", str(ano_a), str(ano_b), "Variação"]
        tbl = tbl.sort_values("Variação", ascending=False).reset_index(drop=True)
        st.dataframe(tbl, use_container_width=True)
