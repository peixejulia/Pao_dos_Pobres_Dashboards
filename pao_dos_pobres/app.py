"""
app.py — Roteador principal do dashboard Pão dos Pobres.

Define os nomes exibidos na navegação lateral do Streamlit via
st.navigation()/st.Page(), independente do nome dos arquivos.

Para rodar:  streamlit run app.py
"""
import streamlit as st

# ── Configuração da página (única para todo o app) ────────────────────────────
st.set_page_config(
    page_title="Pão dos Pobres — Dashboard LEM",
    page_icon="🏠",
    layout="wide",
)

# ── Páginas ────────────────────────────────────────────────────────────────────
pagina_visao_geral = st.Page("home.py", title="Visão Geral", default=True)
pagina_evolucao = st.Page("pages/1_Evolução.py", title="Evolução")
pagina_sazonalidade = st.Page("pages/2_Sazonalidade.py", title="Sazonalidade")
pagina_composicao = st.Page("pages/3_Composição.py", title="Composição")
pagina_variacoes = st.Page("pages/4_Variações.py", title="Variações")
pagina_completude = st.Page("pages/5_Completude.py", title="Completude")
pagina_gerenciar = st.Page("pages/6_Gerenciar_Dados.py", title="Gerenciar Dados", icon="🔒")

pg = st.navigation([
    pagina_visao_geral,
    pagina_evolucao,
    pagina_sazonalidade,
    pagina_composicao,
    pagina_variacoes,
    pagina_completude,
    pagina_gerenciar,
])
pg.run()
