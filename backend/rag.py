import logging
import streamlit as st
import tempfile
import os

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document

#from langchain.retrievers import ContextualCompressionRetriever
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

#from langchain_community.document_compressors import LLMChainExtractor

from langchain_community.vectorstores.utils import filter_complex_metadata

from unstructured.partition.pdf import partition_pdf
from unstructured.chunking.title import chunk_by_title

from dotenv import load_dotenv

load_dotenv() 
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatPDF:
    vector_store = None
    retriever = None
    chain = None
    
    def __init__(self):
        # self.model = ChatOllama(model="llama3.1:8b")
        self.model = ChatOpenAI(
            model="deepseek-chat", #"meta-llama/llama-4-maverick",  # OpenRouter model name
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),  # Your API key
            base_url="https://api.deepseek.com/v1",  # OpenRouter endpoint
            default_headers={
                "HTTP-Referer": "http://localhost:5000",  # Optional: Your site URL
                "X-Title": "Legal RAG Assistant",  # Optional: Your app name
            }
        )
        self.prompt = PromptTemplate.from_template(
            """
            You are a legal research assistant. Follow this plan:
            1) Extract timeline events, dates, amounts, identifiers with pin-cites.
            2) Enumerate objections/clauses/citations with pin-cites.
            3) Reconcile referenced sections/annexures; if missing, output a Missing-but-referenced note.
            4) Run a completeness checklist: timeline start→end, objections with all cited cases, clause refs quoted or flagged, ombudsman posture, non-joinder if applicable.
            5) Add confidence tags (High/Med/Low) based on redundancy and section type.

            For simple questions stick to giving really simple, 1-2 sentence concise answers, instead of giving a full description of the timeline and case. 
            Below are some question, answer example pairs:

            simple_question: On what date X thing happened,
            answer: X happened on Y date

            simple_question: How much money was given to X,
            answer: Y amount of money was given to X

            simple_question: Who is the buyer and seller,
            answer: Buyer: X, Seller: Y

            Do not overcomplicate these type of simple questions, just give what I am asking for.
            
            Always:
            - Use bullet points and short sections.
            - Add [page X] after each bullet when page_number is available; otherwise [page ?].
            - Never invent text not in context; if missing, state “Missing from provided context.”

            Question: {question}

            Context:
            {context}

            Answer:
                        """
                        
        )
        logger.info("ChatPDF initialized")

    def classify_query(self, query: str) -> dict:
        """
        Classify legal query and determine optimal retrieval parameters
        Returns: {"type": str, "k_value": int, "description": str}
        """
        query_lower = query.lower()
        
        # Factual extraction patterns - need fewer chunks
        factual_patterns = [
            "what was", "when did", "amount", "date", "number", "premium", 
            "policy number", "sum assured", "issue date", "lapse date",
            "payment history", "specific", "exactly"
        ]
        
        # Legal analysis patterns - need more chunks for comprehensive analysis  
        analysis_patterns = [
            "grounds for", "legal basis", "precedent", "arguments", "why",
            "dismiss", "reject", "defense", "liability", "breach",
            "key legal", "main reasons", "basis for"
        ]
        
        # Process/mechanism patterns - medium chunk count
        process_patterns = [
            "circumstances", "under what", "how can", "when can", "process",
            "procedure", "steps", "mechanism", "conditions", "requirements"
        ]
        
        # Check patterns in order of specificity
        if any(pattern in query_lower for pattern in factual_patterns):
            return {
                "type": "factual",
                "k_value": 8,
                "description": "Factual extraction - focused retrieval"
            }
        elif any(pattern in query_lower for pattern in analysis_patterns):
            return {
                "type": "analysis", 
                "k_value": 22,
                "description": "Legal analysis - comprehensive retrieval"
            }
        elif any(pattern in query_lower for pattern in process_patterns):
            return {
                "type": "process",
                "k_value": 15,
                "description": "Process/mechanism - moderate retrieval"
            }
        else:
            return {
                "type": "general",
                "k_value": 18,
                "description": "General query - balanced retrieval"
            }

    def create_dynamic_retriever(self, k_value: int):
        """Create retriever with dynamic k values based on query type"""
        
        # Adjust k values proportionally
        similarity_k = k_value
        mmr_k = max(int(k_value * 0.8), 5)  # Slightly less for MMR
        keyword_k = max(int(k_value * 0.8), 5)  # Match MMR
        mmr_fetch_k = k_value * 3  # Keep fetch_k ratio
        
        logger.info(f"Creating dynamic retriever with similarity_k={similarity_k}, mmr_k={mmr_k}, keyword_k={keyword_k}")
        
        # Enhanced temporal-aware retriever setup with dynamic k
        similarity_retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": similarity_k}
        )

        # MMR for diversity
        mmr_retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": mmr_k,
                "fetch_k": mmr_fetch_k,
                "lambda_mult": 0.5
            }
        )

        # Create new keyword retriever with dynamic k
        # (We need to recreate this since BM25Retriever k is set at initialization)
        processed_chunks = []
        if hasattr(self, '_processed_chunks'):
            processed_chunks = self._processed_chunks
        else:
            # Fallback - recreate from vector store (less efficient but works)
            logger.warning("Processed chunks not cached, may affect performance")
            
        keyword_retriever = BM25Retriever.from_documents(processed_chunks) if processed_chunks else None
        if keyword_retriever:
            keyword_retriever.k = keyword_k

        # Create ensemble with available retrievers
        retrievers = [similarity_retriever, mmr_retriever]
        weights = [0.6, 0.4]
        
        if keyword_retriever:
            retrievers.append(keyword_retriever)
            weights = [0.5, 0.3, 0.2]
        
        return EnsembleRetriever(
            retrievers=retrievers,
            weights=weights
        )

    def ingest(self, pdf_file_path: str):
        try:
            logger.info(f"Loading and partitioning PDF: {pdf_file_path}")
            elements = partition_pdf(
                filename=pdf_file_path,
                strategy="hi_res",
                model_name="yolox"
                # infer_table_structure=True,
                # extract_images_in_pdf=True
            )
            logger.info(f"Partitioned into {len(elements)} elements")

            # Perform smart chunking
            chunks = chunk_by_title(
                elements=elements,
                max_characters=1500,
                overlap = 400,
                combine_text_under_n_chars=75,
                new_after_n_chars=1200
            )
            logger.info(f"Chunked into {len(chunks)} semantic chunks")

            # Convert ElementMetadata to dictionary for compatibility
            processed_chunks = []
            for chunk in chunks:
                metadata = {}
                if hasattr(chunk, 'metadata') and chunk.metadata:
                    # Convert ElementMetadata to dict
                    metadata_dict = chunk.metadata.to_dict() if hasattr(chunk.metadata, 'to_dict') else {}
                    # Filter to simple types (strings, numbers, etc.)
                    for key, value in metadata_dict.items():
                        if isinstance(value, (str, int, float, bool, type(None))):
                            metadata[key] = value
                        else:
                            metadata[key] = str(value)  # Convert complex types to string
                processed_chunks.append(Document(page_content=chunk.text, metadata=metadata))
            
            # Apply filter_complex_metadata
            processed_chunks = filter_complex_metadata(processed_chunks)

            # Cache processed chunks for dynamic retriever creation
            self._processed_chunks = processed_chunks

            # Create vector store
            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
            self.vector_store = Chroma.from_documents(documents=processed_chunks, embedding=embeddings)
            logger.info("Vector store created")

            # Create initial retriever (will be replaced dynamically per query)
            self.retriever = self.create_dynamic_retriever(k_value=18)  # Default value

            logger.info("Dynamic retriever system initialized")

            def format_docs(docs):
                return "\n\n".join(doc.page_content for doc in docs)
            self.chain = (
                {"context": self.retriever | format_docs, "question": RunnablePassthrough()}
                | self.prompt
                | self.model
                | StrOutputParser()
            )
            logger.info("Chain created successfully")
        except Exception as e:
            logger.error(f"Error in ingest: {str(e)}")
            raise

    def ask(self, query: str):
        if not self.vector_store:
            logger.warning("No vector store found, PDF not ingested")
            return "Please, add a PDF document first."

        logger.info(f"Processing query: {query}")
        
        # Classify query and get optimal parameters
        classification = self.classify_query(query)
        logger.info(f"Query classified as: {classification['type']} - {classification['description']}")
        
        # Create dynamic retriever based on classification
        dynamic_retriever = self.create_dynamic_retriever(classification['k_value'])
        
        # Get relevant documents with optimized retrieval
        retrieved_docs = dynamic_retriever.get_relevant_documents(query)
        
        logger.info(f"Retrieved {len(retrieved_docs)} chunks for {classification['type']} query")
        for i, doc in enumerate(retrieved_docs):
            logger.info(
                f"Retrieved chunk {i} (score: {doc.metadata.get('score', 'N/A')}): {doc.page_content[:200]}..."
            )

        # Format documents
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)
        
        # Create chain with dynamic retriever
        chain = (
            {"context": lambda _: format_docs(retrieved_docs), "question": RunnablePassthrough()}
            | self.prompt
            | self.model
            | StrOutputParser()
        )
        
        # Get model answer
        answer = chain.invoke(query)

        # Try to capture doc_name (from first retrieved doc's metadata)
        doc_name = None
        if retrieved_docs and "source" in retrieved_docs[0].metadata:
            doc_name = os.path.basename(retrieved_docs[0].metadata["source"])

        # Log interaction with classification info
        # log_interaction(f"{query} [Type: {classification['type']}]", answer, doc_name)

        return answer

    def clear(self):
        self.vector_store = None
        self.retriever = None
        self.chain = None
        self._processed_chunks = None
        logger.info("Session cleared")
