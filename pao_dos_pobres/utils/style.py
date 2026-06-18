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
