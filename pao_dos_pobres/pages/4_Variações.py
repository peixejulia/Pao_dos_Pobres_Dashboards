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
from utils.style import CORES_SECAO, ANOS, PLOTLY_TEMPLATE

st.set_page_config(page_title="Variações · LEM", layout="wide")

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
st.title("↕️ Variações entre Anos")
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
st.caption("Cada linha conecta o volume do ano inicial ao ano final. Verde = crescimento · Vermelho = queda.")

if ano_a == ano_b:
    st.warning("Selecione anos diferentes para comparar.")
else:
    df_a = df_anual[df_anual["ano"] == ano_a][["indicador", "secao", "Volume"]].rename(columns={"Volume": "vol_a"})
    df_b = df_anual[df_anual["ano"] == ano_b][["indicador", "Volume"]].rename(columns={"Volume": "vol_b"})
    df_db = df_a.merge(df_b, on="indicador", how="inner")
    df_db["variacao"] = df_db["vol_b"] - df_db["vol_a"]
    df_db["cor"] = df_db["variacao"].apply(lambda v: "#27ae60" if v >= 0 else "#c0392b")
    df_db = df_db.sort_values("variacao")

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
    st.plotly_chart(fig_db, width='stretch')

st.divider()

# ── VIZ 4B: Parallel Coordinates ──────────────────────────────────────────────
st.subheader("Parallel Coordinates — Todos os anos simultaneamente")
st.caption("Cada linha = um indicador. Passe o cursor para destacar. Linhas ascendentes = crescimento.")

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
st.plotly_chart(fig_pc, width='stretch')

# Tabela auxiliar com variação absoluta
with st.expander("Ver tabela de variações"):
    if ano_a != ano_b and "df_db" in dir():
        tbl = df_db[["secao", "indicador", "vol_a", "vol_b", "variacao"]].copy()
        tbl.columns = ["Seção", "Indicador", str(ano_a), str(ano_b), "Variação"]
        tbl = tbl.sort_values("Variação", ascending=False).reset_index(drop=True)
        st.dataframe(tbl, width='stretch')
