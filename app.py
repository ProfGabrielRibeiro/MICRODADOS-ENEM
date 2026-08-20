"""
Explorador de Questões — ENEM (Microdados de Itens)
=====================================================
App Streamlit enxuto, no estilo do questoesenem.streamlit.app: escolha
o ano e a prova, e veja a
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
import plotly.graph_objects as go
import streamlit as st

# ------------------------------------------------------------------
# Configuração da página
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Fênix Vestibulares · Questões ENEM",
    page_icon="🔥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "dados")
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo_fenix.png")

# Cores extraídas da identidade visual da Fênix Vestibulares (botões e logo do site oficial)
FENIX_AZUL = "#39A2DB"
FENIX_AZUL_ESCURO = "#2B85B8"
FENIX_TEXTO = "#1A1A1A"
FENIX_FUNDO_SECUNDARIO = "#F0F7FC"


def _aplicar_identidade_visual():
    """Injeta a fonte e as cores da marca Fênix — fundo branco, azul nos
    botões e destaques, no mesmo formato usado no site oficial."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Inter:wght@400;500&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}
        h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
            font-family: 'Poppins', sans-serif !important;
            font-weight: 600 !important;
            color: {FENIX_TEXTO} !important;
        }}
        /* botões de rádio (Prova / Idioma) selecionados em azul, como no site */
        div[role="radiogroup"] label div:first-child {{
            border-color: {FENIX_AZUL} !important;
        }}
        div[role="radiogroup"] label div:first-child > div {{
            background-color: {FENIX_AZUL} !important;
        }}
        /* botões de ação (download etc.) no estilo sólido arredondado do site */
        .stButton > button, .stDownloadButton > button {{
            background-color: {FENIX_AZUL} !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-family: 'Poppins', sans-serif !important;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
            background-color: {FENIX_AZUL_ESCURO} !important;
        }}
        .fenix-tagline {{
            font-family: 'Poppins', sans-serif;
            font-style: italic;
            font-weight: 600;
            font-size: 1.15rem;
            color: {FENIX_AZUL};
            text-align: center;
            margin-top: 0.2rem;
            margin-bottom: 0.8rem;
        }}
        .fenix-rodape {{
            text-align: right;
            color: #9AA0A6;
            font-size: 0.8rem;
            margin-top: 1.5rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


_aplicar_identidade_visual()

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
# Tema claro, no estilo do site oficial da Fênix
# ------------------------------------------------------------------
def _garantir_tema_claro():
    config_dir = os.path.join(os.path.dirname(__file__), ".streamlit")
    config_path = os.path.join(config_dir, "config.toml")
    if not os.path.exists(config_path):
        os.makedirs(config_dir, exist_ok=True)
        with open(config_path, "w") as f:
            f.write(
                "[theme]\nbase = \"light\"\nprimaryColor = \"#39A2DB\"\n"
                "backgroundColor = \"#FFFFFF\"\nsecondaryBackgroundColor = \"#F0F7FC\"\n"
                "textColor = \"#1A1A1A\"\n"
            )


_garantir_tema_claro()

# ------------------------------------------------------------------
# Grupos de CO_PROVA confirmados manualmente contra o gabarito oficial
# do INEP (comparação posição a posição). Sempre que uma combinação
# (ano, área) aparecer aqui, o app usa esse grupo diretamente como
# "Regular" em vez de tentar adivinhar pela heurística de contagem de
# cores/cadernos — que pode errar em caso de empate (como aconteceu
# em Ciências da Natureza 2024, onde dois grupos tinham a mesma
# quantidade de cores e o desempate por "mais cadernos" escolheu o
# grupo errado).
GRUPOS_VALIDADOS = {
    (2020, "LC"): [577, 578, 579, 580, 583, 584, 585],
    (2020, "CH"): [567, 568, 569, 570, 573, 574, 575],
    (2020, "CN"): [597, 598, 599, 600],
    (2020, "MT"): [587, 588, 589, 590],
    (2021, "LC"): [889, 890, 891, 892, 893, 894, 1003, 1004, 1005, 1006],
    (2021, "CH"): [879, 880, 881, 882, 883, 884, 885, 886, 887, 999, 1000, 1001, 1002],
    (2021, "CN"): [909, 910, 911, 912, 913, 914, 1011, 1012, 1013, 1014],
    (2021, "MT"): [899, 900, 901, 902, 903, 904, 907, 1007, 1008, 1009, 1010],
    (2022, "LC"): [1065, 1066, 1067, 1068, 1069, 1070, 1071, 1072, 1179, 1180, 1181, 1182],
    (2022, "CH"): [1055, 1056, 1057, 1058, 1059, 1060, 1061, 1062, 1063, 1175, 1176, 1177, 1178],
    (2022, "CN"): [1085, 1086, 1087, 1088, 1089, 1090, 1091, 1092, 1187, 1188, 1189, 1190],
    (2022, "MT"): [1075, 1076, 1077, 1078, 1079, 1080, 1083, 1183, 1184, 1185, 1186],
    (2023, "LC"): [1201, 1202, 1203, 1204, 1205, 1206, 1207, 1208, 1210],
    (2023, "CH"): [1191, 1192, 1193, 1194, 1195, 1196, 1197, 1198, 1199, 1200, 1311, 1312],
    (2023, "CN"): [1221, 1222, 1223, 1224, 1225, 1226],
    (2023, "MT"): [1211, 1212, 1213, 1214, 1215, 1216],
    (2024, "LC"): [1395, 1396, 1397, 1398, 1399, 1400, 1401, 1402, 1406],
    (2024, "CH"): [1383, 1384, 1385, 1386, 1387, 1388, 1389, 1390, 1391, 1392, 1393, 1394],
    (2024, "CN"): [1419, 1420, 1421, 1422, 1423, 1424],
    (2024, "MT"): [1407, 1408, 1409, 1410, 1411, 1412, 1415, 1416, 1417],
    (2025, "LC"): [1459, 1460, 1461, 1462, 1463, 1464, 1465, 1466, 1470, 1496],
    (2025, "CH"): [1447, 1448, 1449, 1450, 1451, 1452, 1453, 1454, 1455, 1456, 1457, 1458, 1495],
    (2025, "CN"): [1483, 1484, 1485, 1486],
    (2025, "MT"): [1471, 1472, 1473, 1474, 1479, 1480, 1481],
}


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
    """Para cada combinação (ano, área), usa o grupo de CO_PROVA já
    validado manualmente (GRUPOS_VALIDADOS) para a aplicação Regular.
    O grupo PPL/Reaplicação é identificado por heurística (o conjunto
    remanescente com mais cores/cadernos distintos) — como ainda não
    temos gabarito oficial de PPL pra validar, essa parte é uma
    aproximação, diferente da Regular que é 100% conferida."""
    chaves = {"NU_ANO", "SG_AREA", "CO_ITEM", "CO_PROVA"}
    if not chaves.issubset(dados.columns):
        dados = dados.copy()
        dados["APLICACAO"] = "Regular"
        return dados

    dados = dados.copy()
    dados["APLICACAO"] = pd.NA

    for (ano, area), bloco in dados.groupby(["NU_ANO", "SG_AREA"]):
        rotulos = {}

        grupos_por_prova = bloco.groupby("CO_PROVA")["CO_ITEM"].apply(lambda s: frozenset(s))
        conjuntos = set(grupos_por_prova.values)

        ranking = []
        for conjunto in conjuntos:
            provas_do_conjunto = [p for p, s in grupos_por_prova.items() if s == conjunto]
            n_cores = bloco[bloco["CO_PROVA"].isin(provas_do_conjunto)]["TX_COR"].nunique()
            ranking.append((n_cores, len(provas_do_conjunto), conjunto, provas_do_conjunto))
        ranking.sort(key=lambda t: (t[0], t[1]), reverse=True)

        chave_validada = GRUPOS_VALIDADOS.get((int(ano), area))
        if chave_validada is not None:
            # usa o grupo confirmado manualmente contra o gabarito oficial
            provas_presentes = set(bloco["CO_PROVA"].unique())
            provas_regular = [p for p in chave_validada if p in provas_presentes]
        else:
            provas_regular = ranking[0][3] if ranking else []

        for prova in provas_regular:
            rotulos[prova] = "Regular"

        # PPL/Reaplicação: maior grupo restante que não seja o Regular (heurística)
        provas_regular_set = set(provas_regular)
        for _, _, _, provas_do_conjunto in ranking:
            if set(provas_do_conjunto) & provas_regular_set:
                continue
            for prova in provas_do_conjunto:
                rotulos[prova] = "PPL/Reaplicação"
            break

        indices = dados.index[(dados["NU_ANO"] == ano) & (dados["SG_AREA"] == area)]
        dados.loc[indices, "APLICACAO"] = dados.loc[indices, "CO_PROVA"].map(rotulos)

    # descarta grupos além de Regular e PPL/Reaplicação (versões digitais/adaptadas extras)
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

    blocos = []
    for ano in anos_exemplo:
        for area in MATRIZES.keys():
            n_por_prova = 50 if area == "LC" else 45
            item_ids = rng.integers(100000, 999999, size=n_por_prova)
            for cor in cores_regular:
                blocos.append(pd.DataFrame({
                    "CO_ITEM": item_ids,
                    "SG_AREA": area,
                    "NU_ANO": ano,
                    "CO_PROVA": f"{ano}{area}REG{cor[:2]}",
                    "TX_COR": cor,
                    "APLICACAO": "Regular",
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
dados = carregar_dados_reais()
usando_exemplo = dados.empty
if usando_exemplo:
    dados = gerar_dados_exemplo()

# ------------------------------------------------------------------
# Cabeçalho — logo centralizada, no estilo do site oficial
# ------------------------------------------------------------------
_, col_logo_centro, _ = st.columns([1, 1.2, 1])
with col_logo_centro:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, use_container_width=True)

st.markdown("<p class='fenix-tagline'>O maior e melhor curso do RS!</p>", unsafe_allow_html=True)

st.markdown(
    "Consulte a habilidade e a dificuldade de cada uma das questões do ENEM "
    "dos últimos anos, conforme publicado nos microdados oficiais do INEP — "
    "um material de apoio organizado para o seu estudo."
)
if usando_exemplo:
    st.warning(
        "Nenhum microdado real encontrado — exibindo **dados de exemplo** "
        "(fictícios). Verifique se os arquivos ITENS_PROVA estão na pasta `dados/` do repositório."
    )

# ------------------------------------------------------------------
# Controles — Ano / Aplicação / Prova
# ------------------------------------------------------------------
anos_disponiveis = sorted(dados["NU_ANO"].dropna().unique().tolist(), reverse=True) if "NU_ANO" in dados.columns else []

st.markdown("**Ano da aplicação**")
ano_selecionado = st.selectbox("Ano da aplicação", options=anos_disponiveis, label_visibility="collapsed")

st.markdown("**Aplicação**")
aplicacao_selecionada = st.radio(
    "Aplicação",
    options=["Regular", "PPL/Reaplicação"],
    horizontal=True,
    label_visibility="collapsed",
)
if aplicacao_selecionada == "PPL/Reaplicação":
    st.caption(
        "⚠️ A separação de PPL/Reaplicação ainda é uma aproximação (sem gabarito oficial "
        "para validar) — pode conter imprecisões, diferente da aplicação Regular, que é 100% conferida."
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
    cores_disponiveis = [c for c in cores_disponiveis if c != "LEITOR TELA"]
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
    # Gráfico 3D de incidência das habilidades — Ano selecionado x Total histórico
    # ------------------------------------------------------------------
    def _contar_por_habilidade(dados_para_grafico: pd.DataFrame) -> dict:
        base = dados_para_grafico[dados_para_grafico["HABILIDADE_LABEL"].notna()]
        if base.empty:
            return {}
        contagem = base.groupby(["CO_HABILIDADE", "COMPETENCIA"]).size()
        resultado = {}
        for (hab, comp), n in contagem.items():
            resultado[int(hab)] = (int(n), comp)
        return resultado

    def _cuboide(x0, x1, y0, y1, z0, z1, cor, texto):
        """Um paralelepípedo (barra 3D) construído com 12 triângulos."""
        x = [x0, x1, x1, x0, x0, x1, x1, x0]
        y = [y0, y0, y1, y1, y0, y0, y1, y1]
        z = [z0, z0, z0, z0, z1, z1, z1, z1]
        i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
        j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
        k = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6]
        return go.Mesh3d(
            x=x, y=y, z=z, i=i, j=j, k=k,
            color=cor, opacity=1, flatshading=True,
            hovertext=texto, hoverinfo="text",
            showlegend=False,
        )

    # paleta fixa por competência (mesma cor nas duas fileiras do gráfico)
    todas_competencias = list(MATRIZES[area_selecionada]["competencias"].values())
    paleta = px.colors.qualitative.Set2 + px.colors.qualitative.Set3
    cor_por_competencia = {comp: paleta[i % len(paleta)] for i, comp in enumerate(todas_competencias)}

    contagem_ano = _contar_por_habilidade(filtrado)

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
        cores_ano = [c for c in cores_ano if c != "LEITOR TELA"]
        cor_ano = _escolher_cor(cores_ano)
        bloco = bloco[bloco["TX_COR"] == cor_ano] if cores_ano else bloco
        if area_selecionada == "LC" and "TP_LINGUA" in bloco.columns:
            bloco = bloco.copy()
            codigo_idioma_hist = {"Inglês": 0, "Espanhol": 1}.get(idioma_selecionado, 0)
            bloco["TP_LINGUA"] = pd.to_numeric(bloco["TP_LINGUA"], errors="coerce")
            bloco = bloco[bloco["TP_LINGUA"].isna() | (bloco["TP_LINGUA"] == codigo_idioma_hist)]
        linhas_historico.append(bloco)

    contagem_total = _contar_por_habilidade(pd.concat(linhas_historico, ignore_index=True)) if linhas_historico else {}

    st.divider()
    st.markdown(f"#### 📊 Incidência das habilidades (3D) — {MATRIZES[area_selecionada]['nome']}")
    st.caption(
        f"Fileira da frente: **Ano {int(ano_selecionado)}** ({aplicacao_selecionada}). Fileira de trás: "
        f"**total acumulado** de {int(min(anos_disponiveis))} a {int(max(anos_disponiveis))} (sempre aplicação Regular)"
        + (f", língua estrangeira: {idioma_selecionado}." if idioma_selecionado else ".")
        + " Arraste com o mouse pra girar o gráfico."
    )

    if not contagem_ano and not contagem_total:
        st.info("Não há dados suficientes para montar o gráfico de incidência.")
    else:
        largura_barra = 0.35
        traces = []
        legendas_usadas = set()
        for hab in range(1, 31):
            for linha_y, contagem in [(0, contagem_ano), (1, contagem_total)]:
                if hab not in contagem:
                    continue
                valor, competencia = contagem[hab]
                cor = cor_por_competencia.get(competencia, "#999999")
                texto = f"H{hab} · {competencia}<br>Incidência: {valor}"
                traces.append(_cuboide(
                    hab - largura_barra, hab + largura_barra,
                    linha_y - 0.35, linha_y + 0.35,
                    0, valor,
                    cor, texto,
                ))

        fig3d = go.Figure(data=traces)

        # traços "fantasma" só pra desenhar a legenda de competências
        for comp, cor in cor_por_competencia.items():
            fig3d.add_trace(go.Scatter3d(
                x=[None], y=[None], z=[None], mode="markers",
                marker=dict(size=8, color=cor), name=comp,
            ))

        fig3d.update_layout(
            scene=dict(
                xaxis=dict(title="Habilidade", tickmode="array", tickvals=list(range(1, 31)), ticktext=[f"H{i}" for i in range(1, 31)]),
                yaxis=dict(title="", tickmode="array", tickvals=[0, 1], ticktext=[f"Ano {int(ano_selecionado)}", "Total histórico"]),
                zaxis=dict(title="Incidência"),
            ),
            legend_title="Competência",
            margin=dict(l=0, r=0, t=10, b=0),
            height=560,
        )
        st.plotly_chart(fig3d, use_container_width=True)

st.markdown("<div class='fenix-rodape'>Desenvolvido por Gabriel Ribeiro</div>", unsafe_allow_html=True)
