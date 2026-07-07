"""
Página 6 — Gerenciar Dados (área restrita)

Permite à equipe da Fundação:
  • Ver quais planilhas LEM estão hoje alimentando o painel
  • Adicionar uma planilha nova (por ano) ou substituir uma existente
  • Excluir uma planilha (o painel recalcula tudo sem ela)
  • Adicionar ou substituir o arquivo gerencial anual (alimenta a página
    "Efetividade Gerencial")

Cada mudança reprocessa os dados relevantes e publica o resultado num único
commit no GitHub — o mesmo repositório que alimenta o site público no
Streamlit Cloud, que se atualiza sozinho a partir disso.

NOTA: esta página não pede mais uma "Unidade" para cada planilha — cada
ano tem no máximo UMA planilha oficial. O campo existia para o caso de a
Fundação reportar por casa/unidade separadamente, mas isso nunca foi
confirmado com a instituição e, na prática, só criava risco: bastava
digitar um nome de unidade diferente por engano para o painel passar a
tratar aquilo como um arquivo "novo" em vez de substituir o existente,
gerando dados fragmentados ou duplicados. Se no futuro a Fundação passar
a reportar por unidade de fato, vale reintroduzir o campo com uma lista
fixa (não texto livre) para evitar esse risco.

NOTA IMPORTANTE sobre o arquivo gerencial (reintroduzido em 07/07/2026):
esta seção publica APENAS os 3 arquivos tratados gerenciais
(lem_gerencial_2025.csv/.parquet, lem_atividades_culturais_2025.csv) — ela
NUNCA mexe em lem_desdobramentos.csv/.parquet, e a seção de planilhas
anuais acima NUNCA mexe nos arquivos gerenciais. Isso é proposital: as
duas fontes de dados são processadas e publicadas de forma independente,
para que editar uma nunca apague ou reprocesse a outra sem necessidade
(foi exatamente esse acoplamento que causou o incidente de 07/07/2026 em
que qualquer publicação de planilha anual zerava os dados gerenciais —
ver memória do projeto para o histórico completo).
"""
import io
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from utils.style import titulo_com_logo
from utils.tratamento import (
    reprocessar_tudo,
    serializar_para_publicacao,
    parse_lem_file,
    parse_lem_anual_2025,
    add_date_column,
    ResultadoReprocessamento,
    ErroDeFormato,
)
from utils.github_sync import (
    listar_arquivos_brutos,
    baixar_arquivo,
    publicar_mudancas,
    testar_conexao,
    path_anual,
    path_gerencial,
    PASTA_DADOS_TRATADOS,
    ErroGitHub,
)

# Mesmo ícone (logo da Fundação) do resto do painel, definido em app.py —
# repetido aqui porque esta página também chama set_page_config() por conta
# própria (para ajustar o título da aba especificamente desta página).
_LOGO_ICONE = Image.open(Path(__file__).parent.parent / "assets" / "logo.png")
st.set_page_config(page_title="Gerenciar Dados · LEM", page_icon=_LOGO_ICONE, layout="wide")

titulo_com_logo("Gerenciar Dados")
st.markdown(
    "Área restrita para adicionar, substituir ou remover as planilhas LEM "
    "que alimentam o painel. Qualquer mudança aqui atualiza o site público "
    "automaticamente em cerca de 1 minuto."
)

st.markdown("**ℹ️ Como usar esta página** (clique em cada tópico abaixo para expandir)")

with st.expander("📅 Passo a passo — Adicionar ou substituir uma planilha anual"):
    st.markdown(
        "1. Em **Ano**, escolha o ano da planilha (ex.: 2026).\n"
        "2. Clique em **Upload** e escolha o arquivo Excel (.xlsx) no seu computador.\n"
        "3. Confira a mensagem de prévia (\"Planilha lida com sucesso: X registros "
        "encontrados\"). Se aparecer um erro em vermelho, pare e peça ajuda antes "
        "de continuar.\n"
        "4. Clique em **\"✅ Confirmar e publicar\"** e aguarde a mensagem de "
        "sucesso — o site público reinicia sozinho em seguida (leva uns 30 a "
        "60 segundos).\n"
        "5. Se já existia uma planilha para o mesmo ano, ela é "
        "**substituída automaticamente** pela nova — não duplica dados.\n\n"
        "**Dica:** faça um arquivo de cada vez e espere a publicação terminar "
        "antes de subir o próximo."
    )

with st.expander("🗑️ Passo a passo — Excluir uma planilha"):
    st.markdown(
        "1. Encontre a planilha na lista em **\"Planilhas atualmente no "
        "painel\"**.\n"
        "2. Clique em **\"🗑️ Excluir\"** ao lado dela.\n"
        "3. Confirme clicando em **\"Sim, excluir\"**. O painel público é "
        "recalculado sem os dados daquele ano."
    )

with st.expander("📊 Passo a passo — Adicionar ou substituir o arquivo gerencial"):
    st.markdown(
        "1. Este é um arquivo **diferente** das planilhas anuais acima — a "
        "planilha \"LEM anual completo\", com os indicadores de "
        "efetividade social e as atividades culturais. Ela alimenta só a "
        "página **\"Efetividade Gerencial\"** do painel.\n"
        "2. Em **Ano**, escolha o ano de referência do arquivo (ex.: 2025).\n"
        "3. Clique em **Upload** e escolha o arquivo Excel (.xlsx).\n"
        "4. Confira a mensagem de prévia. Se aparecer um erro em vermelho, "
        "pare e peça ajuda antes de continuar.\n"
        "5. Clique em **\"✅ Confirmar e publicar arquivo gerencial\"** e "
        "aguarde a mensagem de sucesso.\n\n"
        "**Importante:** publicar este arquivo não afeta as planilhas "
        "anuais das outras seções desta página, e vice-versa — são dados "
        "independentes."
    )

st.divider()

# ── Portão de senha ─────────────────────────────────────────────────────────
if "gerenciar_autorizado" not in st.session_state:
    st.session_state["gerenciar_autorizado"] = False

if not st.session_state["gerenciar_autorizado"]:
    try:
        senha_configurada = st.secrets.get("senha_gerenciar_dados")
    except Exception:
        senha_configurada = None  # nenhum secrets.toml configurado ainda
    if not senha_configurada:
        st.error(
            "⚠️ Esta página ainda não foi configurada. Falta definir "
            '`senha_gerenciar_dados` nos "Secrets" do Streamlit.'
        )
        st.stop()

    senha_digitada = st.text_input("Senha de acesso", type="password")
    if st.button("Entrar"):
        if senha_digitada == senha_configurada:
            st.session_state["gerenciar_autorizado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()

# ── Diagnóstico de conexão com o GitHub ──────────────────────────────────────
with st.expander("🔧 Diagnóstico da conexão com o GitHub"):
    if st.button("Testar conexão"):
        ok, mensagem = testar_conexao()
        (st.success if ok else st.error)(mensagem)

# ── Carregar lista atual de arquivos ──────────────────────────────────────────
try:
    arquivos = listar_arquivos_brutos()
except ErroGitHub as e:
    st.error(f"Não foi possível carregar a lista de arquivos: {e}")
    st.stop()

# Um arquivo anual por ano (no máximo). Se por algum motivo existir mais de
# um arquivo para o mesmo ano (ex.: sobra do formato antigo com "unidade"),
# fica o último encontrado — a próxima publicação já limpa a duplicata.
arquivos_anuais_existentes = {
    a["metadata"]["ano"]: a
    for a in arquivos
    if a["metadata"] and a["metadata"]["tipo"] == "anual"
}

# Mesma lógica para o arquivo gerencial — hoje só existe um ano em uso
# (2025), mas a estrutura já suporta mais de um se a Fundação passar a
# mandar esse arquivo em anos futuros também.
arquivos_gerenciais_existentes = {
    a["metadata"]["ano"]: a
    for a in arquivos
    if a["metadata"] and a["metadata"]["tipo"] == "gerencial"
}


def _publicar(estado_final_anos: dict, mensagem_commit: str):
    """
    Reprocessa tudo a partir do conjunto final de arquivos anuais (já com a
    mudança aplicada) e publica num único commit.

    `estado_final_anos`: dict {ano: bytes_ou_None} — o estado final
    desejado para cada ano (None = não deve mais existir planilha anual
    daquele ano). Se um ano já tinha um arquivo publicado com o nome
    antigo (formato com "unidade"), esse arquivo antigo é removido e o
    conteúdo novo é gravado só no caminho atual (um arquivo por ano) —
    evita duplicar o mesmo ano sob dois nomes diferentes no repositório.
    """
    with st.spinner("Reprocessando dados e publicando no GitHub — isso pode levar até 1 minuto..."):
        arquivos_para_reprocessar = {
            ano: conteudo
            for ano, conteudo in estado_final_anos.items()
            if conteudo is not None
        }
        resultado = reprocessar_tudo(arquivos_para_reprocessar)

        mudancas = {}
        for ano, conteudo in estado_final_anos.items():
            caminho_atual = arquivos_anuais_existentes.get(ano, {}).get("path")
            caminho_novo = path_anual(ano)
            if conteudo is None:
                if caminho_atual:
                    mudancas[caminho_atual] = None
            else:
                if caminho_atual and caminho_atual != caminho_novo:
                    mudancas[caminho_atual] = None
                mudancas[caminho_novo] = conteudo

        saida = serializar_para_publicacao(resultado)
        # Esta seção só gerencia planilhas anuais (desdobramentos) — o
        # arquivo gerencial tem sua própria seção/função de publicação
        # (_publicar_gerencial) mais abaixo, e nunca deve ser tocado aqui.
        # reprocessar_tudo() acima roda com arquivo_gerencial=None, o que
        # produziria DataFrames VAZIOS para lem_gerencial_2025 e
        # lem_atividades_culturais_2025 — publicar esses arquivos aqui
        # apagaria silenciosamente os dados reais já publicados (foi
        # exatamente o que aconteceu num incidente em 07/07/2026). Por
        # isso só os arquivos de desdobramentos entram nesta publicação.
        for nome_arquivo in ("lem_desdobramentos.csv", "lem_desdobramentos.parquet"):
            mudancas[f"{PASTA_DADOS_TRATADOS}/{nome_arquivo}"] = saida[nome_arquivo]

        try:
            publicar_mudancas(mudancas, mensagem_commit)
        except ErroGitHub as e:
            st.error(f"Não foi possível publicar: {e}")
            return

    if resultado.avisos:
        for aviso in resultado.avisos:
            st.warning(aviso)
    st.success(
        "✅ Publicado! O site público vai reiniciar sozinho e mostrar a "
        "atualização em instantes."
    )
    st.balloons()


def _publicar_gerencial(ano: int, conteudo_bytes: bytes, mensagem_commit: str):
    """
    Processa e publica SÓ o arquivo gerencial (indicadores de efetividade +
    atividades culturais), sem tocar nos arquivos de desdobramentos.

    Ao contrário de `_publicar()` (que sempre reprocessa TODOS os anos
    anuais a partir do zero, porque esse conjunto é cumulativo), aqui só
    existe UM arquivo gerencial "atual" por ano — então basta reprocessar
    o arquivo recém-enviado e publicar seus 3 arquivos tratados
    correspondentes, deixando lem_desdobramentos intocado.
    """
    with st.spinner("Reprocessando dados gerenciais e publicando no GitHub — isso pode levar até 1 minuto..."):
        try:
            df_gerencial, df_atividades = parse_lem_anual_2025(io.BytesIO(conteudo_bytes), ano=ano)
        except ErroDeFormato as e:
            st.error(f"Não foi possível publicar: {e}")
            return

        df_gerencial = add_date_column(df_gerencial)
        df_gerencial = df_gerencial.sort_values(["indicador", "data"]).reset_index(drop=True)
        df_gerencial["valor"] = pd.to_numeric(df_gerencial["valor"], errors="coerce")

        resultado_parcial = ResultadoReprocessamento(
            df_desdobramentos=pd.DataFrame(),
            df_gerencial=df_gerencial,
            df_atividades=df_atividades,
        )
        saida = serializar_para_publicacao(resultado_parcial)

        caminho_atual = arquivos_gerenciais_existentes.get(ano, {}).get("path")
        caminho_novo = path_gerencial(ano)

        mudancas = {}
        if caminho_atual and caminho_atual != caminho_novo:
            mudancas[caminho_atual] = None
        mudancas[caminho_novo] = conteudo_bytes
        # Só os 3 arquivos tratados GERENCIAIS entram aqui — nunca
        # lem_desdobramentos, que é responsabilidade exclusiva de
        # _publicar() (seção de planilhas anuais, acima).
        for nome_arquivo in (
            "lem_gerencial_2025.csv",
            "lem_gerencial_2025.parquet",
            "lem_atividades_culturais_2025.csv",
        ):
            mudancas[f"{PASTA_DADOS_TRATADOS}/{nome_arquivo}"] = saida[nome_arquivo]

        try:
            publicar_mudancas(mudancas, mensagem_commit)
        except ErroGitHub as e:
            st.error(f"Não foi possível publicar: {e}")
            return

    st.success(
        "✅ Publicado! O site público vai reiniciar sozinho e mostrar a "
        "atualização em instantes."
    )
    st.balloons()


st.subheader("Planilhas atualmente no painel")
if not arquivos_anuais_existentes:
    st.info("Nenhuma planilha anual publicada ainda.")
else:
    for ano, info in sorted(arquivos_anuais_existentes.items()):
        col1, col2, col3 = st.columns([2, 2, 1])
        col1.markdown(f"**{ano}**")
        col2.caption(f"{info['tamanho_kb']} KB")
        if col3.button("🗑️ Excluir", key=f"del_{ano}"):
            st.session_state["confirmar_exclusao"] = ano

    if "confirmar_exclusao" in st.session_state:
        ano_del = st.session_state["confirmar_exclusao"]
        st.warning(
            f"Tem certeza que quer excluir a planilha do ano **{ano_del}**? "
            "O painel será recalculado sem os dados desse ano."
        )
        c1, c2 = st.columns(2)
        if c1.button("Sim, excluir", type="primary"):
            estado_final = {
                a: baixar_arquivo(info["path"])
                for a, info in arquivos_anuais_existentes.items()
                if a != ano_del
            }
            estado_final[ano_del] = None
            _publicar(estado_final, f"Remove planilha do ano {ano_del}")
            del st.session_state["confirmar_exclusao"]
        if c2.button("Cancelar"):
            del st.session_state["confirmar_exclusao"]
            st.rerun()

st.divider()
st.subheader("Adicionar ou substituir uma planilha")
st.caption("Se já existir uma planilha para o mesmo ano, ela será substituída pela nova.")

ano_novo = st.number_input("Ano", min_value=2000, max_value=2100, value=2026, step=1)
arquivo_novo = st.file_uploader("Planilha LEM (.xlsx)", type=["xlsx"], key="upload_anual")

if arquivo_novo is not None:
    try:
        preview = parse_lem_file(arquivo_novo, int(ano_novo), nome_exibicao=arquivo_novo.name)
    except ErroDeFormato as e:
        st.error(str(e))
        preview = None

    if preview is not None:
        if preview.empty:
            st.warning("A planilha foi lida, mas nenhum registro com dado foi encontrado. Confira o arquivo.")
        else:
            st.success(f"Planilha lida com sucesso: {len(preview)} registros encontrados.")
            st.dataframe(
                preview.groupby("secao")["indicador"].nunique().rename("Nº de indicadores")
            )
            if st.button("✅ Confirmar e publicar", type="primary", key="confirmar_anual"):
                estado_final = {
                    a: baixar_arquivo(info["path"])
                    for a, info in arquivos_anuais_existentes.items()
                    if a != int(ano_novo)
                }
                arquivo_novo.seek(0)
                estado_final[int(ano_novo)] = arquivo_novo.read()
                _publicar(
                    estado_final,
                    f"Adiciona/substitui planilha do ano {int(ano_novo)}",
                )

st.divider()
st.subheader("Arquivo gerencial anual")
st.caption(
    "Alimenta a página \"Efetividade Gerencial\" do painel — indicadores de "
    "efetividade social e atividades culturais. Estrutura própria, "
    "independente das planilhas anuais acima."
)

if not arquivos_gerenciais_existentes:
    st.info("Nenhum arquivo gerencial publicado ainda.")
else:
    for ano, info in sorted(arquivos_gerenciais_existentes.items()):
        st.markdown(f"**Arquivo gerencial de {ano}** — {info['tamanho_kb']} KB")

ano_gerencial_novo = st.number_input(
    "Ano de referência do arquivo gerencial", min_value=2000, max_value=2100, value=2025, step=1,
    key="ano_gerencial_novo",
)
arquivo_gerencial_novo = st.file_uploader(
    "Arquivo gerencial (.xlsx) — ex.: \"LEM anual completo.xlsx\"", type=["xlsx"], key="upload_gerencial",
)

if arquivo_gerencial_novo is not None:
    try:
        preview_gerencial, preview_atividades = parse_lem_anual_2025(
            arquivo_gerencial_novo, int(ano_gerencial_novo), nome_exibicao=arquivo_gerencial_novo.name
        )
    except ErroDeFormato as e:
        st.error(str(e))
        preview_gerencial = None

    if preview_gerencial is not None:
        if preview_gerencial.empty:
            st.warning("A planilha foi lida, mas nenhum indicador gerencial com dado foi encontrado. Confira o arquivo.")
        else:
            st.success(
                f"Planilha lida com sucesso: {preview_gerencial['indicador'].nunique()} indicadores "
                f"gerenciais e {len(preview_atividades)} registros de atividades culturais encontrados."
            )
            if st.button("✅ Confirmar e publicar arquivo gerencial", type="primary", key="confirmar_gerencial"):
                arquivo_gerencial_novo.seek(0)
                conteudo_gerencial = arquivo_gerencial_novo.read()
                _publicar_gerencial(
                    int(ano_gerencial_novo),
                    conteudo_gerencial,
                    f"Adiciona/substitui arquivo gerencial do ano {int(ano_gerencial_novo)}",
                )
