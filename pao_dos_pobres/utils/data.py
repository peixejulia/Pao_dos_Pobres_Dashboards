"""
Carregamento e cache dos dados LEM.
Todos os DataFrames são carregados uma única vez (@st.cache_data) e
reutilizados em todas as páginas sem releitura.
"""
import pandas as pd
import streamlit as st
from pathlib import Path

# Caminho para a pasta de dados (relativo a este arquivo)
DATA_DIR = Path(__file__).parent.parent / "dados"


@st.cache_data
def carregar_desdobramentos() -> pd.DataFrame:
    """
    Retorna o DataFrame principal com todos os indicadores LEM (2021–2025).
    Colunas: ano, mes, mes_num, secao, indicador, valor, data

    NOTA: até jul/2026 havia também uma coluna `unidade` (sempre
    "unidade_1" — conceito removido do painel). Ela pode ainda aparecer
    nos arquivos CSV publicados antes dessa mudança; se aparecer, é
    inofensiva e nenhuma página do painel a utiliza.
    """
    df = pd.read_csv(
        DATA_DIR / "lem_desdobramentos.csv",
        parse_dates=["data"],
        encoding="utf-8-sig",
    )
    return df


@st.cache_data
def anos_disponiveis() -> list:
    """
    Lista de anos presentes na base tratada, em ordem crescente — derivada
    dinamicamente dos dados (não hardcoded). Assim, se um novo ano (ex.: 2026)
    for adicionado via a página "Gerenciar Dados", ele aparece automaticamente
    nos filtros e nos textos do painel, sem precisar editar código.
    """
    df = carregar_desdobramentos()
    return sorted(int(a) for a in df["ano"].dropna().unique())


@st.cache_data
def carregar_gerencial() -> pd.DataFrame:
    """
    Retorna os indicadores de efetividade gerencial (2025).
    Mesma estrutura de colunas do DataFrame principal.
    """
    df = pd.read_csv(
        DATA_DIR / "lem_gerencial_2025.csv",
        parse_dates=["data"],
        encoding="utf-8-sig",
    )
    return df


@st.cache_data
def carregar_atividades() -> pd.DataFrame:
    """
    Retorna o registro de atividades culturais (2025).
    Colunas: mês, número de participantes (e outras colunas descritivas).
    """
    df = pd.read_csv(
        DATA_DIR / "lem_atividades_culturais_2025.csv",
        encoding="utf-8-sig",
    )
    return df
