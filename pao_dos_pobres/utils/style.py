"""
Constantes de estilo compartilhadas entre todas as páginas.
Importar com: from utils.style import CORES_SECAO, ORDEM_MES
"""

# Paleta de cores por seção temática (usada em todos os gráficos) — alinhada
# com a paleta harmônica institucional definida em _CORES_HARMONICAS abaixo,
# pensada para combinar com o azul do logo sem ser tudo em tons de azul.
CORES_SECAO = {
    "Desdobramentos Técnicos": "#257C9D",  # azul petróleo (institucional)
    "Educação":                "#6B8D49",  # oliva
    "Profissionalização":      "#DE9B35",  # mostarda
    "Saúde":                   "#BA3B3B",  # vinho/marsala
}

# Ordem canônica dos meses (para eixos e reindexação)
ORDEM_MES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
             "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

# Anos disponíveis na base
ANOS = [2021, 2022, 2023, 2024, 2025]

# Tema padrão dos gráficos Plotly
PLOTLY_TEMPLATE = "plotly_white"

import base64
import colorsys
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


# Paleta harmônica institucional — âncora no azul da Fundação (mesma família
# do CORES_SECAO acima) somada a tons terrosos/complementares (terracota,
# dourado, sálvia, rosa-velho etc.), inspirada em referências de paletas
# "editoriais" que combinam azuis petróleo/marinho com neutros quentes.
# Importante: NÃO é uma paleta monocromática de azul — é pensada para ficar
# visualmente agradável AO LADO do azul do logo, com bastante variedade.
_CORES_HARMONICAS = [
    "#257C9D",  # azul petróleo (institucional)
    "#BA3B3B",  # vinho/marsala
    "#DE9B35",  # mostarda
    "#6B8D49",  # oliva
    "#6FAE8F",  # sálvia
    "#50667C",  # slate azul-acinzentado
    "#CF8B77",  # rosa-velho / terracota
    "#1A3861",  # azul-marinho escuro
    "#CD8484",  # vinho claro (tom mais claro do vinho/marsala acima)
    "#E1C498",  # dourado claro (tom mais claro da mostarda acima)
    "#AAC28E",  # oliva claro (tom mais claro do oliva acima)
]


def _ajustar_luminosidade(hex_cor: str, delta: float) -> str:
    """Clareia (delta > 0) ou escurece (delta < 0) uma cor hex, mantendo o matiz."""
    hex_cor = hex_cor.lstrip("#")
    r, g, b = (int(hex_cor[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = min(0.88, max(0.12, l + delta))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


def paleta_institucional(n: int) -> list:
    """
    Gera `n` cores a partir da paleta harmônica institucional (_CORES_HARMONICAS)
    — usada em gráficos com muitos indicadores diferentes (ex.: Bump Chart, o
    "Ver por indicador" da página Variações), no lugar de paletas nativas do
    Plotly (Alphabet, Dark24 etc.) que costumam ficar berrantes e cansativas.

    Para n <= len(_CORES_HARMONICAS) (tamanho da paleta base), usa as cores na
    ordem definida. Para n maior, reaproveita as mesmas cores em versões mais
    claras/escuras, em vez de inventar tons novos desconectados da identidade
    visual.
    """
    total_base = len(_CORES_HARMONICAS)
    cores = []
    for i in range(n):
        base = _CORES_HARMONICAS[i % total_base]
        volta = i // total_base
        if volta == 0:
            cores.append(base)
        else:
            passo = 0.14 * ((volta + 1) // 2)
            delta = passo if volta % 2 else -passo
            cores.append(_ajustar_luminosidade(base, delta))
    return cores
