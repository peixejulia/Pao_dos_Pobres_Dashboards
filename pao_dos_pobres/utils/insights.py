"""
Geração de resumos em texto simples (linguagem natural, sem jargão) a partir
dos DataFrames já filtrados de cada página. O objetivo é traduzir cada
gráfico em 2-4 frases que qualquer pessoa consiga entender, mesmo sem
experiência com análise de dados.

Convenção: toda função recebe dados já filtrados e devolve uma lista de
strings (cada string = uma frase/observação). Quem chama decide como exibir
(st.info, st.markdown etc.). Se não houver dados suficientes, devolve uma
lista com uma única frase neutra — nunca lança exceção.
"""
from __future__ import annotations
import pandas as pd

from utils.data import periodo_gerencial


def _fmt(n) -> str:
    """Formata número no padrão brasileiro (milhar com ponto, sem decimais)."""
    try:
        return f"{int(round(n)):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(n) -> str:
    try:
        return f"{n:.0f}%"
    except (TypeError, ValueError):
        return "—"


# ── Página inicial (Visão Geral) ───────────────────────────────────────────────
def resumo_geral(df_filtrado: pd.DataFrame) -> list[str]:
    if df_filtrado.empty:
        return ["Não há dados para os filtros selecionados."]

    frases = []

    por_ano = df_filtrado.groupby("ano")["valor"].sum()
    if len(por_ano) >= 2:
        primeiro, ultimo = por_ano.index.min(), por_ano.index.max()
        v_primeiro, v_ultimo = por_ano.loc[primeiro], por_ano.loc[ultimo]
        if v_primeiro > 0:
            variacao = (v_ultimo - v_primeiro) / v_primeiro * 100
            direcao = "aumentou" if variacao >= 0 else "caiu"
            frases.append(
                f"O volume total de registros {direcao} {abs(variacao):.0f}% entre "
                f"{primeiro} ({_fmt(v_primeiro)}) e {ultimo} ({_fmt(v_ultimo)})."
            )

    por_secao = df_filtrado.groupby("secao")["valor"].sum().sort_values(ascending=False)
    if not por_secao.empty:
        top_secao = por_secao.index[0]
        pct = por_secao.iloc[0] / por_secao.sum() * 100 if por_secao.sum() > 0 else 0
        frases.append(
            f"A seção **{top_secao}** concentra a maior parte dos registros "
            f"({_fmt_pct(pct)} do total)."
        )

    if not frases:
        frases.append("Ainda não há dados suficientes para gerar um resumo.")
    return frases


# ── Página 1 — Evolução ────────────────────────────────────────────────────────
def resumo_evolucao(df_f: pd.DataFrame) -> list[str]:
    if df_f.empty:
        return ["Não há dados para os filtros selecionados."]

    frases = []
    por_ano_secao = df_f.groupby(["secao", "ano"])["valor"].sum().reset_index()
    crescimentos = []
    for secao, grupo in por_ano_secao.groupby("secao"):
        grupo = grupo.sort_values("ano")
        if len(grupo) >= 2 and grupo["valor"].iloc[0] > 0:
            var = (grupo["valor"].iloc[-1] - grupo["valor"].iloc[0]) / grupo["valor"].iloc[0] * 100
            crescimentos.append((secao, var))

    if crescimentos:
        secao_top, var_top = max(crescimentos, key=lambda x: x[1])
        direcao = "cresceu" if var_top >= 0 else "caiu"
        frases.append(
            f"A seção que mais **{direcao}** ao longo do período foi "
            f"**{secao_top}** ({var_top:+.0f}%)."
        )

    if not frases:
        frases.append("Ainda não há dados suficientes para comparar a evolução entre seções.")
    return frases


# ── Página 2 — Sazonalidade ─────────────────────────────────────────────────────
def resumo_sazonalidade(df_mes: pd.DataFrame) -> list[str]:
    """df_mes precisa ter colunas 'mes' e 'Volume' (uma linha por mês)."""
    if df_mes.empty or df_mes["Volume"].sum() == 0:
        return ["Não há dados para os filtros selecionados."]

    frases = []
    media = df_mes["Volume"].mean()
    idx_max = df_mes["Volume"].idxmax()
    idx_min = df_mes["Volume"].idxmin()
    mes_max, vol_max = df_mes.loc[idx_max, "mes"], df_mes.loc[idx_max, "Volume"]
    mes_min, vol_min = df_mes.loc[idx_min, "mes"], df_mes.loc[idx_min, "Volume"]

    if media > 0:
        pct_acima = (vol_max - media) / media * 100
        frases.append(
            f"**{mes_max}** é o mês com mais registros ({_fmt(vol_max)}), "
            f"{pct_acima:.0f}% acima da média mensal."
        )
    frases.append(
        f"**{mes_min}** é o mês com menos registros ({_fmt(vol_min)})."
    )
    return frases


# ── Página 3 — Composição ───────────────────────────────────────────────────────
def resumo_composicao(df_agg: pd.DataFrame) -> list[str]:
    """df_agg precisa ter colunas 'secao', 'indicador' e 'Volume'."""
    if df_agg.empty:
        return ["Não há dados para os filtros selecionados."]

    frases = []
    total = df_agg["Volume"].sum()

    top_ind = df_agg.sort_values("Volume", ascending=False).iloc[0]
    if total > 0:
        pct_ind = top_ind["Volume"] / total * 100
        frases.append(
            f"O indicador com mais registros é **{top_ind['indicador']}** "
            f"({_fmt(top_ind['Volume'])}, {pct_ind:.0f}% do total geral)."
        )

    por_secao = df_agg.groupby("secao")["Volume"].sum().sort_values(ascending=False)
    if len(por_secao) >= 2:
        frases.append(
            f"Entre as seções, **{por_secao.index[0]}** lidera, seguida de "
            f"**{por_secao.index[1]}**."
        )
    return frases


# ── Página 4 — Variações ────────────────────────────────────────────────────────
def resumo_variacoes(df_db: pd.DataFrame, ano_a: int, ano_b: int) -> list[str]:
    """df_db precisa ter colunas 'indicador', 'vol_a', 'vol_b', 'variacao'."""
    if df_db.empty:
        return ["Não há dados suficientes para comparar os dois anos selecionados."]

    frases = []
    maior_alta = df_db.loc[df_db["variacao"].idxmax()]
    maior_queda = df_db.loc[df_db["variacao"].idxmin()]

    if maior_alta["variacao"] > 0:
        frases.append(
            f"Quem mais **cresceu** de {ano_a} para {ano_b} foi "
            f"**{maior_alta['indicador']}** (+{_fmt(maior_alta['variacao'])})."
        )
    if maior_queda["variacao"] < 0:
        frases.append(
            f"Quem mais **caiu** foi **{maior_queda['indicador']}** "
            f"({_fmt(maior_queda['variacao'])})."
        )
    if not frases:
        frases.append(f"Os indicadores se mantiveram estáveis entre {ano_a} e {ano_b}.")
    return frases


# ── Página 5 — Completude ───────────────────────────────────────────────────────
def resumo_completude(pivot_comp: pd.DataFrame) -> list[str]:
    """pivot_comp: índice = indicador, colunas = ano, valores = % completude (0-100)."""
    if pivot_comp.empty:
        return ["Não há dados para os filtros selecionados."]

    frases = []
    media_geral = pivot_comp.mean(numeric_only=True).mean()
    frases.append(f"Em média, **{_fmt_pct(media_geral)}** dos meses estão preenchidos nos indicadores selecionados.")

    media_por_indicador = pivot_comp.mean(axis=1, numeric_only=True).sort_values()
    if not media_por_indicador.empty and media_por_indicador.iloc[0] < 90:
        pior = media_por_indicador.index[0]
        frases.append(
            f"O indicador com mais lacunas é **{pior}**, com apenas "
            f"{_fmt_pct(media_por_indicador.iloc[0])} de completude média."
        )
    else:
        frases.append("Nenhum indicador apresenta lacunas relevantes — os dados estão bem completos.")
    return frases


# ── Página 7 — Efetividade Gerencial ────────────────────────────────────────────
def resumo_efetividade(df: pd.DataFrame) -> list[str]:
    """df: lem_gerencial já filtrado, colunas indicador, mes_num, valor."""
    if df.empty:
        return ["Não há dados para os filtros selecionados."]

    frases = []
    d = df.dropna(subset=["valor"])
    if d.empty:
        return ["Não há dados para os filtros selecionados."]

    info = periodo_gerencial(df)
    periodo_texto = info["periodo_label"]
    if info["faltantes_label"]:
        periodo_texto += f" — {info['faltantes_label']} ainda não preenchido(s)"

    alvo = "Número De Crianças E Adolescentes Atendidos"
    serie = d[d["indicador"] == alvo].sort_values("mes_num")
    if not serie.empty:
        frases.append(
            f"Em {info['ano_label']} ({periodo_texto}), a Fundação atendeu em média "
            f"**{serie['valor'].mean():.0f} crianças e adolescentes por mês**."
        )

    mercado = d[d["indicador"] == "Adolescentes Inseridos No Mercado De Trabalho"]
    if not mercado.empty and mercado["valor"].sum() == 0:
        frases.append(
            "Nenhum adolescente foi inserido no **mercado de trabalho** em todo o "
            "período registrado — um ponto de atenção para a Fundação."
        )

    cursos = (
        d[d["indicador"] == "Adolescentes Inseridos Em Cursos Profissionalizantes"]
        .sort_values("mes_num")
    )
    if len(cursos) >= 2:
        pico = cursos["valor"].max()
        ultimo = cursos["valor"].iloc[-1]
        if ultimo < pico:
            frases.append(
                f"As inserções em **cursos profissionalizantes** caíram de um pico de "
                f"{pico:.0f} para {ultimo:.0f} no último mês registrado."
            )

    if not frases:
        frases.append("Ainda não há dados suficientes para gerar um resumo.")
    return frases
