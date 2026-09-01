"""
Gera o PDF de reforço: mostra as habilidades que o aluno errou, as questões
extras de outras edições pra treinar cada uma, e o gabarito dessas questões
extras no final.

Uso típico (dentro do app.py, depois de rodar correcao.corrigir(...) e
correcao.selecionar_questoes_reforco(...)):

    from gerar_pdf_reforco import gerar_pdf

    pdf_bytes = gerar_pdf(
        resultado_correcao=resultado,       # o que corrigir() devolveu
        blocos_reforco=blocos,              # o que selecionar_questoes_reforco() devolveu
        carregar_imagem=minha_funcao_de_download,  # bytes de uma questão a partir da entrada do manifest
        nome_aluno="Fulano de Tal",          # opcional
        logo_path="assets/logo_fenix.png",   # opcional -- None usa um espaço reservado
    )
    # pdf_bytes já vem pronto pra oferecer como st.download_button
"""
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether,
)
from PIL import Image as PILImage

FENIX_AZUL = colors.HexColor("#39A2DB")
FENIX_TEXTO = colors.HexColor("#1A1A1A")
FENIX_FUNDO = colors.HexColor("#F0F7FC")

MAX_LARGURA_IMG = 15.5 * cm  # cabe na largura útil de uma página A4 com margens
MAX_ALTURA_IMG = 22 * cm  # deixa espaço pro rótulo acima, numa página A4


def _estilos():
    base = getSampleStyleSheet()
    estilos = {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Title"], textColor=FENIX_TEXTO, fontSize=18,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=base["Normal"], textColor=FENIX_AZUL,
            fontSize=12, spaceAfter=4,
        ),
        "secao": ParagraphStyle(
            "secao", parent=base["Heading2"], textColor=colors.white,
            backColor=FENIX_AZUL, fontSize=13, spaceBefore=14, spaceAfter=10,
            leftIndent=8, borderPadding=(6, 6, 6, 6),
        ),
        "habilidade": ParagraphStyle(
            "habilidade", parent=base["Heading3"], textColor=FENIX_AZUL,
            fontSize=12, spaceBefore=10, spaceAfter=4,
        ),
        "corpo": base["Normal"],
        "legenda": ParagraphStyle(
            "legenda", parent=base["Normal"], fontSize=9,
            textColor=colors.grey, spaceAfter=10,
        ),
    }
    return estilos


def _logo_flowable(logo_path):
    if logo_path:
        try:
            img = PILImage.open(logo_path)
            largura_alvo = 4 * cm
            proporcao = img.height / img.width
            return Image(logo_path, width=largura_alvo, height=largura_alvo * proporcao)
        except Exception:
            pass
    # placeholder simples caso ainda não tenhamos o logo real
    tabela = Table([["FÊNIX\nVESTIBULARES"]], colWidths=[4 * cm], rowHeights=[2 * cm])
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FENIX_AZUL),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
    ]))
    return tabela


def _imagem_questao_flowable(imagem_bytes):
    pil_img = PILImage.open(io.BytesIO(imagem_bytes))
    largura, altura = pil_img.size
    escala = min(1.0, MAX_LARGURA_IMG / largura, MAX_ALTURA_IMG / altura)
    return Image(io.BytesIO(imagem_bytes), width=largura * escala, height=altura * escala)


def gerar_pdf(resultado_correcao, blocos_reforco, carregar_imagem,
              nome_aluno=None, edicao_label=None, logo_path=None):
    """
    carregar_imagem: função que recebe uma entrada do manifest (dict) e
    devolve os bytes .png da imagem (local ou baixada do R2 -- quem decide
    isso é a função que você passar aqui).
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
    )
    E = _estilos()
    story = []

    # --- Cabeçalho ---
    story.append(_logo_flowable(logo_path))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Relatório de correção e reforço", E["titulo"]))
    if edicao_label:
        story.append(Paragraph(edicao_label, E["subtitulo"]))
    if nome_aluno:
        story.append(Paragraph(f"Aluno(a): {nome_aluno}", E["corpo"]))
    story.append(HRFlowable(width="100%", color=FENIX_AZUL, thickness=1.2, spaceAfter=12))

    # --- Resumo do desempenho ---
    acertos = resultado_correcao["acertos"]
    total = resultado_correcao["total"]
    pct = (acertos / total * 100) if total else 0
    story.append(Paragraph(
        f"Você acertou <b>{acertos} de {total}</b> questões ({pct:.0f}%).",
        E["corpo"],
    ))
    story.append(Spacer(1, 10))

    habilidades_erradas = resultado_correcao["habilidades_erradas"]
    if not habilidades_erradas:
        story.append(Paragraph(
            "Parabéns! Você não errou nenhuma questão associada a uma "
            "habilidade específica neste caderno.", E["corpo"],
        ))
        doc.build(story)
        return buf.getvalue()

    story.append(Paragraph("Habilidades a reforçar", E["secao"]))
    linhas = [["Área", "Habilidade", "Competência", "Erros"]]
    for h in habilidades_erradas:
        linhas.append([h["area"], h["habilidade"], h["competencia"], f'{h["erros"]}/{h["total"]}'])
    tabela_resumo = Table(linhas, colWidths=[1.8 * cm, 2.2 * cm, 9 * cm, 2 * cm])
    tabela_resumo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FENIX_FUNDO),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(tabela_resumo)
    story.append(PageBreak())

    # --- Questões extras, uma seção por habilidade ---
    gabarito_extras = []  # pra tabela final
    for bloco in blocos_reforco:
        titulo = f'{bloco["area"]} · {bloco["habilidade"]} · {bloco["competencia"]}'
        story.append(Paragraph(titulo, E["secao"]))

        if not bloco["questoes"]:
            story.append(Paragraph(
                "Não encontramos questões extras suficientes dessa "
                "habilidade em outras edições.", E["corpo"],
            ))
            continue

        for entrada in bloco["questoes"]:
            rotulo = f'ENEM {entrada["ano"]} · Questão {entrada["questao_caderno"]}'
            imagem_bytes = carregar_imagem(entrada)
            elementos = [
                Paragraph(rotulo, E["habilidade"]),
                _imagem_questao_flowable(imagem_bytes),
                Spacer(1, 8),
            ]
            story.append(KeepTogether(elementos))

            gabarito_extras.append({
                "rotulo": rotulo,
                "area": bloco["area"],
                "habilidade": bloco["habilidade"],
                "gabarito": entrada.get("gabarito"),
            })

    # --- Gabarito das questões extras (só no final, pra não entregar de graça) ---
    story.append(PageBreak())
    story.append(Paragraph("Gabarito das questões extras", E["secao"]))
    linhas = [["Questão", "Área", "Habilidade", "Resposta correta"]]
    for g in gabarito_extras:
        linhas.append([g["rotulo"], g["area"], g["habilidade"], g["gabarito"]])
    tabela_gabarito = Table(linhas, colWidths=[6.5 * cm, 2 * cm, 2.5 * cm, 3.5 * cm])
    tabela_gabarito.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FENIX_FUNDO),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(tabela_gabarito)

    doc.build(story)
    return buf.getvalue()
