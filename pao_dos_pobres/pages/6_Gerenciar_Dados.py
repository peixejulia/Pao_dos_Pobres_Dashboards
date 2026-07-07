"""
Página 6 — Gerenciar Dados (área restrita)

Permite à equipe da Fundação:
  • Ver quais planilhas LEM estão hoje alimentando o painel
  • Adicionar uma planilha nova (por ano) ou substituir uma existente
  • Excluir uma planilha (o painel recalcula tudo sem ela)

Cada mudança reprocessa TODOS os dados a partir dos arquivos que restarem
e publica o resultado num único commit no GitHub — o mesmo repositório
que alimenta o site público no Streamlit Cloud, que se atualiza sozinho
a partir disso.

NOTA: esta página não pede mais uma "Unidade" para cada planilha — cada
ano tem no máximo UMA planilha oficial. O campo existia para o caso de a
Fundação reportar por casa/unidade separadamente, mas isso nunca foi
confirmado com a instituição e, na prática, só criava risco: bastava
digitar um nome de unidade diferente por engano para o painel passar a
tratar aquilo como um arquivo "novo" em vez de substituir o existente,
gerando dados fragmentados ou duplicados. Se no futuro a Fundação passar
a reportar por unidade de fato, vale reintroduzir o campo com uma lista
fixa (não texto livre) para evitar esse risco.
"""
from pathlib import Path

import streamlit as st
from PIL import Image

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
        # Esta página só gerencia planilhas anuais (desdobramentos) — não há
        # upload de arquivo gerencial aqui (removido em 06/07/2026), então
        # reprocessar_tudo() sempre roda com arquivo_gerencial=None, o que
        # produz DataFrames VAZIOS para lem_gerencial_2025 e
        # lem_atividades_culturais_2025. Publicar esses arquivos aqui
        # apagaria silenciosamente os dados reais já publicados (foi
        # exatamente o que aconteceu: um publish anterior zerou os dois).
        # Por isso só os arquivos de desdobramentos entram nesta publicação.
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
