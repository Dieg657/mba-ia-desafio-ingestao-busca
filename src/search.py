import os

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector

load_dotenv()

PROMPT_TEMPLATE = """
CONTEXTO:
{contexto}

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
{pergunta}

RESPONDA A "PERGUNTA DO USUÁRIO"
"""


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def search_prompt(question=None):
    try:
        embeddings = OpenAIEmbeddings(model=require_env("OPENAI_EMBEDDING_MODEL"))
        vector_store = PGVector(
            embeddings=embeddings,
            collection_name=require_env("PG_VECTOR_COLLECTION_NAME"),
            connection=require_env("DATABASE_URL"),
            use_jsonb=True,
        )
        # gpt-5-nano é o modelo mais barato que pode seguir o contexto do PDF.
        # "minimal" esforço recusa respostas dentro do contexto; "low" não.
        llm = ChatOpenAI(
            model=require_env("OPENAI_MODEL"),
            temperature=0,
            reasoning_effort="low",
        )
    except Exception as exc:
        print(f"Erro ao inicializar a busca: {exc}")
        return None

    prompt = PromptTemplate.from_template(PROMPT_TEMPLATE)

    def build_context(user_question: str) -> str:
        results = vector_store.similarity_search_with_score(user_question, k=10)
        return "\n\n".join(document.page_content for document, _score in results)

    chain = (
        {
            "contexto": RunnableLambda(build_context),
            "pergunta": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    if question:
        return chain.invoke(question)
    return chain
