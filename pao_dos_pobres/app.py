"""
app.py — Roteador principal do dashboard Pão dos Pobres.

Define os nomes exibidos na navegação lateral do Streamlit via
st.navigation()/st.Page(), independente do nome dos arquivos.

Para rodar:  streamlit run app.py
"""
from pathlib import Path

import streamlit as st
from PIL import Image

# ── Configuração da página (única para todo o app) ────────────────────────────
# page_icon: logo da Fundação (em vez de emoji) — aparece na aba do navegador.
# Usamos um objeto PIL (não o caminho em texto) porque o caminho relativo se
# comporta de forma inconsistente dependendo de onde o Streamlit é iniciado;
# abrir o arquivo diretamente evita essa ambiguidade.
_LOGO_ICONE = Image.open(Path(__file__).parent / "assets" / "logo.png")

st.set_page_config(
    page_title="Pão dos Pobres — Dashboard LEM",
    page_icon=_LOGO_ICONE,
    layout="wide",
)

# ── Páginas ────────────────────────────────────────────────────────────────────
pagina_visao_geral = st.Page("home.py", title="Visão Geral", default=True)
pagina_evolucao = st.Page("pages/1_Evolução.py", title="Evolução")
pagina_sazonalidade = st.Page("pages/2_Sazonalidade.py", title="Sazonalidade")
pagina_composicao = st.Page("pages/3_Composição.py", title="Composição")
pagina_variacoes = st.Page("pages/4_Variações.py", title="Variações")
pagina_completude = st.Page("pages/5_Completude.py", title="Completude")
pagina_efetividade = st.Page("pages/7_Efetividade_Gerencial.py", title="Efetividade Gerencial")
pagina_gerenciar = st.Page("pages/6_Gerenciar_Dados.py", title="Gerenciar Dados", icon="🔒")

pg = st.navigation([
    pagina_visao_geral,
    pagina_evolucao,
    pagina_sazonalidade,
    pagina_composicao,
    pagina_variacoes,
    pagina_completude,
    pagina_efetividade,
    pagina_gerenciar,
])
pg.run()
