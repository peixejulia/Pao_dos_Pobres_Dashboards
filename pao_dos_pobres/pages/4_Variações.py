"""
Página 4 — Quais indicadores variaram mais entre anos?

Visualizações:
  • Dumbbell Chart         — comparação direta entre dois anos
  • Parallel Coordinates   — todos os anos simultaneamente
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from utils.data import carregar_desdobramentos
from utils.style import CORES_SECAO, ANOS, PLOTLY_TEMPLATE, titulo_com_logo
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
st.subheader(f"Dumbbell Chart — {ano_a} vs {ano_b}")
st.markdown(
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

# ── VIZ 4B: Parallel Coordinates ──────────────────────────────────────────────
st.subheader("Parallel Coordinates — Todos os anos simultaneamente")
st.markdown(
    "**📌 O que este gráfico mostra:** ele expande a análise do Dumbbell Chart acima para "
    "**todos os 5 anos ao mesmo tempo**, permitindo ver a trajetória completa de cada "
    "indicador, não só o ponto de partida e o de chegada. É útil para identificar **padrões "
    "de crescimento consistente**, **quedas pontuais isoladas** (que passariam despercebidas "
    "numa comparação de só dois anos) ou **instabilidade** ao longo de todo o período "
    "analisado, por seção (indicada pela cor)."
)

with st.expander("ℹ️ Como ler este gráfico"):
    st.markdown(
        "**A ideia geral:** enquanto o Dumbbell Chart acima compara só dois anos, este "
        "gráfico mostra **todos os anos ao mesmo tempo**, um indicador de cada vez, como um "
        "conjunto de retas paralelas.\n\n"
        "**Os eixos:** cada **coluna vertical** representa um **ano** (2021 a 2025, da "
        "esquerda para a direita). A posição de um ponto na coluna é o **volume de "
        "registros** daquele indicador naquele ano — mais para cima significa mais volume.\n\n"
        "**As linhas:** cada **linha colorida** que atravessa as colunas representa um "
        "**indicador**, e a cor indica a **seção** dele (veja a barra de cores à direita). "
        "Se a linha **sobe** de uma coluna para a próxima, o indicador **cresceu** naquele "
        "ano; se **desce**, **caiu**. Linhas praticamente retas (nem sobem nem descem muito) "
        "indicam **estabilidade** ao longo do tempo.\n\n"
        "**Dica de interação:** você pode **clicar e arrastar verticalmente sobre o eixo de "
        "um ano específico** para criar um filtro — isso destaca só as linhas que passam "
        "pela faixa de valores selecionada, útil para achar indicadores com volume alto ou "
        "baixo num ano específico. Clique novamente no eixo para remover o filtro."
    )

# Pivot: indicador × ano → volume
df_pivot = df_anual.pivot_table(
    index=["indicador", "secao"], columns="ano", values="Volume", aggfunc="sum"
).reset_index()
df_pivot.columns.name = None
df_pivot.columns = [str(c) for c in df_pivot.columns]

anos_cols = [str(a) for a in ANOS if str(a) in df_pivot.columns]

# Codificar seção como número para colorir
secao_list = sorted(df_pivot["secao"].unique())
secao_num = {s: i for i, s in enumerate(secao_list)}
df_pivot["secao_num"] = df_pivot["secao"].map(secao_num)

dimensions = [
    dict(label=a, values=df_pivot[a].fillna(0))
    for a in anos_cols
]

fig_pc = go.Figure(go.Parcoords(
    line=dict(
        color=df_pivot["secao_num"],
        colorscale=[
            [0,    "#2E86AB"],
            [0.33, "#A23B72"],
            [0.66, "#F18F01"],
            [1,    "#C73E1D"],
        ],
        showscale=True,
        colorbar=dict(
            title="Seção",
            tickvals=list(secao_num.values()),
            ticktext=list(secao_num.keys()),
            len=0.6,
        ),
    ),
    dimensions=dimensions,
    labelangle=-20,
))

fig_pc.update_layout(
    template=PLOTLY_TEMPLATE,
    height=500,
    margin=dict(t=60, b=40, l=80, r=80),
)
st.plotly_chart(fig_pc, use_container_width=True)

# Tabela auxiliar com variação absoluta
with st.expander("Ver tabela de variações"):
    if ano_a != ano_b and "df_db" in dir():
        tbl = df_db[["secao", "indicador", "vol_a", "vol_b", "variacao"]].copy()
        tbl.columns = ["Seção", "Indicador", str(ano_a), str(ano_b), "Variação"]
        tbl = tbl.sort_values("Variação", ascending=False).reset_index(drop=True)
        st.dataframe(tbl, use_container_width=True)
