import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def resolve_pdf_path(pdf_path: str) -> Path:
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")
    return path


def ingest_pdf() -> None:
    pdf_path = resolve_pdf_path(require_env("PDF_PATH"))
    documents = PyPDFLoader(str(pdf_path)).load()
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    ).split_documents(documents)

    if not chunks:
        raise RuntimeError(f"No text chunks were produced from {pdf_path.name}")

    collection_name = require_env("PG_VECTOR_COLLECTION_NAME")
    embeddings = OpenAIEmbeddings(model=require_env("OPENAI_EMBEDDING_MODEL"))
    print(f"PDF lido: {len(documents)} páginas em {pdf_path.name}")
    print(f"Recorte: {len(chunks)} trechos de 1000 caracteres, com 150 de sobreposição")
    PGVector.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=collection_name,
        connection=require_env("DATABASE_URL"),
        pre_delete_collection=True,
        use_jsonb=True,
    )
    print(f"Gravação concluída: {len(chunks)} trechos na collection {collection_name}")


if __name__ == "__main__":
    ingest_pdf()
