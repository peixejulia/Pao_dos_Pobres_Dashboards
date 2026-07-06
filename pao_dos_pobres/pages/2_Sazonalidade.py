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
from utils.style import CORES_SECAO, ANOS, ORDEM_MES, PLOTLY_TEMPLATE, titulo_com_logo, explicacao_grafico, paleta_azuis
from utils.insights import resumo_sazonalidade

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
titulo_com_logo("Sazonalidade dos Registros")
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
st.subheader("Quais meses concentram mais atendimentos, comparando os anos")
st.caption("Técnica: Gráfico de Rosa (Polar Bar Chart)")
explicacao_grafico(
    "**📌 O que este gráfico mostra:** ele analisa a **sazonalidade** dos registros, "
    "cruzando o mês do ano com o ano civil — ou seja, mostra o volume mês a mês, ano a ano, "
    "só que organizado em círculo em vez de em linha do tempo. Ele ajuda a responder: "
    "existem meses que sistematicamente concentram mais (ou menos) atendimentos e atividades, "
    "e esse padrão se repete de um ano para o outro? Essa informação é útil para "
    "**planejamento operacional** — por exemplo, se setembro é sempre um mês de pico, a "
    "equipe pode se preparar com antecedência para os anos seguintes."
)

with st.expander("ℹ️ Como ler este gráfico"):
    st.markdown(
        "**A ideia geral:** este é um gráfico de barras \"dobrado\" em círculo. Pense em um "
        "relógio — cada fatia é um mês, começando em **Janeiro no topo** e girando no "
        "sentido horário até **Dezembro**.\n\n"
        "**O que cada cor significa:** dentro de cada fatia (mês) existem várias barrinhas "
        "coloridas lado a lado, uma para **cada ano** (veja a legenda embaixo do gráfico). "
        "Isso permite comparar o mesmo mês em anos diferentes — por exemplo, ver se Setembro "
        "de 2025 teve mais atendimentos do que Setembro de 2021.\n\n"
        "**O que o tamanho significa:** quanto **mais a barra se estende para fora do "
        "centro** (mais \"comprida\"), **mais registros** houve naquele mês/ano. Os números "
        "no eixo (0, 200, 400...) mostram a escala de volume.\n\n"
        "**A linha vermelha pontilhada** marca a **média geral** de todos os meses e anos "
        "juntos — barras que ultrapassam essa linha tiveram volume acima da média.\n\n"
        "**Dica:** clique nos anos da legenda para esconder/mostrar só os anos que quiser "
        "comparar; passe o mouse sobre uma barra para ver o valor exato."
    )

# Volume por ano e mês (uma série/cor por ano)
df_ano_mes = (
    df_viz
    .groupby(["ano", "mes"])["valor"]
    .sum()
    .reset_index(name="Volume")
)

# Degradê de azuis (do mais claro/2021 ao mais escuro/2025) em vez da paleta
# multicor do resto do painel — para os anos, que são um dado sequencial/
# ordenado, um único matiz variando em intensidade comunica melhor a
# progressão no tempo. Indexado pela posição do ano na lista ANOS (não pela
# posição no filtro), pra cada ano manter sempre o mesmo tom mesmo se a
# seleção da barra lateral mudar.
PALETA_ANOS = paleta_azuis(len(ANOS))
anos_presentes = sorted(df_ano_mes["ano"].unique())
cor_ano = {a: PALETA_ANOS[ANOS.index(a) % len(PALETA_ANOS)] for a in anos_presentes}

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
st.subheader("Volume detalhado por mês e ano")
st.caption("Técnica: Calendar Heatmap")
explicacao_grafico(
    "**📌 O que este gráfico mostra:** é a mesma informação de ano × mês do Gráfico de "
    "Rosa acima, só que em formato de tabela colorida, o que facilita a leitura de **números "
    "exatos** e a localização rápida de combinações específicas de ano e mês. Células cinzas "
    "indicam ausência total de dado naquele mês, o que também serve como um primeiro "
    "diagnóstico de qualidade dos dados (aprofundado na página Completude)."
)

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
