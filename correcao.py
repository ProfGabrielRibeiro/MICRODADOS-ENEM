"""
Lógica de correção do gabarito do aluno + seleção de questões de reforço.

Depende do manifest.json (o índice de questões que já geramos) para:
1. Saber o gabarito real de cada questão do caderno que o aluno fez.
2. Buscar questões extras de OUTRAS edições que cubram a mesma habilidade.

Não depende de Streamlit -- é lógica pura, fácil de testar sozinha.
"""
import random
from collections import defaultdict

N_EXTRAS_POR_HABILIDADE = 3  # decidido: 3 questões extras por habilidade errada


def questoes_da_area(manifest, ano, area, lingua=None):
    """Retorna as entradas do manifest para uma área específica dentro de
    um ano (ex: ano=2022, area="CH" -> as 45 questões de Humanas daquele
    ano), já ordenadas pela posição impressa no caderno.

    Essa é a mesma granularidade que o app.py já usa pros filtros normais
    (Edição + Área), então não precisa saber em qual "dia" cada área caiu
    -- isso muda de ano pra ano (ver HANDOFF.md) e essa função já abstrai
    isso.

    lingua: "ING" ou "ESP" -- necessário só quando area="LC", porque o
    manifest guarda as DUAS versões das questões de língua estrangeira
    impressas no caderno, mas o aluno só respondeu a que ele escolheu.
    """
    entradas = []
    for e in manifest:
        if e["ano"] != ano or e.get("area") != area:
            continue
        if e.get("lingua") is not None and e.get("lingua") != lingua:
            continue
        entradas.append(e)
    entradas.sort(key=lambda e: e["questao_caderno"])
    return entradas


def corrigir(manifest, ano, area, respostas_aluno, lingua=None):
    """
    respostas_aluno: dict {questao_caderno: "A"/"B"/"C"/"D"/"E"}
    lingua: "ING" ou "ESP" -- a língua estrangeira escolhida pelo aluno
            (obrigatório quando area="LC"; veja questoes_da_area)

    Retorna um dicionário com:
      - acertos: int
      - total: int
      - por_questao: lista de {questao_caderno, area, habilidade, competencia,
                                 gabarito, resposta_aluno, acertou}
      - habilidades_erradas: lista de {area, habilidade, competencia, erros, total}
    """
    caderno = questoes_da_area(manifest, ano, area, lingua=lingua)

    por_questao = []
    contagem_habilidade = defaultdict(lambda: {"erros": 0, "total": 0})

    for entrada in caderno:
        q = entrada["questao_caderno"]
        gabarito = entrada.get("gabarito")
        habilidade = entrada.get("habilidade")
        area = entrada.get("area")
        if gabarito in (None, "X"):
            # questão anulada -- não entra na correção
            continue
        resposta = respostas_aluno.get(q)
        acertou = (resposta == gabarito)

        por_questao.append({
            "questao_caderno": q,
            "area": area,
            "habilidade": habilidade,
            "competencia": entrada.get("competencia"),
            "gabarito": gabarito,
            "resposta_aluno": resposta,
            "acertou": acertou,
        })

        if habilidade:
            chave = (area, habilidade)
            contagem_habilidade[chave]["total"] += 1
            contagem_habilidade[chave]["competencia"] = entrada.get("competencia")
            if not acertou:
                contagem_habilidade[chave]["erros"] += 1

    acertos = sum(1 for p in por_questao if p["acertou"])
    total = len(por_questao)

    habilidades_erradas = []
    for (area, habilidade), info in contagem_habilidade.items():
        if info["erros"] > 0:
            habilidades_erradas.append({
                "area": area,
                "habilidade": habilidade,
                "competencia": info["competencia"],
                "erros": info["erros"],
                "total": info["total"],
            })
    # ordena por área e depois por número da habilidade (H1, H2, ...)
    habilidades_erradas.sort(key=lambda h: (h["area"], int(h["habilidade"][1:])))

    return {
        "acertos": acertos,
        "total": total,
        "por_questao": por_questao,
        "habilidades_erradas": habilidades_erradas,
    }


def selecionar_questoes_reforco(manifest, habilidades_erradas, ano_excluir,
                                  n_por_habilidade=N_EXTRAS_POR_HABILIDADE, seed=None,
                                  lingua=None):
    """
    Para cada habilidade errada, seleciona N questões de OUTRAS edições
    (exclui o próprio ano em que o aluno acabou de fazer essa área),
    priorizando variedade de anos em vez de pegar várias do mesmo ano.

    lingua: mesma língua estrangeira escolhida pelo aluno na correção --
    evita escolher a mesma questão duas vezes (uma em inglês, outra em
    espanhol) como se fossem duas questões extras diferentes.

    Retorna: lista de {area, habilidade, competencia, questoes: [entradas do manifest]}
    """
    rng = random.Random(seed)
    resultado = []

    for h in habilidades_erradas:
        candidatas = [
            e for e in manifest
            if e.get("area") == h["area"]
            and e.get("habilidade") == h["habilidade"]
            and e.get("gabarito") not in (None, "X")
            and e["ano"] != ano_excluir
            and (e.get("lingua") is None or e.get("lingua") == lingua)
        ]

        # agrupa por ano pra garantir variedade (no máx. 1 questão por ano
        # até esgotar os anos disponíveis, só repete ano se precisar)
        por_ano = defaultdict(list)
        for c in candidatas:
            por_ano[c["ano"]].append(c)
        for lst in por_ano.values():
            rng.shuffle(lst)

        anos_disponiveis = list(por_ano.keys())
        rng.shuffle(anos_disponiveis)

        escolhidas = []
        while len(escolhidas) < n_por_habilidade and any(por_ano[a] for a in anos_disponiveis):
            for a in anos_disponiveis:
                if por_ano[a] and len(escolhidas) < n_por_habilidade:
                    escolhidas.append(por_ano[a].pop())

        resultado.append({
            "area": h["area"],
            "habilidade": h["habilidade"],
            "competencia": h["competencia"],
            "questoes": escolhidas,
        })

    return resultado
