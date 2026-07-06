"""
utils/github_sync.py — Sincronização com o repositório GitHub que alimenta
o Streamlit Community Cloud.

Por quê isto existe: o disco do Streamlit Community Cloud é temporário
(reinicia sozinho de vez em quando e não guarda nada entre reinícios). Para
que os arquivos enviados pela equipe da Fundação sobrevivam e para que o
painel público reflita as mudanças, a pasta `dados_brutos/` dentro do
próprio repositório GitHub funciona como o "disco permanente": qualquer
arquivo adicionado, substituído ou removido é gravado diretamente lá via
API do GitHub, num único commit atômico — o que aciona automaticamente o
redeploy do Streamlit Cloud (ele já fica de olho nesse repositório).

Credenciais: lidas de st.secrets, NUNCA do código-fonte.
    [github]
    token  = "ghp_..."                        # Personal Access Token, escopo "repo"
    repo   = "peixejulia/Pao_dos_Pobres_Dashboards"
    branch = "main"                           # opcional, default "main"
"""
from __future__ import annotations

import base64
import re

import streamlit as st
from github import Github, InputGitTreeElement
from github.GithubException import GithubException, UnknownObjectException

# Pasta (relativa à raiz do repositório) onde os arquivos brutos ficam.
PASTA_BRUTOS = "pao_dos_pobres/dados_brutos"
PASTA_DADOS_TRATADOS = "pao_dos_pobres/dados"


class ErroGitHub(Exception):
    """Erro amigável para exibir na interface (esconde detalhes técnicos)."""


def _secrets_ok() -> bool:
    try:
        return "github" in st.secrets and all(
            k in st.secrets["github"] for k in ("token", "repo")
        )
    except Exception:
        # Nenhum secrets.toml configurado ainda (comum em ambiente local/teste)
        return False


def _repo():
    if not _secrets_ok():
        raise ErroGitHub(
            "As credenciais do GitHub não foram configuradas ainda "
            '(faltam "token"/"repo" em st.secrets["github"]).'
        )
    try:
        gh = Github(st.secrets["github"]["token"])
        return gh.get_repo(st.secrets["github"]["repo"])
    except GithubException as e:
        raise ErroGitHub(f"Não foi possível acessar o repositório no GitHub ({e}).") from e
    except Exception as e:
        raise ErroGitHub(f"Não foi possível conectar ao GitHub agora ({e}).") from e


def _branch() -> str:
    try:
        return st.secrets.get("github", {}).get("branch", "main")
    except Exception:
        return "main"


# ── Convenções de nomes (é isso que faz a pasta funcionar como "a lista") ──────

def path_anual(ano: int, unidade: str) -> str:
    unidade_slug = re.sub(r"\s+", "_", unidade.strip().lower())
    return f"{PASTA_BRUTOS}/anual/{ano}_{unidade_slug}.xlsx"


def path_gerencial(ano: int) -> str:
    return f"{PASTA_BRUTOS}/gerencial/{ano}_gerencial.xlsx"


def metadata_do_path(path: str) -> dict | None:
    """Extrai {tipo, ano, unidade} a partir de um caminho gerado por path_anual/path_gerencial."""
    m = re.search(r"/anual/(\d{4})_(.+)\.xlsx$", path)
    if m:
        return {"tipo": "anual", "ano": int(m.group(1)), "unidade": m.group(2)}
    m = re.search(r"/gerencial/(\d{4})_gerencial\.xlsx$", path)
    if m:
        return {"tipo": "gerencial", "ano": int(m.group(1))}
    return None


# ── Leitura ────────────────────────────────────────────────────────────────────

def listar_arquivos_brutos() -> list[dict]:
    """
    Lista os arquivos atualmente em dados_brutos/ (e subpastas) no GitHub.
    Cada item: {nome, path, tamanho_kb, sha, metadata}.
    """
    repo = _repo()
    branch = _branch()
    arquivos = []

    def _listar_pasta(path):
        try:
            itens = repo.get_contents(path, ref=branch)
        except UnknownObjectException:
            return
        except GithubException as e:
            raise ErroGitHub(f"Não foi possível listar os arquivos no GitHub ({e}).") from e
        except Exception as e:
            raise ErroGitHub(f"Não foi possível conectar ao GitHub agora ({e}).") from e
        for item in itens:
            if item.type == "dir":
                _listar_pasta(item.path)
            else:
                arquivos.append({
                    "nome": item.name,
                    "path": item.path,
                    "tamanho_kb": round(item.size / 1024, 1),
                    "sha": item.sha,
                    "metadata": metadata_do_path(item.path),
                })

    _listar_pasta(PASTA_BRUTOS)
    return arquivos


def baixar_arquivo(path: str) -> bytes:
    """Baixa o conteúdo bruto (bytes) de um arquivo do repositório."""
    repo = _repo()
    try:
        conteudo = repo.get_contents(path, ref=_branch())
    except UnknownObjectException as e:
        raise ErroGitHub(f'Arquivo "{path}" não encontrado no repositório.') from e
    except GithubException as e:
        raise ErroGitHub(f"Não foi possível baixar o arquivo do GitHub ({e}).") from e
    except Exception as e:
        raise ErroGitHub(f"Não foi possível conectar ao GitHub agora ({e}).") from e
    return conteudo.decoded_content


# ── Escrita (commit atômico multi-arquivo) ─────────────────────────────────────

def publicar_mudancas(mudancas: dict, mensagem_commit: str) -> str:
    """
    Publica um conjunto de mudanças em UM ÚNICO commit, o que dispara UM
    ÚNICO redeploy do Streamlit Cloud (em vez de vários seguidos).

    `mudancas`: dict {caminho_no_repo: bytes_do_conteudo}
                 use valor None para EXCLUIR aquele caminho.
    Retorna o SHA do novo commit.
    """
    repo = _repo()
    branch = _branch()
    try:
        ref = repo.get_git_ref(f"heads/{branch}")
        commit_base = repo.get_git_commit(ref.object.sha)
        base_tree = commit_base.tree

        elementos = []
        for path, conteudo in mudancas.items():
            if conteudo is None:
                elementos.append(InputGitTreeElement(path=path, mode="100644", type="blob", sha=None))
            else:
                content_b64 = base64.b64encode(conteudo).decode("ascii")
                blob = repo.create_git_blob(content_b64, "base64")
                elementos.append(InputGitTreeElement(path=path, mode="100644", type="blob", sha=blob.sha))

        nova_tree = repo.create_git_tree(elementos, base_tree)
        novo_commit = repo.create_git_commit(mensagem_commit, nova_tree, [commit_base])
        ref.edit(novo_commit.sha)
        return novo_commit.sha
    except GithubException as e:
        raise ErroGitHub(f"Falha ao publicar as mudanças no GitHub ({e}).") from e
    except ErroGitHub:
        raise
    except Exception as e:
        raise ErroGitHub(f"Não foi possível conectar ao GitHub agora ({e}).") from e


def testar_conexao() -> tuple[bool, str]:
    """Verifica se as credenciais funcionam. Usado por um botão de diagnóstico na interface."""
    try:
        repo = _repo()
        _ = repo.get_git_ref(f"heads/{_branch()}")
        return True, f'Conectado com sucesso ao repositório "{repo.full_name}".'
    except ErroGitHub as e:
        return False, str(e)
    except GithubException as e:
        return False, f"Erro do GitHub: {e}"
    except Exception as e:
        return False, f"Não foi possível conectar ao GitHub agora ({e})."
