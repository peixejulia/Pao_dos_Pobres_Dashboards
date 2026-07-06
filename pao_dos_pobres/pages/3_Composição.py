"""
Página 3 — Quais áreas concentram mais registros?

Visualizações planejadas:
  • Sunburst Chart — hierarquia radial seção → indicador
  • Treemap        — mosaico de área proporcional
"""
import streamlit as st
import plotly.express as px
import pandas as pd

from utils.data import carregar_desdobramentos
from utils.style import CORES_SECAO, ANOS, PLOTLY_TEMPLATE, titulo_com_logo
from utils.insights import resumo_composicao

# ── Dados ─────────────────────────────────────────────────────────────────────
df = carregar_desdobramentos()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Filtros")
    anos = st.multiselect("Anos", ANOS, default=ANOS)
    secoes = st.multiselect(
        "Seções", sorted(df["secao"].unique()), default=sorted(df["secao"].unique())
    )

df_f = df[df["ano"].isin(anos) & df["secao"].isin(secoes)]

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
titulo_com_logo("Composição por Área Temática")
st.markdown("**PQ3** · Quais seções e indicadores concentram o maior volume de registros?")
st.divider()

# ── Dados agregados ───────────────────────────────────────────────────────────
df_agg = (
    df_f
    .groupby(["secao", "indicador"])["valor"]
    .sum()
    .reset_index(name="Volume")
)
df_agg = df_agg[df_agg["Volume"] > 0]

# Nome curto para rótulos internos
df_agg["ind_curto"] = df_agg["indicador"].apply(
    lambda s: s[:35] + "…" if len(s) > 35 else s
)

if df_agg.empty:
    st.info("Nenhum dado para os filtros selecionados.")
    st.stop()

# ── Resumo em palavras ────────────────────────────────────────────────────────
st.info("📝 **Resumo em palavras**  \n" + "  \n".join(resumo_composicao(df_agg)))

# ── Abas: uma para cada tipo de gráfico ───────────────────────────────────────
aba_sun, aba_tree = st.tabs(["☀️ Sunburst", "🗺️ Treemap"])

# ── VIZ 3A: Sunburst ──────────────────────────────────────────────────────────
with aba_sun:
    st.markdown(
        "**📌 O que este gráfico mostra:** ele analisa a **composição** do volume total de "
        "registros em duas camadas — primeiro por seção temática, depois por indicador dentro "
        "de cada seção. Mostra que fatia do total cada seção e cada indicador representam, "
        "ajudando a identificar rapidamente **onde a instituição concentra a maior parte da "
        "sua atividade registrada** no período e nos filtros selecionados."
    )

    with st.expander("ℹ️ Como ler este gráfico"):
        st.markdown(
            "**A ideia geral:** este gráfico mostra uma hierarquia em camadas circulares — "
            "primeiro por seção, depois por indicador dentro dela.\n\n"
            "**Camada interna (anel do meio):** cada fatia é uma das 4 **seções temáticas** "
            "(Desdobramentos Técnicos, Educação, Profissionalização, Saúde), coloridas de "
            "forma consistente com o restante do dashboard.\n\n"
            "**Camada externa:** cada fatia menor é um **indicador** específico dentro "
            "daquela seção. O **tamanho da fatia** (tanto na camada interna quanto na "
            "externa) é proporcional ao **volume de registros** — fatias maiores = mais "
            "registros.\n\n"
            "**Interação:** clique em uma fatia da seção para dar **zoom** e ver só os "
            "indicadores dela em detalhe; clique no centro do círculo para voltar à visão "
            "completa. Passe o mouse sobre qualquer fatia para ver o volume exato e o "
            "percentual que ela representa dentro da seção e do total geral."
        )

    fig_sun = px.sunburst(
        df_agg,
        path=["secao", "ind_curto"],
        values="Volume",
        color="secao",
        color_discrete_map=CORES_SECAO,
        hover_data={"indicador": True, "Volume": True},
        template=PLOTLY_TEMPLATE,
    )
    fig_sun.update_traces(
        textinfo="label+percent parent",
        insidetextorientation="radial",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Volume: %{value:,.0f}<br>"
            "% da seção: %{percentParent:.1%}<br>"
            "% do total: %{percentRoot:.1%}"
            "<extra></extra>"
        ),
    )
    fig_sun.update_layout(height=560, margin=dict(t=20, b=10))
    st.plotly_chart(fig_sun, use_container_width=True)

# ── VIZ 3B: Treemap ───────────────────────────────────────────────────────────
with aba_tree:
    st.markdown(
        "**📌 O que este gráfico mostra:** é a mesma análise de composição do Sunburst "
        "(seção → indicador), mas em formato de blocos retangulares, o que facilita "
        "**comparar visualmente o tamanho** de indicadores de seções diferentes lado a lado — "
        "algo mais difícil de perceber no formato circular."
    )

    with st.expander("ℹ️ Como ler este gráfico"):
        st.markdown(
            "**A ideia geral:** é a mesma informação do Sunburst (seção → indicador), só que "
            "organizada como um mosaico de retângulos em vez de um círculo — pode ser mais "
            "fácil de comparar tamanhos visualmente.\n\n"
            "**O que o tamanho significa:** cada **retângulo** é um indicador; a **área** "
            "dele é proporcional ao volume de registros — quanto **maior o bloco**, mais "
            "registros aquele indicador teve. Blocos maiores chamam mais atenção porque "
            "concentram mais volume.\n\n"
            "**O que a cor significa:** retângulos da **mesma cor** pertencem à **mesma "
            "seção temática** — isso ajuda a enxergar rapidamente quais seções dominam o "
            "espaço total.\n\n"
            "**Interação:** passe o mouse sobre qualquer bloco para ver o nome completo do "
            "indicador, o volume exato e o percentual que ele representa dentro da sua seção."
        )

    fig_tree = px.treemap(
        df_agg,
        path=[px.Constant("LEM"), "secao", "ind_curto"],
        values="Volume",
        color="secao",
        color_discrete_map=CORES_SECAO,
        hover_data={"indicador": True, "Volume": True},
        template=PLOTLY_TEMPLATE,
    )
    fig_tree.update_traces(
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Volume: %{value:,.0f}<br>"
            "% do pai: %{percentParent:.1%}"
            "<extra></extra>"
        ),
        textinfo="label+value",
    )
    fig_tree.update_layout(height=560, margin=dict(t=20, b=10))
    st.plotly_chart(fig_tree, use_container_width=True)
