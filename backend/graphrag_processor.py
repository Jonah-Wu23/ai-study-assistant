# backend/graphrag_processor.py (Version 7 - Corrected LocalSearch arguments)

import os
import logging
import asyncio
import yaml
import traceback
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List

# --- Third-party Imports ---
import pandas as pd
import tiktoken
import lancedb

# --- GraphRAG Imports ---
try:
    from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
    from graphrag.query.indexer_adapters import (
        read_indexer_covariates,
        read_indexer_entities,
        read_indexer_relationships,
        read_indexer_reports,
        read_indexer_text_units,
    )
    from graphrag.query.structured_search.local_search.mixed_context import (
        LocalSearchMixedContext,
    )
    from graphrag.query.structured_search.local_search.search import LocalSearch
    from graphrag.vector_stores.lancedb import LanceDBVectorStore
    from graphrag.config.enums import ModelType
    from graphrag.config.models.language_model_config import LanguageModelConfig
    from graphrag.language_model.manager import ModelManager
    GRAPHRAG_AVAILABLE = True
except ImportError as e:
    print("="*80)
    print(f"ERROR: Could not import necessary graphrag/lancedb modules: {e}")
    print("Please ensure graphrag, lancedb, and dependencies are installed.")
    print("Functionality will be limited.")
    print("="*80)
    GRAPHRAG_AVAILABLE = False
# --- End Imports ---

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)
# --- End Logging Setup ---

# --- Configuration ---
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'data', '.env')
if not os.path.exists(dotenv_path):
     dotenv_path = './data/.env'
load_dotenv(dotenv_path=dotenv_path)

GRAPHRAG_ROOT_DIR = os.path.abspath(os.getenv("GRAPHRAG_ROOT_DIR", "./data"))
OUTPUT_DIR = os.path.join(GRAPHRAG_ROOT_DIR, "output")
LANCEDB_URI = os.path.join(OUTPUT_DIR, "lancedb")

COMMUNITY_REPORT_TABLE = "community_reports.parquet"
ENTITY_TABLE = "entities.parquet"
RELATIONSHIP_TABLE = "relationships.parquet"
TEXT_UNIT_TABLE = "text_units.parquet"
COMMUNITY_TABLE = "communities.parquet"
COVARIATE_TABLE = "claims.parquet"

_settings_path = os.path.join(GRAPHRAG_ROOT_DIR, "settings.yaml")
_llm_config = {}
_embedding_config = {}
_vector_store_config = {}
try:
    with open(_settings_path, 'r', encoding='utf-8') as f:
        _settings_data = yaml.safe_load(f)
        _llm_config = _settings_data.get("models", {}).get("default_chat_model", {})
        _embedding_config = _settings_data.get("models", {}).get("default_embedding_model", {})
        _vector_store_config = _settings_data.get("vector_store", {}).get("default_vector_store", {})
except Exception as e:
    log.error(f"Could not load or parse settings.yaml from {_settings_path}: {e}")

LLM_TYPE = ModelType(_llm_config.get("type", "openai_chat"))
LLM_API_BASE = _llm_config.get("api_base")
LLM_MODEL = _llm_config.get("model")
LLM_ENCODING_MODEL = _llm_config.get("encoding_model", "cl100k_base")
GRAPHRAG_API_KEY = os.getenv("GRAPHRAG_API_KEY")

EMBEDDING_TYPE = ModelType(_embedding_config.get("type", "openai_embedding"))
EMBEDDING_API_BASE = _embedding_config.get("api_base")
EMBEDDING_MODEL = _embedding_config.get("model")
EMBEDDING_ENCODING_MODEL = _embedding_config.get("encoding_model", "cl100k_base")
TEXT_EMBEDDING_API_KEY = os.getenv("TEXT_EMBEDDING_API_KEY")

LANCEDB_COLLECTION_NAME = "default-entity-description"
log.info(f"Using LanceDB collection name for entity embeddings: '{LANCEDB_COLLECTION_NAME}'")

COMMUNITY_LEVEL = 2

_model_manager: Optional[ModelManager] = None
_search_engine: Optional[LocalSearch] = None
_initialized: bool = False
_lock = asyncio.Lock()

# --- Helper Functions ---
def _resolve_api_key(key_value: Optional[str]) -> Optional[str]:
    if key_value and key_value.startswith("${") and key_value.endswith("}"):
        var_name = key_value[2:-1]
        resolved_key = os.getenv(var_name)
        if not resolved_key: log.error(f"API Key environment variable '{var_name}' not found!")
        return resolved_key
    direct_env_key = os.getenv(str(key_value))
    if direct_env_key:
         log.warning(f"Found API key in environment variable '{key_value}' directly. Consider using ${{...}} syntax.")
         return direct_env_key
    return key_value

# --- Initialization Function ---
async def initialize_rag():
    global _model_manager, _search_engine, _initialized
    if _initialized or not GRAPHRAG_AVAILABLE:
        if not GRAPHRAG_AVAILABLE: log.error("GraphRAG modules not available, cannot initialize.")
        return

    async with _lock:
        if _initialized: return

        log.info("--- Initializing GraphRAG Local Search Engine ---")
        try:
            required_files = [ENTITY_TABLE, RELATIONSHIP_TABLE, TEXT_UNIT_TABLE, COMMUNITY_TABLE, COMMUNITY_REPORT_TABLE]
            missing_files = [f for f in required_files if not os.path.exists(os.path.join(OUTPUT_DIR, f))]
            if missing_files:
                 log.error(f"Missing required GraphRAG output files in {OUTPUT_DIR}: {missing_files}")
                 log.error("Please run the 'graphrag index' command first.")
                 return

            log.info("Loading GraphRAG data from Parquet files...")
            entity_df = pd.read_parquet(os.path.join(OUTPUT_DIR, ENTITY_TABLE))
            community_df = pd.read_parquet(os.path.join(OUTPUT_DIR, COMMUNITY_TABLE))
            relationship_df = pd.read_parquet(os.path.join(OUTPUT_DIR, RELATIONSHIP_TABLE))
            report_df = pd.read_parquet(os.path.join(OUTPUT_DIR, COMMUNITY_REPORT_TABLE))
            text_unit_df = pd.read_parquet(os.path.join(OUTPUT_DIR, TEXT_UNIT_TABLE))

            covariates = None
            covariate_path = os.path.join(OUTPUT_DIR, COVARIATE_TABLE)
            if os.path.exists(covariate_path):
                log.info("Loading covariates (claims)...")
                covariate_df = pd.read_parquet(covariate_path)
                claims = read_indexer_covariates(covariate_df)
                covariates = {"claims": claims}
                log.info(f"Loaded {len(claims)} claim records.")
            else:
                log.warning(f"Covariate file '{COVARIATE_TABLE}' not found in {OUTPUT_DIR}. Skipping claims loading.")

            log.info("Converting DataFrames to GraphRAG objects...")
            entities = read_indexer_entities(entity_df, community_df, COMMUNITY_LEVEL)
            relationships = read_indexer_relationships(relationship_df)
            reports = read_indexer_reports(report_df, community_df, COMMUNITY_LEVEL)
            text_units = read_indexer_text_units(text_unit_df)
            log.info(f"Loaded: {len(entities)} entities, {len(relationships)} relationships, {len(reports)} reports, {len(text_units)} text units.")

            log.info(f"Connecting to LanceDB vector store at: {LANCEDB_URI}")
            entity_description_embedding_store_adapter = LanceDBVectorStore(
                collection_name=LANCEDB_COLLECTION_NAME,
            )
            entity_description_embedding_store_adapter.connect(db_uri=LANCEDB_URI)

            try:
                log.debug(f"Attempting to open LanceDB table '{LANCEDB_COLLECTION_NAME}' at '{LANCEDB_URI}' for existence check...")
                db = lancedb.connect(LANCEDB_URI)
                table_names = db.table_names()
                if LANCEDB_COLLECTION_NAME not in table_names:
                     log.error(f"LanceDB collection '{LANCEDB_COLLECTION_NAME}' not found in tables: {table_names} at {LANCEDB_URI}!")
                     log.error("Ensure indexing ran correctly and created the collection.")
                     return
                log.info(f"LanceDB check passed. Found collections: {table_names}")
            except Exception as ldb_err:
                 log.error(f"Failed to connect to or verify LanceDB collection '{LANCEDB_COLLECTION_NAME}' at {LANCEDB_URI}: {ldb_err}")
                 log.debug(traceback.format_exc())
                 return

            log.info("Setting up Language Model Manager...")
            _model_manager = ModelManager()

            # Chat LLM Config
            chat_api_key_val = _llm_config.get("api_key")
            resolved_chat_api_key = _resolve_api_key(chat_api_key_val)
            if not resolved_chat_api_key: log.warning("Chat API Key seems unresolved.")
            if not LLM_MODEL or not LLM_API_BASE:
                 log.error("Missing Chat LLM configuration (Model or API Base).")
                 return
            log.info(f"Chat Model Config: Type={LLM_TYPE}, Model={LLM_MODEL}, Base={LLM_API_BASE}, Encoding={LLM_ENCODING_MODEL}")
            chat_config = LanguageModelConfig(
                api_key=resolved_chat_api_key, type=LLM_TYPE, model=LLM_MODEL, api_base=LLM_API_BASE,
                encoding_model=LLM_ENCODING_MODEL, max_retries=_llm_config.get("max_retries", 5),
            )
            chat_model = _model_manager.get_or_create_chat_model(
                name="local_search_chat", model_type=LLM_TYPE, config=chat_config
            )

            # Embedding LLM Config
            embedding_api_key_val = _embedding_config.get("api_key")
            resolved_embedding_api_key = _resolve_api_key(embedding_api_key_val)
            if not resolved_embedding_api_key: log.warning("Embedding API Key seems unresolved.")
            if not EMBEDDING_MODEL or not EMBEDDING_API_BASE:
                  log.error("Missing Embedding LLM configuration (Model or API Base).")
                  return
            log.info(f"Embedding Model Config: Type={EMBEDDING_TYPE}, Model={EMBEDDING_MODEL}, Base={EMBEDDING_API_BASE}, Encoding={EMBEDDING_ENCODING_MODEL}")
            embedding_config = LanguageModelConfig(
                api_key=resolved_embedding_api_key, type=EMBEDDING_TYPE, model=EMBEDDING_MODEL, api_base=EMBEDDING_API_BASE,
                encoding_model=EMBEDDING_ENCODING_MODEL, max_retries=_embedding_config.get("max_retries", 5),
            )
            text_embedder = _model_manager.get_or_create_embedding_model(
                name="local_search_embedding", model_type=EMBEDDING_TYPE, config=embedding_config
            )

            # Token Encoder
            try:
                 token_encoder = tiktoken.encoding_for_model(LLM_ENCODING_MODEL)
                 log.info(f"Using token encoder: {LLM_ENCODING_MODEL}")
            except Exception as e:
                 log.warning(f"Failed to get tiktoken encoder for '{LLM_ENCODING_MODEL}', falling back to 'cl100k_base'. Error: {e}")
                 token_encoder = tiktoken.get_encoding("cl100k_base")

            log.info("Creating Local Search Context Builder...")
            context_builder = LocalSearchMixedContext(
                community_reports=reports, text_units=text_units, entities=entities,
                relationships=relationships, covariates=covariates,
                entity_text_embeddings=entity_description_embedding_store_adapter,
                embedding_vectorstore_key=EntityVectorStoreKey.ID,
                text_embedder=text_embedder, token_encoder=token_encoder,
            )

            log.info("Creating Local Search Engine...")
            local_context_params = {
                "text_unit_prop": 0.5, "community_prop": 0.1, "conversation_history_max_turns": 5,
                "conversation_history_user_turns_only": True, "top_k_mapped_entities": 10, "top_k_relationships": 10,
                "include_entity_rank": True, "include_relationship_weight": True, "include_community_rank": False,
                "return_candidate_context": False, "embedding_vectorstore_key": EntityVectorStoreKey.ID,
                "max_tokens": 12_000,
            }
            llm_params_from_settings = _llm_config.get("params", {})
            model_params = {
                "max_tokens": llm_params_from_settings.get("max_tokens", 2000),
                "temperature": llm_params_from_settings.get("temperature", 0.0),
                **llm_params_from_settings
            }
            log.info(f"Using LLM parameters for search: {model_params}")

            # --- CORRECTED ARGUMENTS ---
            _search_engine = LocalSearch(
                model=chat_model, # Use 'model' instead of 'llm'
                context_builder=context_builder,
                token_encoder=token_encoder,
                model_params=model_params, # Use 'model_params' instead of 'llm_params'
                context_builder_params=local_context_params,
                response_type="multiple paragraphs",
            )
            # --- END CORRECTION ---

            _initialized = True
            log.info("--- GraphRAG Local Search Engine Initialized Successfully ---")

        except FileNotFoundError as fnf_err:
            log.exception(f"ERROR during GraphRAG initialization: Required file not found - {fnf_err}")
            _initialized = False
        except ImportError as imp_err:
             log.exception(f"ERROR during GraphRAG initialization: Missing dependency - {imp_err}")
             _initialized = False
        except Exception as e:
            log.exception("!!! UNEXPECTED ERROR during GraphRAG initialization !!!")
            _initialized = False

# --- Query Function ---
async def query_rag(question: str, chat_history: Optional[List[Dict]] = None) -> str:
    if not _initialized or not _search_engine:
        log.error("GraphRAG search engine is not initialized. Cannot query.")
        return "知识库引擎尚未初始化，请稍后重试或检查启动日志。(Knowledge base engine not initialized. Please try again later or check startup logs.)"

    log.info(f"--- Querying GraphRAG (Local Search) ---")
    log.info(f"Query: '{question}'")

    try:
        result = await _search_engine.search(query=question)
        if result and hasattr(result, 'response') and result.response:
            log.info(f"GraphRAG response received, length: {len(result.response)}")
            return result.response
        else:
            log.warning(f"GraphRAG query returned no response or unexpected result format: {result}")
            return "抱歉，未能从知识库中找到明确的答案。(Sorry, could not find a clear answer in the knowledge base.)"

    except Exception as e:
        log.exception("!!! ERROR during GraphRAG local search query !!!")
        return f"查询知识库时遇到错误，请稍后再试。(Error querying the knowledge base, please try again later.) Details: {type(e).__name__}"

# --- Ingestion Trigger (Using CLI) ---
async def trigger_ingestion():
    global _initialized, _search_engine
    log.info("--- Triggering GraphRAG Indexing via CLI ---")
    _initialized = False
    _search_engine = None
    log.info("Search engine state reset. Will re-initialize after indexing and on next query/restart.")
    try:
        cmd = ["graphrag", "index", "--root", GRAPHRAG_ROOT_DIR]
        log.info(f"Executing command: {' '.join(cmd)}")
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        log.info("GraphRAG CLI process finished.")
        stdout_decoded = stdout.decode(errors='ignore') if stdout else ""
        stderr_decoded = stderr.decode(errors='ignore') if stderr else ""
        if stdout_decoded: log.info(f"GraphRAG STDOUT:\n{stdout_decoded}")
        if process.returncode != 0:
            if stderr_decoded: log.error(f"GraphRAG STDERR:\n{stderr_decoded}")
            log.error(f"GraphRAG indexing command failed with return code {process.returncode}")
            raise RuntimeError(f"GraphRAG indexing failed. Check logs above.")
        else:
            if stderr_decoded: log.info(f"GraphRAG STDERR (Return Code 0):\n{stderr_decoded}")
            log.info("--- GraphRAG Indexing Completed Successfully via CLI ---")
    except FileNotFoundError:
        log.error("ERROR: 'graphrag' command not found. Is GraphRAG installed and in the system PATH?")
        raise RuntimeError("'graphrag' command not found.")
    except Exception as e:
        log.exception("ERROR during GraphRAG indexing trigger")
        raise RuntimeError(f"Indexing trigger failed: {e}")