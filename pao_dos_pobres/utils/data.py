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


_NOMES_MES_EXTENSO = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def nome_mes(mes_num: int) -> str:
    """Nome do mês por extenso (1 -> 'janeiro', ..., 12 -> 'dezembro')."""
    return _NOMES_MES_EXTENSO[int(mes_num) - 1]


def periodo_gerencial(df: pd.DataFrame) -> dict:
    """
    Deriva DINAMICAMENTE do próprio DataFrame quais anos e quais meses estão
    de fato preenchidos no conjunto gerencial — em vez de textos com "2025"
    e "jan-nov" fixos no código. Assim, se a planilha for atualizada no
    futuro (ex.: dezembro preenchido, ou um novo ano adicionado), os textos
    da página "Efetividade Gerencial" acompanham automaticamente, sem virar
    um alerta desatualizado/falso.

    Retorna um dict com:
      ano_label       — "2025" ou "2025–2026" se houver mais de um ano
      periodo_label   — "janeiro a novembro" (intervalo de meses com dado)
      faltantes_label — "dezembro" (meses finais do último ano ainda sem
                         dado) ou "" se não houver lacuna no final
      n_indicadores   — nº de indicadores distintos no DataFrame
    """
    anos = sorted(int(a) for a in df["ano"].dropna().unique())
    if not anos:
        ano_label = "—"
    elif len(anos) == 1:
        ano_label = str(anos[0])
    else:
        ano_label = f"{min(anos)}–{max(anos)}"

    d = df.dropna(subset=["valor"])
    meses_com_dado = sorted(int(m) for m in d["mes_num"].dropna().unique())

    if meses_com_dado:
        primeiro, ultimo = meses_com_dado[0], meses_com_dado[-1]
        if primeiro == ultimo:
            periodo_label = _NOMES_MES_EXTENSO[primeiro - 1]
        else:
            periodo_label = f"{_NOMES_MES_EXTENSO[primeiro - 1]} a {_NOMES_MES_EXTENSO[ultimo - 1]}"
        meses_faltantes_finais = [m for m in range(ultimo + 1, 13) if m not in meses_com_dado]
        faltantes_label = ", ".join(_NOMES_MES_EXTENSO[m - 1] for m in meses_faltantes_finais)
    else:
        periodo_label = "nenhum mês"
        faltantes_label = ""

    return {
        "ano_label": ano_label,
        "periodo_label": periodo_label,
        "faltantes_label": faltantes_label,
        "n_indicadores": int(df["indicador"].nunique()),
    }
