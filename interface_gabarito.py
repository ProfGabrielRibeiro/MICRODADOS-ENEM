"""
Tela do gabarito em branco -- o aluno marca A-E pra cada questão.

Reaproveita exatamente o CSS de "pills" que já existe no app.py
(_aplicar_identidade_visual), porque ele já estiliza qualquer
div[role="radiogroup"] -- inclusive os que a gente criar aqui.
Não precisa adicionar CSS novo, só chamar essa função depois de
_aplicar_identidade_visual() já ter rodado (ela roda uma vez, cedo,
no seu app.py atual).

Uso típico dentro do app.py:

    from interface_gabarito import tela_gabarito
    from correcao import corrigir, selecionar_questoes_reforco
    from gerar_pdf_reforco import gerar_pdf

    if st.checkbox("Enviar minhas respostas"):
        respostas, enviado = tela_gabarito(caderno_questoes, lingua=idioma_escolhido)
        if enviado:
            resultado = corrigir(manifest, ano, dia, respostas, lingua=idioma_escolhido)
            ... (mostrar resultado, oferecer o PDF pra download)
"""
import streamlit as st

LETRAS = ["A", "B", "C", "D", "E"]
N_COLUNAS = 5  # mais colunas = grade mais compacta

_CSS_GRADE_COMPACTA = """
<style>
.st-key-grade_gabarito div[role="radiogroup"] {
    gap: 4px;
}
.st-key-grade_gabarito div[role="radiogroup"] label {
    padding: 3px 8px !important;
    border-radius: 6px !important;
    border-width: 1.5px !important;
}
.st-key-grade_gabarito div[role="radiogroup"] label p {
    font-size: 0.8rem !important;
}
.st-key-grade_gabarito [data-testid="stWidgetLabel"] p {
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    margin-bottom: 2px !important;
}
</style>
"""


def tela_gabarito(entradas_caderno, lingua=None, key_prefix="gabarito"):
    """
    entradas_caderno: lista de entradas do manifest para o caderno
                       (já filtradas pela língua, se aplicável --
                       veja correcao.questoes_da_area)

    Retorna (respostas, enviado):
      respostas: dict {questao_caderno: "A".."E"} com o que foi
                 preenchido até agora (mesmo antes de enviar)
      enviado: True só no momento em que o aluno clica em Corrigir
    """
    st.markdown(_CSS_GRADE_COMPACTA, unsafe_allow_html=True)
    st.markdown("### Gabarito")
    st.caption(
        "Marque a alternativa escolhida em cada questão e clique em "
        "**Corrigir** no final."
    )

    respostas = {}
    with st.form(key=f"{key_prefix}_form"):
        with st.container(key="grade_gabarito"):
            colunas = st.columns(N_COLUNAS)
            for i, entrada in enumerate(entradas_caderno):
                q = entrada["questao_caderno"]
                col = colunas[i % N_COLUNAS]
                with col:
                    escolha = st.radio(
                        f"Q{q}",
                        LETRAS,
                        index=None,
                        horizontal=True,
                        key=f"{key_prefix}_{q}_{lingua or ''}",
                    )
                    if escolha:
                        respostas[q] = escolha

        st.markdown("")  # respiro antes do botão
        enviado = st.form_submit_button("Corrigir")

    if enviado:
        faltando = [e["questao_caderno"] for e in entradas_caderno
                    if e["questao_caderno"] not in respostas]
        if faltando:
            st.warning(
                f"Faltou marcar {len(faltando)} questão(ões): "
                f"{', '.join(str(q) for q in sorted(faltando))}. "
                "Você pode corrigir mesmo assim -- as que faltaram contam como erradas."
            )

    return respostas, enviado
