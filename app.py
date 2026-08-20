"""
Explorador de Questões — ENEM (Microdados de Itens)
=====================================================
App Streamlit enxuto, no estilo do questoesenem.streamlit.app: escolha
o ano, a aplicação (Regular ou PPL/Reaplicação) e a prova, e veja a
tabela com a habilidade e a dificuldade de cada uma das questões.

Como usar
---------
1. Baixe os microdados do ENEM em:
   https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem
2. Dentro do zip de cada ano, pegue o arquivo:
   DADOS/ITENS_PROVA_AAAA.csv
3. Coloque esse(s) arquivo(s) dentro da pasta "dados/" ao lado deste
   script (pode ter vários anos, um arquivo por ano) OU envie pelo
   uploader dentro do próprio app.
4. Rode:  streamlit run app.py

Se nenhum arquivo for encontrado, o app carrega um conjunto de dados
de EXEMPLO (fictício) só para você visualizar o layout antes de
plugar os dados reais.
"""

import glob
import os
import re

import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------------
# Configuração da página
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Questões ENEM",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "dados")

# ------------------------------------------------------------------
# Matrizes de Referência do INEP — uma por área do conhecimento.
# Cada matriz mapeia faixas de habilidade (H1–H30, numeração reinicia
# em cada área) às competências de área oficiais.
# ------------------------------------------------------------------
MATRIZES = {
    "MT": {
        "nome": "Matemática",
        "competencias": {
            1: "C1 · Números e operações", 2: "C2 · Geometria (espaço e forma)",
            3: "C3 · Grandezas e medidas", 4: "C4 · Variação de grandezas",
            5: "C5 · Álgebra e funções", 6: "C6 · Gráficos e tabelas",
            7: "C7 · Estatística e probabilidade",
        },
        "faixas": {
            1: range(1, 6), 2: range(6, 10), 3: range(10, 15), 4: range(15, 19),
            5: range(19, 24), 6: range(24, 27), 7: range(27, 31),
        },
    },
    "LC": {
        "nome": "Linguagens",
        "competencias": {
            1: "C1 · Tecnologias da comunicação", 2: "C2 · Língua estrangeira moderna",
            3: "C3 · Linguagem corporal", 4: "C4 · Arte", 5: "C5 · Texto literário",
            6: "C6 · Sistemas simbólicos e linguagens", 7: "C7 · Confronto de opiniões",
            8: "C8 · Língua portuguesa", 9: "C9 · Tecnologias da informação",
        },
        "faixas": {
            1: range(1, 5), 2: range(5, 9), 3: range(9, 12), 4: range(12, 15),
            5: range(15, 18), 6: range(18, 21), 7: range(21, 25),
            8: range(25, 28), 9: range(28, 31),
        },
    },
    "CH": {
        "nome": "Humanas",
        "competencias": {
            1: "C1 · Identidades culturais", 2: "C2 · Espaços geográficos",
            3: "C3 · Instituições sociais", 4: "C4 · Técnicas e tecnologias",
            5: "C5 · Cidadania e democracia", 6: "C6 · Sociedade e natureza",
        },
        "faixas": {
            1: range(1, 6), 2: range(6, 11), 3: range(11, 16),
            4: range(16, 21), 5: range(21, 26), 6: range(26, 31),
        },
    },
    "CN": {
        "nome": "Natureza",
        "competencias": {
            1: "C1 · Ciência e tecnologia", 2: "C2 · Tecnologias associadas",
            3: "C3 · Intervenções ambientais", 4: "C4 · Organismo e saúde",
            5: "C5 · Métodos científicos", 6: "C6 · Física aplicada",
            7: "C7 · Química aplicada", 8: "C8 · Biologia aplicada",
        },
        "faixas": {
            1: range(1, 5), 2: range(5, 8), 3: range(8, 13), 4: range(13, 17),
            5: range(17, 20), 6: range(20, 24), 7: range(24, 28), 8: range(28, 31),
        },
    },
}

# Ordem de exibição dos botões "Selecione a Prova"
ORDEM_AREAS = ["LC", "CH", "CN", "MT"]

# Preferência de cor quando disponível na aplicação escolhida
ORDEM_COR_PREFERIDA = ["AZUL", "AMARELA", "BRANCA", "ROSA", "CINZA", "VERDE", "LARANJA", "ROXA"]


# ------------------------------------------------------------------
# Tema escuro (equivalente ao app de referência)
# ------------------------------------------------------------------
def _garantir_tema_escuro():
    config_dir = os.path.join(os.path.dirname(__file__), ".streamlit")
    config_path = os.path.join(config_dir, "config.toml")
    if not os.path.exists(config_path):
        os.makedirs(config_dir, exist_ok=True)
        with open(config_path, "w") as f:
            f.write(
                "[theme]\nbase = \"dark\"\nprimaryColor = \"#FF4B6E\"\n"
                "backgroundColor = \"#0E1117\"\nsecondaryBackgroundColor = \"#1E2129\"\n"
                "textColor = \"#FAFAFA\"\n"
            )


_garantir_tema_escuro()


# ------------------------------------------------------------------
# Carregamento de dados
# ------------------------------------------------------------------
def _extrair_ano_do_nome(nome_arquivo: str):
    match = re.search(r"(19|20)\d{2}", nome_arquivo)
    return int(match.group()) if match else None


def _ler_csv_flexivel(caminho_ou_arquivo, nome_arquivo: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(caminho_ou_arquivo, sep=";", encoding="latin-1")
        if df.shape[1] == 1:
            raise ValueError("separador incorreto")
    except Exception:
        if hasattr(caminho_ou_arquivo, "seek"):
            caminho_ou_arquivo.seek(0)
        df = pd.read_csv(caminho_ou_arquivo, sep=",", encoding="utf-8")

    if "NU_ANO" not in df.columns:
        df["NU_ANO"] = _extrair_ano_do_nome(nome_arquivo)

    return df


@st.cache_data(show_spinner="Carregando microdados...")
def carregar_dados_reais(arquivos_enviados=None) -> pd.DataFrame:
    frames = []

    caminhos_locais = sorted(glob.glob(os.path.join(DATA_DIR, "ITENS_PROVA_*.csv")))
    for caminho in caminhos_locais:
        try:
            frames.append(_ler_csv_flexivel(caminho, os.path.basename(caminho)))
        except Exception as e:
            st.warning(f"Não foi possível ler {os.path.basename(caminho)}: {e}")

    if arquivos_enviados:
        for arq in arquivos_enviados:
            try:
                frames.append(_ler_csv_flexivel(arq, arq.name))
            except Exception as e:
                st.warning(f"Não foi possível ler {arq.name}: {e}")

    if not frames:
        return pd.DataFrame()

    dados = pd.concat(frames, ignore_index=True)

    if "SG_AREA" in dados.columns:
        dados["SG_AREA"] = dados["SG_AREA"].astype(str).str.upper().str.strip()
        dados = dados[dados["SG_AREA"].isin(MATRIZES.keys())]

    dados = _classificar_aplicacoes(dados)
    return tratar_dados(dados)


def _classificar_aplicacoes(dados: pd.DataFrame) -> pd.DataFrame:
    """Para cada combinação (ano, área), identifica os grupos de
    CO_PROVA que compartilham o mesmo conjunto de itens (= mesma
    aplicação do exame) e classifica o grupo com mais cores/cadernos
    como 'Regular' e o segundo colocado como 'PPL/Reaplicação'. Os
    demais grupos (versões adicionais/adaptadas menores) ficam de
    fora, mantendo o app fiel ao padrão binário Regular vs.
    PPL/Reaplicação."""
    chaves = {"NU_ANO", "SG_AREA", "CO_ITEM", "CO_PROVA"}
    if not chaves.issubset(dados.columns):
        dados = dados.copy()
        dados["APLICACAO"] = "Regular"
        return dados

    dados = dados.copy()
    dados["APLICACAO"] = pd.NA

    for (ano, area), bloco in dados.groupby(["NU_ANO", "SG_AREA"]):
        grupos_por_prova = bloco.groupby("CO_PROVA")["CO_ITEM"].apply(lambda s: frozenset(s))
        conjuntos = set(grupos_por_prova.values)

        ranking = []
        for conjunto in conjuntos:
            provas_do_conjunto = [p for p, s in grupos_por_prova.items() if s == conjunto]
            n_cores = bloco[bloco["CO_PROVA"].isin(provas_do_conjunto)]["TX_COR"].nunique()
            ranking.append((n_cores, len(provas_do_conjunto), conjunto, provas_do_conjunto))
        ranking.sort(key=lambda t: (t[0], t[1]), reverse=True)

        rotulos = {}
        if len(ranking) >= 1:
            for prova in ranking[0][3]:
                rotulos[prova] = "Regular"
        if len(ranking) >= 2:
            for prova in ranking[1][3]:
                rotulos[prova] = "PPL/Reaplicação"

        indices = dados.index[(dados["NU_ANO"] == ano) & (dados["SG_AREA"] == area)]
        dados.loc[indices, "APLICACAO"] = dados.loc[indices, "CO_PROVA"].map(rotulos)

    # descarta grupos além do 2º colocado (versões digitais/adaptadas extras)
    dados = dados[dados["APLICACAO"].notna()]
    dados = dados.drop_duplicates(subset=["NU_ANO", "SG_AREA", "CO_ITEM", "APLICACAO", "TX_COR"])
    return dados


@st.cache_data
def gerar_dados_exemplo(seed: int = 42) -> pd.DataFrame:
    """Base fictícia só para demonstração do layout, com 45 itens por
    área/ano/aplicação (50 em Linguagens, por causa da língua
    estrangeira), como numa aplicação real do ENEM."""
    import numpy as np

    rng = np.random.default_rng(seed)
    anos_exemplo = list(range(2020, 2026))
    cores_regular = ["AZUL", "AMARELA", "BRANCA", "ROSA"]
    cores_ppl = ["CINZA", "VERDE"]

    blocos = []
    for ano in anos_exemplo:
        for area in MATRIZES.keys():
            n_por_prova = 50 if area == "LC" else 45
            for aplicacao, cores in [("Regular", cores_regular), ("PPL/Reaplicação", cores_ppl)]:
                item_ids = rng.integers(100000, 999999, size=n_por_prova)
                for cor in cores:
                    blocos.append(pd.DataFrame({
                        "CO_ITEM": item_ids,
                        "SG_AREA": area,
                        "NU_ANO": ano,
                        "CO_PROVA": f"{ano}{area}{aplicacao[:3]}{cor[:2]}",
                        "TX_COR": cor,
                        "APLICACAO": aplicacao,
                        "CO_HABILIDADE": rng.integers(1, 31, size=n_por_prova),
                        "TX_GABARITO": rng.choice(list("ABCDE"), size=n_por_prova),
                        "CO_POSICAO": range(1, 1 + n_por_prova),
                        "NU_PARAM_A": rng.uniform(0.5, 2.2, size=n_por_prova).round(3),
                        "NU_PARAM_B": rng.normal(0.4, 1.1, size=n_por_prova).round(3),
                        "NU_PARAM_C": rng.uniform(0.05, 0.25, size=n_por_prova).round(3),
                        "IN_ITEM_ABAN": rng.choice([0, 0, 0, 0, 1], size=n_por_prova),
                        "TX_MOTIVO_ABAN": None,
                    }))

    dados = pd.concat(blocos, ignore_index=True)
    return tratar_dados(dados)


def tratar_dados(dados: pd.DataFrame) -> pd.DataFrame:
    dados = dados.copy()

    for col in ["NU_PARAM_A", "NU_PARAM_B", "NU_PARAM_C"]:
        if col in dados.columns:
            dados[col] = pd.to_numeric(dados[col], errors="coerce")

    if "NU_PARAM_B" in dados.columns:
        dados["NIVEL_DIFICULDADE"] = pd.cut(
            dados["NU_PARAM_B"],
            bins=[-99, -1, 0, 1, 99],
            labels=["Muito fácil", "Fácil", "Médio", "Difícil"],
        )

    if {"SG_AREA", "CO_HABILIDADE"}.issubset(dados.columns):
        dados["CO_HABILIDADE"] = pd.to_numeric(dados["CO_HABILIDADE"], errors="coerce")

        def _mapear_competencia(row):
            info = MATRIZES.get(row["SG_AREA"])
            if info is None or pd.isna(row["CO_HABILIDADE"]):
                return "Não classificado"
            h = int(row["CO_HABILIDADE"])
            for comp, faixa in info["faixas"].items():
                if h in faixa:
                    return info["competencias"][comp]
            return "Não classificado"

        dados["COMPETENCIA"] = dados.apply(_mapear_competencia, axis=1)
        dados["HABILIDADE_LABEL"] = "H" + dados["CO_HABILIDADE"].astype("Int64").astype(str)

    if "IN_ITEM_ABAN" in dados.columns:
        dados["SITUACAO"] = dados["IN_ITEM_ABAN"].map({0: "Válido", 1: "Anulado"}).fillna("Válido")

    return dados


def _escolher_cor(cores_disponiveis: list) -> str:
    for preferida in ORDEM_COR_PREFERIDA:
        if preferida in cores_disponiveis:
            return preferida
    return sorted(cores_disponiveis)[0] if cores_disponiveis else "—"


# ------------------------------------------------------------------
# Carregamento
# ------------------------------------------------------------------
with st.expander("📁 Enviar arquivos ITENS_PROVA (.csv)", expanded=False):
    arquivos = st.file_uploader(
        "Arraste um ou mais arquivos ITENS_PROVA_AAAA.csv",
        type=["csv"],
        accept_multiple_files=True,
    )

dados = carregar_dados_reais(arquivos)
usando_exemplo = dados.empty
if usando_exemplo:
    dados = gerar_dados_exemplo()

# ------------------------------------------------------------------
# Cabeçalho
# ------------------------------------------------------------------
st.markdown(
    "Nesta aplicação você pode consultar a habilidade e a dificuldade de "
    "cada uma das questões do ENEM dos últimos anos, conforme publicado "
    "nos microdados do ENEM."
)
if usando_exemplo:
    st.warning(
        "Nenhum microdado real encontrado — exibindo **dados de exemplo** "
        "(fictícios). Envie os arquivos reais acima, ou coloque-os na pasta `dados/`."
    )

# ------------------------------------------------------------------
# Controles — Ano / Aplicação / Prova
# ------------------------------------------------------------------
anos_disponiveis = sorted(dados["NU_ANO"].dropna().unique().tolist(), reverse=True) if "NU_ANO" in dados.columns else []

st.markdown("**Ano da aplicação**")
ano_selecionado = st.selectbox("Ano da aplicação", options=anos_disponiveis, label_visibility="collapsed")

st.markdown("**Aplicação**")
aplicacao_selecionada = st.radio(
    "Aplicação", options=["Regular", "PPL/Reaplicação"], horizontal=True, label_visibility="collapsed",
)

st.markdown("**Selecione a Prova**")
areas_no_ano = dados.loc[dados["NU_ANO"] == ano_selecionado, "SG_AREA"].unique().tolist() if ano_selecionado is not None else []
opcoes_area = [a for a in ORDEM_AREAS if a in areas_no_ano]
area_selecionada = st.radio(
    "Selecione a Prova",
    options=opcoes_area,
    format_func=lambda a: MATRIZES[a]["nome"],
    horizontal=True,
    label_visibility="collapsed",
)

# ------------------------------------------------------------------
# Filtragem
# ------------------------------------------------------------------
filtrado = dados[
    (dados["NU_ANO"] == ano_selecionado)
    & (dados["APLICACAO"] == aplicacao_selecionada)
    & (dados["SG_AREA"] == area_selecionada)
].copy()

if filtrado.empty:
    st.info(
        f"Não há dados para {MATRIZES.get(area_selecionada, {}).get('nome', area_selecionada)} "
        f"· {ano_selecionado} · {aplicacao_selecionada}. Tente outra combinação."
    )
else:
    cores_disponiveis = sorted(filtrado["TX_COR"].dropna().unique().tolist()) if "TX_COR" in filtrado.columns else []
    cor_padrao = _escolher_cor(cores_disponiveis)

    if cores_disponiveis:
        st.markdown("**Cor da Prova**")
        cor_selecionada = st.selectbox(
            "Cor da Prova",
            options=cores_disponiveis,
            index=cores_disponiveis.index(cor_padrao) if cor_padrao in cores_disponiveis else 0,
            format_func=lambda c: c.title(),
            label_visibility="collapsed",
        )
        filtrado = filtrado[filtrado["TX_COR"] == cor_selecionada]
    else:
        cor_selecionada = None

    # Em Linguagens, o candidato escolhe Inglês ou Espanhol no dia da
    # prova — deixamos essa escolha explícita em vez de fixar em Inglês.
    idioma_selecionado = None
    if "TP_LINGUA" in filtrado.columns and area_selecionada == "LC":
        st.markdown("**Língua estrangeira**")
        idioma_selecionado = st.radio(
            "Língua estrangeira",
            options=["Inglês", "Espanhol"],
            horizontal=True,
            label_visibility="collapsed",
        )
        codigo_idioma = {"Inglês": 0, "Espanhol": 1}[idioma_selecionado]
        filtrado["TP_LINGUA"] = pd.to_numeric(filtrado["TP_LINGUA"], errors="coerce")
        filtrado = filtrado[filtrado["TP_LINGUA"].isna() | (filtrado["TP_LINGUA"] == codigo_idioma)]

    st.divider()

    colunas_exibir = {
        "CO_POSICAO": "Questão",
        "HABILIDADE_LABEL": "Habilidade",
        "COMPETENCIA": "Competência",
        "TX_GABARITO": "Gabarito",
        "NIVEL_DIFICULDADE": "Dificuldade",
    }
    colunas_presentes = [c for c in colunas_exibir if c in filtrado.columns]

    tabela = filtrado[colunas_presentes].rename(columns=colunas_exibir)
    if "Questão" in tabela.columns:
        tabela = tabela.sort_values("Questão")

    st.dataframe(tabela, use_container_width=True, hide_index=True, height=520)

    csv_export = tabela.to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button(
        "⬇️ Baixar esta prova em CSV",
        data=csv_export,
        file_name=f"enem_{ano_selecionado}_{area_selecionada}_{aplicacao_selecionada.replace('/', '-')}.csv",
        mime="text/csv",
    )

    st.caption(
        f"{len(tabela)} questões"
        + (f" · língua estrangeira: {idioma_selecionado}" if idioma_selecionado else "")
        + " · fonte: microdados do ENEM (INEP) · "
        "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem"
    )

    # ------------------------------------------------------------------
    # Gráficos de incidência das habilidades
    # ------------------------------------------------------------------
    def _grafico_incidencia(dados_para_grafico: pd.DataFrame):
        base = dados_para_grafico[dados_para_grafico["HABILIDADE_LABEL"].notna()]
        if base.empty:
            return None
        contagem = (
            base.groupby(["HABILIDADE_LABEL", "COMPETENCIA"])
            .size()
            .reset_index(name="Incidência")
        )
        contagem["_ordem"] = contagem["HABILIDADE_LABEL"].str.replace("H", "", regex=False).astype(int)
        contagem = contagem.sort_values("_ordem")

        fig = px.bar(
            contagem, x="HABILIDADE_LABEL", y="Incidência", color="COMPETENCIA",
            labels={"HABILIDADE_LABEL": "Habilidade", "COMPETENCIA": "Competência"},
        )
        fig.update_layout(xaxis_title="Habilidade", yaxis_title="Nº de vezes que apareceu", legend_title="Competência")
        return fig

    st.divider()
    st.markdown(f"#### 📊 Incidência das habilidades — {MATRIZES[area_selecionada]['nome']}")

    # --- Gráfico 1: só o ano selecionado (mesmos filtros da tabela) ---
    st.markdown(f"**Ano {int(ano_selecionado)}** ({aplicacao_selecionada})")
    fig_ano = _grafico_incidencia(filtrado)
    if fig_ano is not None:
        st.plotly_chart(fig_ano, use_container_width=True)
    else:
        st.info("Não há dados suficientes para este ano.")

    # --- Gráfico 2: total acumulado dos anos carregados ---
    st.markdown(
        f"**Total acumulado ({int(min(anos_disponiveis))}–{int(max(anos_disponiveis))}, Regular)**"
    )
    st.caption(
        "Soma das ocorrências de cada habilidade em todos os anos carregados "
        "(sempre a aplicação Regular e a cor de prova preferida disponível)"
        + (f", língua estrangeira: **{idioma_selecionado}**." if idioma_selecionado else ".")
    )

    linhas_historico = []
    for ano_hist in anos_disponiveis:
        bloco = dados[
            (dados["NU_ANO"] == ano_hist)
            & (dados["APLICACAO"] == "Regular")
            & (dados["SG_AREA"] == area_selecionada)
        ]
        if bloco.empty:
            continue
        cores_ano = sorted(bloco["TX_COR"].dropna().unique().tolist()) if "TX_COR" in bloco.columns else []
        cor_ano = _escolher_cor(cores_ano)
        bloco = bloco[bloco["TX_COR"] == cor_ano] if cores_ano else bloco
        if area_selecionada == "LC" and "TP_LINGUA" in bloco.columns and idioma_selecionado:
            bloco = bloco.copy()
            codigo_idioma_hist = {"Inglês": 0, "Espanhol": 1}[idioma_selecionado]
            bloco["TP_LINGUA"] = pd.to_numeric(bloco["TP_LINGUA"], errors="coerce")
            bloco = bloco[bloco["TP_LINGUA"].isna() | (bloco["TP_LINGUA"] == codigo_idioma_hist)]
        linhas_historico.append(bloco)

    fig_total = _grafico_incidencia(pd.concat(linhas_historico, ignore_index=True)) if linhas_historico else None
    if fig_total is not None:
        st.plotly_chart(fig_total, use_container_width=True)
    else:
        st.info("Não há dados suficientes para montar o gráfico de incidência total.")
