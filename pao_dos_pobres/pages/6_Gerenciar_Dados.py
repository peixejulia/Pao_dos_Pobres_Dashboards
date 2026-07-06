"""
Página 6 — Gerenciar Dados (área restrita)

Permite à equipe da Fundação:
  • Ver quais planilhas LEM estão hoje alimentando o painel
  • Adicionar uma planilha nova (ano/unidade) ou substituir uma existente
  • Excluir uma planilha (o painel recalcula tudo sem ela)

Cada mudança reprocessa TODOS os dados a partir dos arquivos que restarem
e publica o resultado num único commit no GitHub — o mesmo repositório
que alimenta o site público no Streamlit Cloud, que se atualiza sozinho
a partir disso.
"""
import streamlit as st

from utils.style import titulo_com_logo
from utils.tratamento import (
    reprocessar_tudo,
    serializar_para_publicacao,
    parse_lem_file,
    ErroDeFormato,
)
from utils.github_sync import (
    listar_arquivos_brutos,
    baixar_arquivo,
    publicar_mudancas,
    testar_conexao,
    path_anual,
    PASTA_DADOS_TRATADOS,
    ErroGitHub,
)

st.set_page_config(page_title="Gerenciar Dados · LEM", layout="wide")

titulo_com_logo("Gerenciar Dados")
st.markdown(
    "Área restrita para adicionar, substituir ou remover as planilhas LEM "
    "que alimentam o painel. Qualquer mudança aqui atualiza o site público "
    "automaticamente em cerca de 1 minuto."
)

st.markdown("**ℹ️ Como usar esta página** (clique em cada tópico abaixo para expandir)")

with st.expander("❓ O que é \"Unidade\"?"):
    st.markdown(
        "É a casa/unidade física da Fundação que gerou aquela planilha (caso "
        "existam várias casas reportando separadamente). Hoje todos os dados "
        "históricos usam **`unidade_1`** — a não ser que você tenha certeza de "
        "que o arquivo é de uma casa diferente, **deixe sempre `unidade_1`**."
    )

with st.expander("📅 Passo a passo — Adicionar ou substituir uma planilha anual"):
    st.markdown(
        "1. Em **Ano**, escolha o ano da planilha (ex.: 2026).\n"
        "2. Em **Unidade**, deixe `unidade_1` (a não ser que saiba que é outra).\n"
        "3. Clique em **Upload** e escolha o arquivo Excel (.xlsx) no seu computador.\n"
        "4. Confira a mensagem de prévia (\"Planilha lida com sucesso: X registros "
        "encontrados\"). Se aparecer um erro em vermelho, pare e peça ajuda antes "
        "de continuar.\n"
        "5. Clique em **\"✅ Confirmar e publicar\"** e aguarde a mensagem de "
        "sucesso — o site público reinicia sozinho em seguida (leva uns 30 a "
        "60 segundos).\n"
        "6. Se já existia uma planilha para o mesmo ano e unidade, ela é "
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
        "recalculado sem os dados daquele ano/unidade."
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

arquivos_anuais_existentes = {
    (a["metadata"]["ano"], a["metadata"]["unidade"]): a
    for a in arquivos
    if a["metadata"] and a["metadata"]["tipo"] == "anual"
}


def _publicar(novos_anuais: dict, mensagem_commit: str):
    """
    Reprocessa tudo a partir do conjunto final de arquivos (já com a
    mudança aplicada) e publica num único commit.
    `novos_anuais`: dict {(ano, unidade): bytes_ou_None}  (None = exclui)
    """
    with st.spinner("Reprocessando dados e publicando no GitHub — isso pode levar até 1 minuto..."):
        resultado = reprocessar_tudo(novos_anuais)

        mudancas = {}
        for (ano, unidade), conteudo in novos_anuais.items():
            mudancas[path_anual(ano, unidade)] = conteudo  # None = exclui

        saida = serializar_para_publicacao(resultado)
        for nome_arquivo, conteudo in saida.items():
            mudancas[f"{PASTA_DADOS_TRATADOS}/{nome_arquivo}"] = conteudo

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


st.subheader("Planilhas atualmente no painel")
if not arquivos_anuais_existentes:
    st.info("Nenhuma planilha anual publicada ainda.")
else:
    for (ano, unidade), info in sorted(arquivos_anuais_existentes.items()):
        col1, col2, col3 = st.columns([2, 2, 1])
        col1.markdown(f"**{ano}** — {unidade}")
        col2.caption(f"{info['tamanho_kb']} KB")
        if col3.button("🗑️ Excluir", key=f"del_{ano}_{unidade}"):
            st.session_state["confirmar_exclusao"] = (ano, unidade)

    if "confirmar_exclusao" in st.session_state:
        ano_del, unidade_del = st.session_state["confirmar_exclusao"]
        st.warning(
            f"Tem certeza que quer excluir a planilha de **{ano_del} / {unidade_del}**? "
            "O painel será recalculado sem os dados desse ano/unidade."
        )
        c1, c2 = st.columns(2)
        if c1.button("Sim, excluir", type="primary"):
            novos_anuais = {
                (a, u): baixar_arquivo(info["path"])
                for (a, u), info in arquivos_anuais_existentes.items()
                if (a, u) != (ano_del, unidade_del)
            }
            novos_anuais[(ano_del, unidade_del)] = None  # marca para exclusão
            _publicar(novos_anuais, f"Remove planilha {ano_del}/{unidade_del}")
            del st.session_state["confirmar_exclusao"]
        if c2.button("Cancelar"):
            del st.session_state["confirmar_exclusao"]
            st.rerun()

st.divider()
st.subheader("Adicionar ou substituir uma planilha")
st.caption(
    "Se já existir uma planilha para o mesmo ano e unidade, ela será "
    "substituída pela nova."
)

col_ano, col_unidade = st.columns(2)
ano_novo = col_ano.number_input("Ano", min_value=2000, max_value=2100, value=2026, step=1)
unidade_nova = col_unidade.text_input("Unidade", value="unidade_1")
arquivo_novo = st.file_uploader("Planilha LEM (.xlsx)", type=["xlsx"], key="upload_anual")

if arquivo_novo is not None:
    try:
        preview = parse_lem_file(arquivo_novo, int(ano_novo), unidade_nova, nome_exibicao=arquivo_novo.name)
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
                novos_anuais = {
                    (a, u): baixar_arquivo(info["path"])
                    for (a, u), info in arquivos_anuais_existentes.items()
                    if (a, u) != (int(ano_novo), unidade_nova)
                }
                arquivo_novo.seek(0)
                novos_anuais[(int(ano_novo), unidade_nova)] = arquivo_novo.read()
                _publicar(
                    novos_anuais,
                    f"Adiciona/substitui planilha {int(ano_novo)}/{unidade_nova}",
                )
