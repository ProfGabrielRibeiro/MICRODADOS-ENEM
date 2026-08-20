# 📐 Questões ENEM · Matemática

App em Streamlit para explorar os microdados dos **itens da prova de
Matemática** do ENEM (dificuldade, discriminação, habilidades cobertas,
gabaritos etc.), com filtros, gráficos e exportação em CSV.

## Como rodar localmente

1. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

2. Este projeto já vem com `dados/ITENS_PROVA_2025.csv`. Para adicionar
   outros anos, baixe os microdados do ENEM no site oficial do INEP:

   https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem

   Dentro do `.zip` de cada ano, pegue o arquivo:

   ```
   DADOS/ITENS_PROVA_AAAA.csv
   ```

3. Coloque esse(s) arquivo(s) — pode ter vários anos — dentro da pasta
   `dados/` deste projeto (mantendo o ano no nome do arquivo, que é de
   onde o app extrai `NU_ANO`). Também é possível enviá-los diretamente
   pelo painel de upload dentro do próprio app, sem mexer em pastas.

4. Rode o app:

   ```bash
   streamlit run app.py
   ```

Se nenhum arquivo real for encontrado, o app carrega automaticamente um
conjunto de **dados de exemplo** (fictícios) só para você conferir o
layout antes de plugar os dados reais.

## Publicar gratuitamente (como o exemplo que você mencionou)

1. Suba esta pasta para um repositório no GitHub (pode subir os CSVs
   também, se não forem muito grandes, ou deixar o upload manual).
2. Acesse https://streamlit.io/cloud, conecte sua conta do GitHub e
   aponte para o repositório, arquivo `app.py`.
3. Em alguns minutos você tem um link público, tipo
   `seu-app.streamlit.app`.

## Estrutura do projeto

```
enem_app/
├── app.py              # aplicação Streamlit
├── requirements.txt    # dependências
├── dados/              # coloque aqui os ITENS_PROVA_AAAA.csv
└── README.md
```

## Personalização

O código foi escrito para se adaptar às colunas que existirem no CSV —
se alguma coluna esperada não estiver presente, o filtro ou gráfico
correspondente simplesmente é desativado, sem quebrar o app. Isso é
útil porque o layout de `ITENS_PROVA` mudou um pouco ao longo dos anos.

Pontos fáceis de customizar em `app.py`:

- `EIXOS_MATEMATICA`: nomes dos eixos temáticos (ajuste se o INEP mudar
  os códigos).
- Faixas de `NIVEL_DIFICULDADE` (função `tratar_dados`).
- Cores dos gráficos (parâmetro `color_discrete_sequence` de cada
  `px.*`).
