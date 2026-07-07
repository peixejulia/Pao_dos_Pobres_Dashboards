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

# NOTA: a lista de anos disponíveis NÃO fica mais aqui como constante fixa —
# ela é derivada dinamicamente dos dados via `anos_disponiveis()` em
# utils/data.py, para que anos novos (ex.: 2026) adicionados pela página
# "Gerenciar Dados" apareçam automaticamente nos filtros, sem editar código.

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


def paleta_azuis(n: int) -> list:
    """
    Gera `n` tons de azul (mesmo matiz do azul institucional), do mais claro
    ao mais escuro — pensada para dados sequenciais/ordenados (como anos),
    onde um degradê de uma única cor comunica melhor a progressão no tempo
    do que uma paleta qualitativa multicolor (usada, por ex., nos anos do
    Gráfico de Rosa da página Sazonalidade).
    """
    matiz = 197 / 360  # mesmo matiz do azul petróleo institucional (CORES_SECAO)
    saturacao = 0.60
    if n <= 1:
        return ["#257C9D"]
    cores = []
    for i in range(n):
        t = i / (n - 1)
        luminosidade = 0.78 - t * 0.50  # do claro (0.78) ao escuro (0.28)
        r, g, b = colorsys.hls_to_rgb(matiz, luminosidade, saturacao)
        cores.append("#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255)))
    return cores


# ── Categorias dos indicadores de Efetividade Gerencial (LEM Gerencial 2025) ──
# Os 13 indicadores do arquivo gerencial são heterogêneos — para facilitar a
# leitura, foram agrupados em 3 categorias temáticas (usadas na página
# "Efetividade Gerencial" para colorir gráficos e organizar os KPIs).
CATEGORIAS_GERENCIAL = {
    "Atendimento e Permanência": [
        "Número De Crianças E Adolescentes Atendidos",
        "Crianças E Adolescentes Em Ensino Regular Matriculados",
        "Crianças E Adolescentes/Desligamentos",
        "Crianças E Adolescentes/Evasões",
    ],
    "Inserção e Efetividade": [
        "Adolescentes Inseridos Em Cursos Profissionalizantes",
        "Adolescentes Inseridos No Mercado De Trabalho",
        "Apadrinhamentos Afetivos Efetivados",
    ],
    "Equipe e Atividades": [
        "Atividades Lúdicas/Recreativas/Culturais",
        "Capacitações Coordenações",
        "Capacitações Equipes",
        "PIAS / Relatórios",
        "Reuniões De Equipe",
        "Visitas Domiciliares",
    ],
}

# Mesmas cores usadas em CORES_SECAO, reaproveitadas aqui para manter a
# identidade visual — mas representam uma dimensão diferente (categoria de
# efetividade gerencial, não seção temática do LEM principal).
CORES_CATEGORIA_GERENCIAL = {
    "Atendimento e Permanência": "#257C9D",  # azul petróleo institucional
    "Inserção e Efetividade": "#6B8D49",     # oliva
    "Equipe e Atividades": "#DE9B35",        # mostarda
}

# Classificação de cada indicador como "nível" (retrato/foto do mês — ex.:
# quantas crianças estão atualmente atendidas) ou "evento" (contagem de
# ocorrências no mês — ex.: quantos desligamentos aconteceram). Essa
# distinção importa porque somar um indicador de "nível" ao longo dos meses
# não faz sentido (dá um número sem significado real), enquanto somar um
# indicador de "evento" é uma métrica válida (total de ocorrências no ano).
TIPO_INDICADOR_GERENCIAL = {
    "Número De Crianças E Adolescentes Atendidos": "nivel",
    "Crianças E Adolescentes Em Ensino Regular Matriculados": "nivel",
    "Adolescentes Inseridos Em Cursos Profissionalizantes": "nivel",
    "Adolescentes Inseridos No Mercado De Trabalho": "nivel",
    "Apadrinhamentos Afetivos Efetivados": "nivel",
    "Crianças E Adolescentes/Desligamentos": "evento",
    "Crianças E Adolescentes/Evasões": "evento",
    "Atividades Lúdicas/Recreativas/Culturais": "evento",
    "Capacitações Coordenações": "evento",
    "Capacitações Equipes": "evento",
    "PIAS / Relatórios": "evento",
    "Reuniões De Equipe": "evento",
    "Visitas Domiciliares": "evento",
}


def categoria_do_indicador_gerencial(indicador: str) -> str:
    """Devolve a categoria (Atendimento/Inserção/Equipe) de um indicador
    gerencial, ou "Outros" se não estiver mapeado (ex.: indicador novo
    adicionado no futuro)."""
    for categoria, indicadores in CATEGORIAS_GERENCIAL.items():
        if indicador in indicadores:
            return categoria
    return "Outros"
