"""
Enhanced Retrieval Module

Implements advanced retrieval strategies:
1. Semantic/Sentence-aware chunking
2. Hybrid Search (Vector + BM25 keyword)
3. Metadata Filtering
4. Re-ranking with Cohere
5. Parent-Child document retrieval

These improvements significantly enhance RAG accuracy for patent document generation.
"""

import os
from typing import List, Optional, Dict, Any
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.node_parser import SentenceSplitter, TokenTextSplitter

# Try to import optional dependencies
try:
    from llama_index.postprocessor.cohere_rerank import CohereRerank
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False
    print("Cohere reranker not available - install llama-index-postprocessor-cohere-rerank")

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    print("BM25 not available - install rank-bm25")


# ============================================================================
# CHUNKING STRATEGIES
# ============================================================================

def get_sentence_splitter(chunk_size: int = 1024, chunk_overlap: int = 100):
    """
    Get sentence-aware text splitter.

    Benefits over token-based:
    - Doesn't split mid-sentence
    - Preserves semantic coherence
    - Better for technical/patent documents

    Args:
        chunk_size: Maximum chunk size in characters
        chunk_overlap: Overlap between chunks for context continuity
    """
    return SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        paragraph_separator="\n\n",
        secondary_chunking_regex="[^,.;。？！]+[,.;。？！]?",  # Sentence boundaries
    )


def get_token_splitter(chunk_size: int = 600, chunk_overlap: int = 50):
    """
    Fallback token-based splitter (original behavior).
    """
    return TokenTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )


def configure_chunking_strategy(strategy: str = "sentence"):
    """
    Configure the global chunking strategy.

    Args:
        strategy: "sentence" for sentence-aware, "token" for token-based
    """
    if strategy == "sentence":
        Settings.text_splitter = get_sentence_splitter(chunk_size=1024, chunk_overlap=100)
        print("Chunking: Using sentence-aware splitter (1024 chars, 100 overlap)")
    else:
        Settings.text_splitter = get_token_splitter(chunk_size=600, chunk_overlap=50)
        print("Chunking: Using token-based splitter (600 tokens, 50 overlap)")


# ============================================================================
# HYBRID SEARCH (Vector + BM25)
# ============================================================================

class HybridRetriever(BaseRetriever):
    """
    Hybrid retriever combining dense vector search with sparse BM25 keyword search.

    Benefits:
    - Vector search captures semantic similarity
    - BM25 captures exact keyword matches (important for technical terms)
    - Combined results provide better recall
    """

    def __init__(
        self,
        vector_retriever: BaseRetriever,
        nodes: List[TextNode],
        similarity_top_k: int = 5,
        bm25_weight: float = 0.3,
        vector_weight: float = 0.7
    ):
        """
        Initialize hybrid retriever.

        Args:
            vector_retriever: LlamaIndex vector retriever
            nodes: List of document nodes for BM25 indexing
            similarity_top_k: Number of results to return
            bm25_weight: Weight for BM25 scores (0-1)
            vector_weight: Weight for vector scores (0-1)
        """
        super().__init__()
        self.vector_retriever = vector_retriever
        self.similarity_top_k = similarity_top_k
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight

        # Build BM25 index if available
        self.bm25 = None
        self.nodes = nodes
        if BM25_AVAILABLE and nodes:
            self._build_bm25_index(nodes)

    def _build_bm25_index(self, nodes: List[TextNode]):
        """Build BM25 index from nodes."""
        try:
            # Tokenize documents for BM25
            tokenized_docs = [node.text.lower().split() for node in nodes]
            self.bm25 = BM25Okapi(tokenized_docs)
            print(f"BM25 index built with {len(nodes)} documents")
        except Exception as e:
            print(f"Failed to build BM25 index: {e}")
            self.bm25 = None

    def _retrieve(self, query_bundle) -> List[NodeWithScore]:
        """Retrieve using hybrid approach."""
        query = query_bundle.query_str

        # 1. Get vector search results
        vector_results = self.vector_retriever.retrieve(query)

        # 2. Get BM25 results if available
        bm25_results = []
        if self.bm25 is not None and self.nodes:
            try:
                tokenized_query = query.lower().split()
                bm25_scores = self.bm25.get_scores(tokenized_query)

                # Get top-k BM25 results
                top_indices = sorted(
                    range(len(bm25_scores)),
                    key=lambda i: bm25_scores[i],
                    reverse=True
                )[:self.similarity_top_k * 2]  # Get more for fusion

                for idx in top_indices:
                    if bm25_scores[idx] > 0:
                        bm25_results.append(NodeWithScore(
                            node=self.nodes[idx],
                            score=float(bm25_scores[idx])
                        ))
            except Exception as e:
                print(f"BM25 search error: {e}")

        # 3. Fuse results using Reciprocal Rank Fusion (RRF)
        fused_results = self._reciprocal_rank_fusion(vector_results, bm25_results)

        return fused_results[:self.similarity_top_k]

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[NodeWithScore],
        bm25_results: List[NodeWithScore],
        k: int = 60
    ) -> List[NodeWithScore]:
        """
        Combine results using Reciprocal Rank Fusion.

        RRF score = sum(1 / (k + rank)) for each result list
        """
        scores = {}
        node_map = {}

        # Score vector results
        for rank, result in enumerate(vector_results):
            node_id = result.node.node_id or result.node.text[:100]
            scores[node_id] = scores.get(node_id, 0) + self.vector_weight * (1 / (k + rank + 1))
            node_map[node_id] = result.node

        # Score BM25 results
        for rank, result in enumerate(bm25_results):
            node_id = result.node.node_id or result.node.text[:100]
            scores[node_id] = scores.get(node_id, 0) + self.bm25_weight * (1 / (k + rank + 1))
            node_map[node_id] = result.node

        # Sort by fused score
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Convert back to NodeWithScore
        fused_results = []
        for node_id, score in sorted_items:
            if node_id in node_map:
                fused_results.append(NodeWithScore(
                    node=node_map[node_id],
                    score=score
                ))

        return fused_results


# ============================================================================
# METADATA FILTERING
# ============================================================================

def create_metadata_filter(
    doc_type: Optional[str] = None,
    source_contains: Optional[str] = None,
    namespace: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create metadata filter for targeted retrieval.

    Args:
        doc_type: Filter by document type ("pdf", "pptx", "docx", "image")
        source_contains: Filter by source filename containing this string
        namespace: Filter by Pinecone namespace

    Returns:
        Dictionary of filters to pass to retriever
    """
    filters = {}

    if doc_type:
        filters["type"] = doc_type

    if source_contains:
        filters["source"] = {"$contains": source_contains}

    return filters


def get_filtered_retriever(
    index: VectorStoreIndex,
    similarity_top_k: int = 5,
    filters: Optional[Dict[str, Any]] = None
) -> BaseRetriever:
    """
    Get retriever with metadata filters applied.

    Args:
        index: VectorStoreIndex instance
        similarity_top_k: Number of results
        filters: Metadata filters
    """
    from llama_index.core.vector_stores import MetadataFilters, MetadataFilter, FilterOperator

    if filters:
        metadata_filters = []
        for key, value in filters.items():
            if isinstance(value, dict) and "$contains" in value:
                metadata_filters.append(MetadataFilter(
                    key=key,
                    value=value["$contains"],
                    operator=FilterOperator.CONTAINS
                ))
            else:
                metadata_filters.append(MetadataFilter(
                    key=key,
                    value=value,
                    operator=FilterOperator.EQ
                ))

        return index.as_retriever(
            similarity_top_k=similarity_top_k,
            filters=MetadataFilters(filters=metadata_filters)
        )

    return index.as_retriever(similarity_top_k=similarity_top_k)


# ============================================================================
# RE-RANKING
# ============================================================================

def get_cohere_reranker(top_n: int = 5, api_key: Optional[str] = None):
    """
    Get Cohere reranker for improving result quality.

    Reranking takes the initial retrieved results and reorders them
    using a more powerful cross-encoder model for better relevance.

    Args:
        top_n: Number of results after reranking
        api_key: Cohere API key (uses env var if not provided)
    """
    if not COHERE_AVAILABLE:
        print("Cohere reranker not available")
        return None

    cohere_api_key = api_key or os.environ.get("COHERE_API_KEY")
    if not cohere_api_key:
        print("COHERE_API_KEY not set - reranking disabled")
        return None

    try:
        return CohereRerank(
            api_key=cohere_api_key,
            top_n=top_n,
            model="rerank-english-v3.0"  # Latest Cohere rerank model
        )
    except Exception as e:
        print(f"Failed to initialize Cohere reranker: {e}")
        return None


# ============================================================================
# ENHANCED RETRIEVER FACTORY
# ============================================================================

class EnhancedRetrieverConfig:
    """Configuration for enhanced retriever."""

    def __init__(
        self,
        use_hybrid: bool = True,
        use_reranking: bool = False,
        similarity_top_k: int = 5,
        rerank_top_n: int = 3,
        bm25_weight: float = 0.3,
        vector_weight: float = 0.7,
        metadata_filters: Optional[Dict[str, Any]] = None
    ):
        self.use_hybrid = use_hybrid
        self.use_reranking = use_reranking
        self.similarity_top_k = similarity_top_k
        self.rerank_top_n = rerank_top_n
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        self.metadata_filters = metadata_filters


def create_enhanced_retriever(
    index: VectorStoreIndex,
    nodes: Optional[List[TextNode]] = None,
    config: Optional[EnhancedRetrieverConfig] = None
) -> BaseRetriever:
    """
    Create an enhanced retriever with all improvements.

    Args:
        index: VectorStoreIndex instance
        nodes: List of document nodes (for BM25 hybrid search)
        config: EnhancedRetrieverConfig instance

    Returns:
        Enhanced retriever instance
    """
    config = config or EnhancedRetrieverConfig()

    # Start with base vector retriever
    if config.metadata_filters:
        base_retriever = get_filtered_retriever(
            index,
            similarity_top_k=config.similarity_top_k * 2,  # Get more for fusion/reranking
            filters=config.metadata_filters
        )
    else:
        base_retriever = index.as_retriever(
            similarity_top_k=config.similarity_top_k * 2
        )

    # Add hybrid search if enabled and nodes available
    if config.use_hybrid and nodes and BM25_AVAILABLE:
        retriever = HybridRetriever(
            vector_retriever=base_retriever,
            nodes=nodes,
            similarity_top_k=config.similarity_top_k,
            bm25_weight=config.bm25_weight,
            vector_weight=config.vector_weight
        )
        print("Enhanced retriever: Hybrid search (Vector + BM25) enabled")
    else:
        retriever = base_retriever
        print("Enhanced retriever: Vector search only")

    return retriever


def apply_reranking(
    results: List[NodeWithScore],
    query: str,
    top_n: int = 3
) -> List[NodeWithScore]:
    """
    Apply Cohere reranking to results.

    Args:
        results: Initial retrieval results
        query: The query string
        top_n: Number of results after reranking

    Returns:
        Reranked results
    """
    reranker = get_cohere_reranker(top_n=top_n)
    if reranker is None:
        return results[:top_n]

    try:
        from llama_index.core import QueryBundle
        query_bundle = QueryBundle(query_str=query)
        reranked = reranker.postprocess_nodes(results, query_bundle)
        print(f"Reranking: Reduced {len(results)} results to top {len(reranked)}")
        return reranked
    except Exception as e:
        print(f"Reranking failed: {e}")
        return results[:top_n]


# ============================================================================
# INITIALIZATION HELPER
# ============================================================================

def initialize_enhanced_settings(
    chunking_strategy: str = "sentence",
    chunk_size: int = 1024,
    chunk_overlap: int = 100
):
    """
    Initialize enhanced retrieval settings.

    Call this at app startup to configure improved chunking.

    Args:
        chunking_strategy: "sentence" or "token"
        chunk_size: Chunk size (chars for sentence, tokens for token)
        chunk_overlap: Overlap size
    """
    if chunking_strategy == "sentence":
        Settings.text_splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        print(f"Enhanced Settings: Sentence-aware chunking ({chunk_size} chars, {chunk_overlap} overlap)")
    else:
        Settings.text_splitter = TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        print(f"Enhanced Settings: Token-based chunking ({chunk_size} tokens, {chunk_overlap} overlap)")

    return Settings
