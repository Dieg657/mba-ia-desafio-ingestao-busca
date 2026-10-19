# Perguntas sobre um PDF, com LangChain e Postgres

Este repositório lê um PDF, guarda os trechos como vetores no PostgreSQL e responde perguntas no terminal. A resposta sai somente dos trechos recuperados. Se a informação não estiver nesses trechos, a frase é sempre:

`Não tenho informações necessárias para responder sua pergunta.`

## Caminho dos dados

```
document.pdf
    │  PyPDFLoader
    ▼
34 páginas
    │  cortes de 1000 caracteres, 150 de sobreposição
    ▼
67 trechos
    │  text-embedding-3-small
    ▼
Postgres + pgvector  (collection mba_docs)

pergunta no terminal
    │  o mesmo modelo de embedding
    ▼
10 trechos mais próximos
    │  prompt fixo + gpt-5-nano
    ▼
resposta
```

A LLM não recebe o PDF inteiro. Ela recebe os 10 trechos mais próximos da pergunta e as regras que impedem o uso de conhecimento de fora do documento.

## Antes de começar

- Python 3.13
- Docker com o plugin Compose
- Chave da OpenAI com saldo em [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

O projeto usa só a OpenAI. O embedding é `text-embedding-3-small`. O chat é `gpt-5-nano`.

## Preparação

Crie o ambiente e instale as dependências fixadas:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copie o modelo de ambiente e preencha a chave:

```bash
cp .env.example .env
```

| Variável | Função |
|---|---|
| `OPENAI_API_KEY` | Chave da API. É o único valor que você precisa colocar. |
| `OPENAI_EMBEDDING_MODEL` | Modelo que gera os vetores. Aqui, `text-embedding-3-small`. |
| `OPENAI_MODEL` | Modelo que redige a resposta. Aqui, `gpt-5-nano`. |
| `DATABASE_URL` | Conexão `postgresql+psycopg://postgres:postgres@localhost:5432/rag`. |
| `PG_VECTOR_COLLECTION_NAME` | Nome da collection. Aqui, `mba_docs`. |
| `PDF_PATH` | Caminho do PDF a partir da raiz do projeto. |

O `.env` está no `.gitignore`. Ele fica só na sua máquina.

Suba o banco:

```bash
docker compose up -d
```

O Compose sobe o PostgreSQL 17 com a imagem `pgvector/pgvector` e cria a extensão `vector`. O container `postgres_rag` precisa aparecer saudável:

```bash
docker compose ps
```

## Uso

Ingestão, uma vez por PDF ou depois de trocar o arquivo:

```bash
python src/ingest.py
```

Saída esperada:

```
PDF lido: 34 páginas em document.pdf
Recorte: 67 trechos de 1000 caracteres, com 150 de sobreposição
Gravação concluída: 67 trechos na collection mba_docs
```

Chat:

```bash
python src/chat.py
```

## Sessão de exemplo

```
Perguntas sobre o PDF. A resposta usa só o que foi recuperado do banco.
Encerre com sair, ou com Ctrl+C.

PERGUNTA: Qual o faturamento da Empresa SuperTechIABrazil?
RESPOSTA: R$ 10.000.000,00

PERGUNTA: Qual o faturamento da Alfa Telecom LTDA?
RESPOSTA: R$ 80.272.365,43

PERGUNTA: Em que ano foi fundada a Alfa Energia S.A.?
RESPOSTA: 1972

PERGUNTA: Quantos clientes temos em 2024?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.

PERGUNTA: sair
Encerrado.
```

## Arquivos

```
├── docker-compose.yml    # Postgres 17 e a extensão vector
├── requirements.txt      # pacotes com versão travada
├── .env.example          # variáveis sem segredo
├── document.pdf          # documento ingerido
├── src/
│   ├── ingest.py         # PDF, recorte, embeddings e gravação
│   ├── search.py         # busca dos 10 trechos, prompt e LLM
│   └── chat.py           # loop do terminal
└── README.md
```

## Escolhas deste repositório

O enunciado pede cortes de 1000 caracteres, com 150 de sobreposição, e uma busca dos 10 trechos mais próximos. Eu segui isso. A sobreposição existe porque o corte não olha o sentido da frase: se uma informação fica bem na divisa de dois pedaços, um pouco dela se repete no pedaço seguinte e a busca ainda consegue achar. Os 10 trechos chegam juntos para o modelo. Ele lê o que está escrito e monta a resposta a partir daí.

Para abrir o PDF, usei o `PyPDFLoader`, que é o carregador sugerido no desafio. Cada página vira um documento, e o recorte leva essa informação junto.

Toda vez que eu rodo a ingestão, a collection é apagada antes de gravar de novo (`pre_delete_collection=True`). Se eu deixasse os vetores antigos, a segunda execução duplicaria tudo e a busca dos 10 trechos perderia espaço com cópias. A consulta só lê. Ela não mexe no que já está salvo.

No chat eu fiquei com o `gpt-5-nano` e `reasoning_effort="low"`. É o modelo de conversa mais barato que ainda respondeu certo neste PDF. Com o esforço `minimal`, ele dizia que não sabia mesmo quando a resposta estava no documento. Com `low`, as perguntas do exemplo voltaram com o valor certo, e as que estão fora do PDF caíram na frase pedida. O modelo de embedding continua o mesmo, então eu não precisei ingerir o arquivo outra vez.

## Resultados

Fui testando uma configuração de cada vez. O embedding foi sempre `text-embedding-3-small`. O que mudou foi o modelo de chat e o esforço de raciocínio.

**`gpt-6-luna` sem temperatura.** A pergunta do PDF veio certa e a pergunta de fora caiu na frase do enunciado:

```
PERGUNTA: Qual o faturamento da Empresa SuperTechIABrazil?
RESPOSTA: R$ 10.000.000,00

PERGUNTA: Quantos clientes temos em 2024?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.
```

**`gpt-6-luna` com `temperature=0` e `reasoning_effort="none"`.** Com o raciocínio desligado, a temperatura zero passou. O resultado foi o mesmo das duas perguntas acima.

**`gpt-5-nano` com `reasoning_effort="minimal"`.** A API aceitou, mas o modelo recusou até o que estava escrito no PDF:

```
PERGUNTA: Qual o faturamento da Empresa SuperTechIABrazil?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.

PERGUNTA: Quantos clientes temos em 2024?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.

PERGUNTA: Qual é a capital da França?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.
```

**`gpt-4.1-nano` com `temperature=0`.** Esse aceita temperatura direto e respondeu certo. Eu não fiquei com ele porque o `gpt-5-nano` custa menos na entrada e, no ajuste seguinte, também acertou:

```
PERGUNTA: Qual o faturamento da Empresa SuperTechIABrazil?
RESPOSTA: R$ 10.000.000,00

PERGUNTA: Quantos clientes temos em 2024?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.
```

**`gpt-5-nano` com `reasoning_effort="low"`.** Esta é a configuração que ficou no projeto. As perguntas de dentro do PDF voltaram com o número do documento, e a de fora ficou na frase obrigatória:

```
PERGUNTA: Qual o faturamento da Empresa SuperTechIABrazil?
RESPOSTA: R$ 10.000.000,00

PERGUNTA: Qual o faturamento da Alfa Telecom LTDA?
RESPOSTA: R$ 80.272.365,43

PERGUNTA: Em que ano foi fundada a Alfa Energia S.A.?
RESPOSTA: 1972

PERGUNTA: Quantos clientes temos em 2024?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.
```

Rodei as mesmas duas perguntas no `gpt-6-luna`, com o raciocínio desligado, em quatro temperaturas: 0, 0,7, 1,3 e 2.

**Temperatura 0.** A resposta do faturamento veio só com o valor, sem frase em volta. A pergunta de clientes em 2024 ficou na frase de quem não achou a informação no PDF.

```
PERGUNTA: Qual o faturamento da Empresa SuperTechIABrazil?
RESPOSTA: R$ 10.000.000,00

PERGUNTA: Quantos clientes temos em 2024?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.
```

**Temperatura 0,7.** O faturamento continuou o mesmo, mas o modelo escreveu uma frase inteira em vez de soltar só o número. A pergunta de fora do PDF não escapou.

```
PERGUNTA: Qual o faturamento da Empresa SuperTechIABrazil?
RESPOSTA: O faturamento da SuperTechIABrazil é R$ 10.000.000,00.

PERGUNTA: Quantos clientes temos em 2024?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.
```

**Temperatura 1,3.** Voltou ao número seco, igual na temperatura 0. A pergunta de 2024 de novo caiu na frase obrigatória.

```
PERGUNTA: Qual o faturamento da Empresa SuperTechIABrazil?
RESPOSTA: R$ 10.000.000,00

PERGUNTA: Quantos clientes temos em 2024?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.
```

**Temperatura 2.** No teto da faixa, a resposta do faturamento ficou na frase completa de novo, com o mesmo valor. A pergunta que não está no documento continuou recusada.

```
PERGUNTA: Qual o faturamento da Empresa SuperTechIABrazil?
RESPOSTA: O faturamento da SuperTechIABrazil é R$ 10.000.000,00.

PERGUNTA: Quantos clientes temos em 2024?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.
```

## Se algo falhar

**Toda pergunta cai na frase de falta de informação.** A collection pode estar vazia. Rode `python src/ingest.py` e só depois abra o chat.

**A mensagem de inicialização do chat aparece na hora.** Falta variável no `.env` ou o Postgres não está aceitando conexão em `localhost:5432`. O texto logo acima dessa mensagem indica qual dos dois aconteceu.

**A ingestão quebra depois de trocar o modelo de embedding.** A coluna de vetor nasce com a dimensão do primeiro modelo. O `text-embedding-3-small` usa 1536. Para outro modelo, apague o volume e ingira de novo:

```bash
docker compose down -v
docker compose up -d
python src/ingest.py
```

**A porta 5432 já está ocupada.** Outro Postgres está no mesmo endereço. Pare esse serviço ou mude a porta publicada no `docker-compose.yml` e o host do `DATABASE_URL`.

<details>
<summary>Enunciado do desafio</summary>

## Objetivo

Entregar um software capaz de:

- Ingestão: ler um PDF e salvar o conteúdo em PostgreSQL com a extensão pgVector.
- Busca: responder perguntas no terminal usando apenas o conteúdo do PDF.

## Tecnologias obrigatórias

- Python
- LangChain
- PostgreSQL + pgVector
- Docker e Docker Compose para o banco

## Requisitos

### Ingestão

- Dividir o PDF em trechos de 1000 caracteres com sobreposição de 150.
- Converter cada trecho em embedding.
- Guardar os vetores no PostgreSQL com pgVector.

### Consulta

Ao receber uma pergunta:

- Vetorizar a pergunta.
- Buscar os 10 resultados mais próximos (`k=10`).
- Montar o prompt e chamar a LLM.
- Retornar a resposta ao usuário.

Prompt:

```
CONTEXTO:
{resultados concatenados do banco de dados}

REGRAS:
- Responda somente com base no CONTEXTO.
- Se a informação não estiver explicitamente no CONTEXTO, responda:
  "Não tenho informações necessárias para responder sua pergunta."
- Nunca invente ou use conhecimento externo.
- Nunca produza opiniões ou interpretações além do que está escrito.

EXEMPLOS DE PERGUNTAS FORA DO CONTEXTO:
Pergunta: "Qual é a capital da França?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Quantos clientes temos em 2024?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Você acha isso bom ou ruim?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

PERGUNTA DO USUÁRIO:
{pergunta do usuário}

RESPONDA A "PERGUNTA DO USUÁRIO"
```

## Entregável

Repositório público no GitHub com o código-fonte e um README que explique como executar o projeto.

</details>
