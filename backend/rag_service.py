import os
import shutil
from typing import List
from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Make Google Gemini imports optional
try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
except Exception:
    GoogleGenerativeAIEmbeddings = None
    ChatGoogleGenerativeAI = None

# Use modern langchain-openai package
try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
except Exception:
    ChatOpenAI = None
    OpenAIEmbeddings = None
from langchain_community.vectorstores import Chroma
from langchain_classic.chains.retrieval_qa.base import RetrievalQA
from langchain_core.prompts import PromptTemplate
import tempfile
import logging

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

# Initialize global variables for persistence in this simple demo
# In a production app, you might want a more robust way to handle state or multiple sessions
vector_store = None
qa_chain = None

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def get_embeddings():
    # Prefer OpenAI embeddings if OPENAI_API_KEY is provided
    if OPENAI_API_KEY:
        if OpenAIEmbeddings is None:
            raise RuntimeError("OpenAIEmbeddings not available. Please install langchain-openai package.")
        return OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=OPENAI_API_KEY)

    # Otherwise try Gemini/Google embeddings
    if GEMINI_API_KEY:
        if GoogleGenerativeAIEmbeddings is None:
            raise RuntimeError("GoogleGenerativeAIEmbeddings not available. Please install langchain-google-genai.")
        return GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GEMINI_API_KEY)

    raise ValueError("No embedding API key available. Set OPENAI_API_KEY or GOOGLE_API_KEY in environment variables.")

def get_llm():
    # Prefer OpenAI chat model if key provided
    if OPENAI_API_KEY:
        if ChatOpenAI is None:
            raise RuntimeError("ChatOpenAI not available. Please install langchain-openai package.")
        return ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=OPENAI_API_KEY, temperature=0)

    if GEMINI_API_KEY:
        if ChatGoogleGenerativeAI is None:
            raise RuntimeError("ChatGoogleGenerativeAI not available. Please install langchain-google-genai.")
        # Using gemini-flash-latest for free tier access
        return ChatGoogleGenerativeAI(model="gemini-flash-latest", google_api_key=GEMINI_API_KEY, convert_system_message_to_human=True)

    raise ValueError("No LLM API key available. Set OPENAI_API_KEY or GOOGLE_API_KEY in environment variables.")

async def process_document(file: UploadFile):
    global vector_store, qa_chain
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name

    try:
        # Load Document
        if file.filename.endswith(".pdf"):
            loader = PyPDFLoader(temp_path)
            docs = loader.load()
        elif file.filename.endswith(".txt") or file.filename.endswith(".md"):
            loader = TextLoader(temp_path)
            docs = loader.load()
        else:
            raise ValueError("Unsupported file type. Please upload PDF, TXT, or MD.")

        # Chunking
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)

        # Create/Update Vector Store
        used_local = False
        try:
            embeddings = get_embeddings()
            # Try remote embeddings first
            vector_store = Chroma.from_documents(
                documents=splits,
                embedding=embeddings,
                persist_directory="./chroma_db",
            )
        except Exception as e:
            # If remote embeddings fail (quota, API error, etc.), fall back to local embeddings
            logging.exception("Remote embeddings failed: %s", e)
            if SentenceTransformer is None:
                raise RuntimeError("Remote embeddings failed and sentence-transformers is not installed.") from e

            class LocalEmbeddings:
                def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
                    self._model = SentenceTransformer(model_name)

                def embed_documents(self, texts: List[str]):
                    embs = self._model.encode(list(texts), show_progress_bar=False)
                    return [list(map(float, e)) for e in embs]

                def embed_query(self, text: str):
                    emb = self._model.encode([text])[0]
                    return list(map(float, emb))

            embeddings = LocalEmbeddings()
            used_local = True
            vector_store = Chroma.from_documents(
                documents=splits,
                embedding=embeddings,
                persist_directory="./chroma_db_local",
            )
        
        # Setup QA Chain
        retriever = vector_store.as_retriever(search_kwargs={"k": 5})
        llm = get_llm()
        
        prompt_template = """Use the following pieces of context to answer the question at the end. 
if you don't know the answer, just say that you don't know, don't try to make up an answer.

{context}

Question: {question}
Helpful Answer:"""
        PROMPT = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT}
        )
        
        return {"status": "success", "message": f"Processed {len(splits)} chunks."}

    finally:
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

def ask_question(question: str):
    global qa_chain
    if not qa_chain:
        return {"error": "No document uploaded yet. Please upload a document first."}
    
    result = qa_chain.invoke({"query": question})
    return {
        "answer": result["result"],
        "source_documents": [doc.page_content[:200] + "..." for doc in result["source_documents"]]
    }
