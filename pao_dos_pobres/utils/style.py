"""
Constantes de estilo compartilhadas entre todas as páginas.
Importar com: from utils.style import CORES_SECAO, ORDEM_MES
"""

# Paleta de cores por seção temática (usada em todos os gráficos)
CORES_SECAO = {
    "Desdobramentos Técnicos": "#2E86AB",
    "Educação":                "#A23B72",
    "Profissionalização":      "#F18F01",
    "Saúde":                   "#C73E1D",
}

# Ordem canônica dos meses (para eixos e reindexação)
ORDEM_MES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
             "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

# Anos disponíveis na base
ANOS = [2021, 2022, 2023, 2024, 2025]

# Tema padrão dos gráficos Plotly
PLOTLY_TEMPLATE = "plotly_white"

import base64
from pathlib import Path
import streamlit as st

_LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo.png"


@st.cache_data
def _logo_base64() -> str:
    """Lê o logo da Fundação e devolve como string base64 (cacheado)."""
    if not _LOGO_PATH.exists():
        return ""
    return base64.b64encode(_LOGO_PATH.read_bytes()).decode()


def titulo_com_logo(texto: str, nivel: int = 1) -> None:
    """
    Renderiza um título de página com o logo da Fundação Pão dos Pobres ao
    lado, no lugar de um emoji. Se o arquivo do logo não for encontrado, cai
    de volta para um título simples sem emoji.
    """
    b64 = _logo_base64()
    tag = f"h{nivel}"
    if not b64:
        st.markdown(f"<{tag}>{texto}</{tag}>", unsafe_allow_html=True)
        return
    st.markdown(
        f'<div style="display:flex; align-items:center; gap:0.6rem; margin-bottom:0.2rem;">'
        f'<img src="data:image/png;base64,{b64}" style="height:2.1rem; width:auto;">'
        f'<{tag} style="margin:0; padding:0;">{texto}</{tag}>'
        f'</div>',
        unsafe_allow_html=True,
    )


def explicacao_grafico(texto: str) -> None:
    """
    Renderiza o texto "📌 O que este gráfico mostra" de forma discreta —
    fonte menor e cinza (via st.caption), pra não competir visualmente com
    o gráfico em si, mas continuar sempre visível (sem exigir clique).
    """
    st.caption(texto)
