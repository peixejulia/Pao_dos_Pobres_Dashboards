"""
utils/tratamento.py — Lógica de ingestão e limpeza dos dados LEM.

Portado do notebook `tratamento_dados_lem.ipynb`, adaptado para:
  • aceitar arquivos em memória (bytes / BytesIO), não só caminhos em disco
    — necessário porque os arquivos agora chegam via upload no navegador
      ou são baixados do GitHub, não vêm mais de uma pasta local fixa.
  • expor uma função orquestradora `reprocessar_tudo()` que recebe o
    conjunto de arquivos atualmente "oficiais" (um por ano+unidade, mais
    o arquivo gerencial) e devolve os 3 DataFrames finais, prontos para
    serem salvos como CSV/parquet.

Nenhuma regra de negócio foi alterada em relação ao notebook original —
mesma tabela de correção de typos, mesma detecção de seções, mesmo
critério de "linha tem dado". Ver o notebook para o histórico/contexto
de cada decisão.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import BinaryIO, Union

import numpy as np
import pandas as pd

ArquivoTipo = Union[bytes, BinaryIO, str]

# ── Tabelas de referência (idênticas ao notebook) ──────────────────────────────

MES_MAP = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4,
    "MAI": 5, "JUN": 6, "JUL": 7, "AGO": 8,
    "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
}

TYPO_CORRECTIONS = {
    r"atendimentos indvidual": "Atendimentos Individual",
    r"atedimento familiar":    "Atendimento Familiar",
    r"saude mental":           "Saúde Mental",
    r"saúde mental":           "Saúde Mental",
    r"saúde clínica":          "Saúde Clínica",
    r"interface com rede socioassistencial": "Interface com Rede Socioassistencial",
    r"interface com judiciário":             "Interface com Judiciário",
    r"interface com saúde":                  "Interface com Saúde",
    r"interface com educação":               "Interface com Educação",
    r"pias / relatórios":                    "PIAS / Relatórios",
    r"visitas domiciliares":                 "Visitas Domiciliares",
    r"apadrinhamento afetivo":               "Apadrinhamento Afetivo",
    r"colocação em família substituta":      "Colocação em Família Substituta",
    r"reunião de equipe.*":                  "Reunião de Equipe",
    r"desligamentos":                        "Desligamentos",
    r"evasão":                               "Evasão",
    r"novos ingressos":                      "Novos Ingressos",
    r"transferências":                       "Transferências",
    r"efetivos na casa":                     "Efetivos na Casa",
    r"documentação civil.*":                 "Documentação Civil",
    r"inseridos em curso profissionalizante": "Inseridos em Curso Profissionalizante",
    r"encaminhados para curso profissionalizante": "Encaminhados para Curso Profissionalizante",
    r"inserido no mercado de trabalho":      "Inserido no Mercado de Trabalho",
    r"encaminhado para mercado de trabalho": "Encaminhado para Mercado de Trabalho",
    r"internações":                          "Internações",
    r"outros.*":                             "Outros (Reforço/Psicopedagoga/Trabalho Educativo)",
}

SECTION_HEADERS = {
    "DESDOBRAMENTOS TÉCNICOS",
    "PROFISSIONALIZAÇÃO",
    "SAÚDE",
    "EDUCAÇÃO",
}

EDU_SUBGROUPS = {
    "ensino infantil", "ensino regular", "ensino eja", "scfv"
}


# ── Erros específicos (pra dar mensagens claras na interface) ─────────────────

class ErroDeFormato(Exception):
    """Levantado quando um arquivo não bate com o formato LEM esperado."""


# ── Funções auxiliares (idênticas ao notebook) ─────────────────────────────────

def normalize_indicator(name: str) -> str:
    if not isinstance(name, str):
        return str(name)
    cleaned = name.strip().lower()
    for pattern, replacement in TYPO_CORRECTIONS.items():
        if re.fullmatch(pattern, cleaned):
            return replacement
    return name.strip().title()


def is_section_header(value) -> bool:
    if not isinstance(value, str):
        return False
    v = value.strip().upper()
    return any(v.startswith(h.upper()) for h in SECTION_HEADERS)


def is_edu_subgroup(value) -> bool:
    if not isinstance(value, str):
        return False
    v = value.strip().lower()
    return any(v.startswith(sg) for sg in EDU_SUBGROUPS)


def safe_numeric(val):
    if isinstance(val, (int, float)):
        return float(val) if not (isinstance(val, float) and np.isnan(val)) else np.nan
    if isinstance(val, str):
        stripped = val.strip()
        if stripped == "":
            return np.nan
        try:
            return float(stripped.replace(",", "."))
        except ValueError:
            return np.nan
    return np.nan


def add_date_column(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["data"] = pd.to_datetime(
        df["ano"].astype(str) + "-" + df["mes_num"].astype(str).str.zfill(2) + "-01"
    )
    return df


# ── Parsers principais (idênticos ao notebook, só trocando Path por arquivo) ──

def parse_lem_file(arquivo: ArquivoTipo, ano: int, unidade: str, nome_exibicao: str = "") -> pd.DataFrame:
    """
    Lê um arquivo LEM padrão (aba "Planilha1") e retorna um DataFrame no
    formato longo: [ano, unidade, mes, mes_num, secao, indicador, valor].

    `arquivo` pode ser um caminho, bytes ou um objeto tipo-arquivo (ex.: o
    retorno de st.file_uploader ou um BytesIO baixado do GitHub).
    """
    nome_exibicao = nome_exibicao or str(arquivo)
    try:
        df_raw = pd.read_excel(arquivo, sheet_name="Planilha1", header=None)
    except ValueError as e:
        raise ErroDeFormato(
            f'Não encontramos a aba "Planilha1" em "{nome_exibicao}". '
            f"Confirme que é a mesma planilha LEM de sempre (erro original: {e})"
        ) from e

    header_row_idx = None
    for i, row in df_raw.iterrows():
        vals = row.dropna().astype(str).tolist()
        if any("JAN" in v.upper() for v in vals):
            header_row_idx = i
            break

    if header_row_idx is None:
        raise ErroDeFormato(
            f'Não encontramos a linha com os meses (JAN, FEV, ...) em "{nome_exibicao}". '
            "Confirme que é a mesma planilha LEM de sempre."
        )

    header_row = df_raw.iloc[header_row_idx]

    month_cols: dict = {}
    for col_idx, val in header_row.items():
        if isinstance(val, str) and val.strip().upper() in MES_MAP:
            month_name = val.strip().upper()
            if month_name not in month_cols.values():
                month_cols[col_idx] = month_name

    if not month_cols:
        raise ErroDeFormato(
            f'Não conseguimos identificar as colunas de mês em "{nome_exibicao}".'
        )

    indicator_col = 0
    records = []
    current_section = "Desdobramentos Técnicos"
    current_edu_subgroup = None

    for i in range(header_row_idx + 1, len(df_raw)):
        row = df_raw.iloc[i]
        cell0 = row.iloc[indicator_col]

        if pd.isna(cell0):
            continue

        cell0_str = str(cell0).strip()
        if not cell0_str or cell0_str in ("0", "0.0"):
            continue

        if is_section_header(cell0_str):
            section_clean = cell0_str.strip().upper()
            if "PROFISSIONALIZAÇÃO" in section_clean:
                current_section = "Profissionalização"
            elif "SAÚDE" in section_clean or "SAUDE" in section_clean:
                current_section = "Saúde"
            elif "EDUCAÇÃO" in section_clean or "EDUCACAO" in section_clean:
                current_section = "Educação"
            elif "DESDOBRAMENTOS" in section_clean:
                current_section = "Desdobramentos Técnicos"
            current_edu_subgroup = None
            continue

        if current_section == "Educação" and is_edu_subgroup(cell0_str):
            sg = cell0_str.strip().lower()
            if "infantil" in sg:
                current_edu_subgroup = "Ensino Infantil"
            elif "regular" in sg:
                current_edu_subgroup = "Ensino Regular"
            elif "eja" in sg:
                current_edu_subgroup = "Ensino EJA"
            elif "scfv" in sg:
                current_edu_subgroup = "SCFV"
            continue

        indicator_raw = re.sub(r"\s+", " ", cell0_str).strip()

        if current_section == "Educação" and current_edu_subgroup:
            indicator_norm = f"{current_edu_subgroup} — {normalize_indicator(indicator_raw)}"
        else:
            indicator_norm = normalize_indicator(indicator_raw)

        has_data = any(
            not np.isnan(safe_numeric(row.iloc[c])) for c in month_cols
        )
        if not has_data:
            continue

        for col_idx, mes_nome in month_cols.items():
            val = safe_numeric(row.iloc[col_idx])
            records.append({
                "ano":       ano,
                "unidade":   unidade,
                "mes":       mes_nome,
                "mes_num":   MES_MAP[mes_nome],
                "secao":     current_section,
                "indicador": indicator_norm,
                "valor":     val,
            })

    return pd.DataFrame(records)


def parse_lem_anual_2025(arquivo: ArquivoTipo, ano: int = 2025, nome_exibicao: str = ""):
    """
    Lê o arquivo "LEM anual completo" (indicadores gerenciais + atividades
    culturais). Retorna (df_gerencial, df_atividades_culturais).

    Aceita um `ano` explícito porque, no futuro, pode existir um arquivo
    equivalente para outros anos além de 2025.
    """
    nome_exibicao = nome_exibicao or str(arquivo)

    # Como vamos ler a mesma origem duas vezes (duas abas), se for um
    # objeto tipo-arquivo precisamos garantir que o cursor volte ao início
    # entre as leituras.
    def _seek_inicio(a):
        if hasattr(a, "seek"):
            a.seek(0)

    _seek_inicio(arquivo)
    try:
        df_raw = pd.read_excel(arquivo, sheet_name="dados de informação gerencial", header=None)
    except ValueError as e:
        raise ErroDeFormato(
            f'Não encontramos a aba "dados de informação gerencial" em "{nome_exibicao}". '
            f"Confirme que é a planilha LEM anual completa (erro original: {e})"
        ) from e

    header_row = df_raw.iloc[3]
    month_cols: dict = {}
    for col_idx, val in header_row.items():
        if isinstance(val, str) and val.strip().upper() in MES_MAP:
            m = val.strip().upper()
            if m not in month_cols.values():
                month_cols[col_idx] = m

    records = []
    for i in range(4, len(df_raw)):
        row = df_raw.iloc[i]
        cell0 = row.iloc[0]
        if pd.isna(cell0) or str(cell0).strip().upper().startswith("OBS"):
            continue
        indicator_raw = re.sub(r"\s+", " ", str(cell0)).strip()
        if not indicator_raw:
            continue
        indicator_norm = normalize_indicator(indicator_raw)

        has_data = any(not np.isnan(safe_numeric(row.iloc[c])) for c in month_cols)
        if not has_data:
            continue

        for col_idx, mes_nome in month_cols.items():
            val = safe_numeric(row.iloc[col_idx])
            records.append({
                "ano":       ano,
                "unidade":   "gerencial",
                "mes":       mes_nome,
                "mes_num":   MES_MAP[mes_nome],
                "secao":     "Dados Gerenciais de Efetividade",
                "indicador": indicator_norm,
                "valor":     val,
            })

    _seek_inicio(arquivo)
    try:
        df_cult = pd.read_excel(arquivo, sheet_name="atividades culturais", header=1)
    except ValueError as e:
        raise ErroDeFormato(
            f'Não encontramos a aba "atividades culturais" em "{nome_exibicao}". '
            f"Confirme que é a planilha LEM anual completa (erro original: {e})"
        ) from e

    df_cult.columns = [str(c).strip().lower() for c in df_cult.columns]

    if "mês" in df_cult.columns and "número de participantes" in df_cult.columns:
        df_cult_clean = df_cult[["mês", "número de participantes"]].copy()
        df_cult_clean = df_cult_clean.dropna(subset=["número de participantes"])
        df_cult_clean["número de participantes"] = df_cult_clean["número de participantes"].apply(safe_numeric)
        df_cult_clean = df_cult_clean.dropna(subset=["número de participantes"])
        df_cult_clean["mês"] = df_cult_clean["mês"].ffill()
    else:
        df_cult_clean = pd.DataFrame(columns=["mês", "número de participantes"])

    return pd.DataFrame(records), df_cult_clean


# ── Orquestração ────────────────────────────────────────────────────────────

@dataclass
class ResultadoReprocessamento:
    df_desdobramentos: pd.DataFrame
    df_gerencial: pd.DataFrame
    df_atividades: pd.DataFrame
    avisos: list = field(default_factory=list)


def reprocessar_tudo(
    arquivos_anuais: dict,
    arquivo_gerencial=None,
    ano_gerencial: int = 2025,
) -> ResultadoReprocessamento:
    """
    Recebe o conjunto ATUAL de arquivos "oficiais" e devolve os 3
    DataFrames finais, já com a coluna `data` e ordenados — exatamente
    como o notebook produzia, mas podendo ser chamado a qualquer momento
    com qualquer combinação de arquivos (não só os 5 originais).

    `arquivos_anuais`: dict {(ano, unidade): arquivo}
    `arquivo_gerencial`: arquivo LEM anual completo, ou None se não houver
    """
    avisos = []
    dfs = []
    for (ano, unidade), arquivo in arquivos_anuais.items():
        try:
            df = parse_lem_file(arquivo, ano, unidade, nome_exibicao=f"{ano}/{unidade}")
            dfs.append(df)
        except ErroDeFormato as e:
            avisos.append(f"Arquivo {ano}/{unidade} ignorado: {e}")

    if dfs:
        df_main = pd.concat(dfs, ignore_index=True)
        df_main = add_date_column(df_main)
        df_main = df_main.sort_values(["unidade", "secao", "indicador", "data"]).reset_index(drop=True)
        df_main["valor"] = pd.to_numeric(df_main["valor"], errors="coerce")
    else:
        df_main = pd.DataFrame(columns=["ano", "unidade", "mes", "mes_num", "secao", "indicador", "valor", "data"])

    if arquivo_gerencial is not None:
        try:
            df_gerencial, df_atividades = parse_lem_anual_2025(arquivo_gerencial, ano=ano_gerencial)
            df_gerencial = add_date_column(df_gerencial)
            df_gerencial = df_gerencial.sort_values(["indicador", "data"]).reset_index(drop=True)
            df_gerencial["valor"] = pd.to_numeric(df_gerencial["valor"], errors="coerce")
        except ErroDeFormato as e:
            avisos.append(f"Arquivo gerencial ignorado: {e}")
            df_gerencial = pd.DataFrame(columns=["ano", "unidade", "mes", "mes_num", "secao", "indicador", "valor", "data"])
            df_atividades = pd.DataFrame(columns=["mês", "número de participantes"])
    else:
        df_gerencial = pd.DataFrame(columns=["ano", "unidade", "mes", "mes_num", "secao", "indicador", "valor", "data"])
        df_atividades = pd.DataFrame(columns=["mês", "número de participantes"])

    return ResultadoReprocessamento(df_main, df_gerencial, df_atividades, avisos)


# ── Serialização para publicação ───────────────────────────────────────────────

def serializar_para_publicacao(resultado: ResultadoReprocessamento) -> dict:
    """
    Converte os 3 DataFrames finais nos bytes exatos que devem ser
    gravados nos arquivos tratados (mesmo formato/encoding do notebook:
    CSV utf-8-sig + Parquet). Retorna um dict {nome_do_arquivo: bytes},
    pronto para ser combinado com o caminho do repositório e publicado.
    """
    import io

    saida = {}

    buf = io.StringIO()
    resultado.df_desdobramentos.to_csv(buf, index=False)
    saida["lem_desdobramentos.csv"] = buf.getvalue().encode("utf-8-sig")

    buf_pq = io.BytesIO()
    resultado.df_desdobramentos.to_parquet(buf_pq, index=False)
    saida["lem_desdobramentos.parquet"] = buf_pq.getvalue()

    buf = io.StringIO()
    resultado.df_gerencial.to_csv(buf, index=False)
    saida["lem_gerencial_2025.csv"] = buf.getvalue().encode("utf-8-sig")

    buf_pq = io.BytesIO()
    resultado.df_gerencial.to_parquet(buf_pq, index=False)
    saida["lem_gerencial_2025.parquet"] = buf_pq.getvalue()

    buf = io.StringIO()
    resultado.df_atividades.to_csv(buf, index=False)
    saida["lem_atividades_culturais_2025.csv"] = buf.getvalue().encode("utf-8-sig")

    return saida
