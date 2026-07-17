"""Query expansion engine for INDUS MIND retrieval.

Generates multiple semantically diverse search queries from a single user
query.  Expansion strategy is driven by detected intent and extracted
entities, producing complete search queries (not bare entity names) so
that embedding models receive enough semantic context.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import os
from google import genai
from google.genai import types

from backend.services.entity_extractor import EntityType, ExtractedEntity
from backend.services.knowledge_graph_service import KnowledgeGraphService

logger = logging.getLogger(__name__)


class SearchQueryType(str, Enum):
    """Which retrieval channels a search query should use."""

    HYBRID = "hybrid"      # Dense + BM25
    DENSE = "dense"        # Embedding search only
    BM25 = "bm25"          # Keyword search only
    METADATA = "metadata"  # Structured metadata lookup only


@dataclass
class SearchQuery:
    """One concrete search query to execute against the retrieval backend."""

    text: str
    target_entity: str | None = None
    target_document_id: str | None = None
    query_type: SearchQueryType = SearchQueryType.HYBRID
    weight: float = 1.0


class QueryExpander:
    """Generate multiple search queries from one user query.

    The expander produces complete, embeddable search queries — never bare
    entity names.  Different intents get different expansion strategies to
    maximise recall for each query type.
    """

    def __init__(self, client: Any | None = None, kg_service: KnowledgeGraphService | None = None):
        self.client = client or genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.kg_service = kg_service


    # Intent names imported as strings to avoid circular imports; the
    # QueryUnderstandingEngine passes the intent string directly.

    def expand(
        self,
        query: str,
        intent: str,
        entities: list[ExtractedEntity],
        strategy: str,
    ) -> list[SearchQuery]:
        """Expand a user query into multiple search queries.

        Args:
            query: Original user query text.
            intent: Classified intent string (e.g. "comparison", "definition").
            entities: Extracted entities with optional document associations.
            strategy: Retrieval strategy string (e.g. "multi_query", "single").

        Returns:
            List of SearchQuery objects, each a complete search query.
        """

        if strategy == "structured":
            return self._expand_structured(query, entities)

        if intent == "comparison":
            return self._expand_comparison(query, entities)

        if intent in ("definition", "exploratory"):
            return self._expand_definition(query, entities)

        if strategy == "exhaustive":
            return self._expand_exhaustive(query, entities)

        if intent == "cross_document":
            search_queries = self._expand_cross_document(query, entities)
        else:
            search_queries = self._expand_default(query, entities)
            
        # Add Semantic & KG expansions to any base search strategy
        semantic_query = self._build_semantic_query(query, intent, entities)
        if semantic_query:
            search_queries.append(semantic_query)
            
        return search_queries

    def _build_semantic_query(self, query: str, intent: str, entities: list[ExtractedEntity]) -> SearchQuery | None:
        """Build a semantic query using LLM terminology and KG context."""
        kg_terms = self._get_kg_expansions(entities)
        llm_terms = self._generate_semantic_expansions(query, intent, entities)
        
        all_terms = list(set(kg_terms + llm_terms))
        if not all_terms:
            return None
            
        expanded_text = " ".join(all_terms)
        return SearchQuery(
            text=expanded_text,
            query_type=SearchQueryType.HYBRID,
            weight=0.6,
        )

    def _get_kg_expansions(self, entities: list[ExtractedEntity]) -> list[str]:
        """Fetch aliases and 1st-degree neighbors from the Knowledge Graph."""
        if not self.kg_service:
            return []
            
        terms = []
        for e in entities:
            try:
                node = self.kg_service.get_node(e.normalized)
                if node:
                    if node.aliases:
                        terms.extend(node.aliases)
                
                # Get neighbors
                neighbors = self.kg_service.get_neighbors(e.normalized, max_depth=1)
                for n in neighbors:
                    terms.append(n["node_id"])
            except Exception as exc:
                logger.warning("Failed to fetch KG expansions for %s: %s", e.normalized, exc)
                
        return [t for t in terms if t.strip()]
        
    def _generate_semantic_expansions(self, query: str, intent: str, entities: list[ExtractedEntity]) -> list[str]:
        """Use Gemini to strictly extract synonyms and acronyms."""
        prompt = f"""You are an industrial terminology expert.
USER QUERY: {query}
ENTITIES: {", ".join(e.text for e in entities)}

Task: Extract established synonyms, acronyms, and direct terminology for the concepts in the query.
CRITICAL RULES:
- ONLY output established synonyms and acronyms.
- DO NOT hallucinate, guess, or invent concepts.
- DO NOT output full sentences.
- Output a comma-separated list of terms.
- If no direct synonym exists, output nothing.
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0)
            )
            if response.text and "nothing" not in response.text.lower():
                # Clean up comma separated list
                return [t.strip() for t in response.text.split(",") if t.strip()]
            return []
        except Exception as exc:
            logger.warning("LLM Semantic Expansion failed: %s", exc)
            return []

    # ── Per-Intent Expansion Strategies ───────────────────────────────

    def _expand_comparison(
        self, query: str, entities: list[ExtractedEntity]
    ) -> list[SearchQuery]:
        """Expand a comparison query into per-entity sub-queries.

        "Compare MAKA and D2DAP" →
        [
            "MAKA authentication protocol features capabilities",
            "MAKA security mechanism architecture",
            "D2DAP authentication protocol features capabilities",
            "D2DAP security mechanism architecture",
            "MAKA vs D2DAP comparison differences",
        ]
        """

        search_queries: list[SearchQuery] = []

        # Identify the comparison entities (exclude structural refs like page/section)
        comparison_entities = [
            e
            for e in entities
            if e.entity_type
            not in (
                EntityType.PAGE,
                EntityType.SECTION,
                EntityType.CHAPTER,
                EntityType.FIGURE,
                EntityType.TABLE,
            )
        ]

        # Extract the topic context from the query (everything except entity names
        # and comparison keywords)
        topic = self._extract_topic(query, comparison_entities)

        if len(comparison_entities) < 2:
            # Cannot decompose — treat as default with emphasis on comparison
            search_queries.append(
                SearchQuery(text=query, query_type=SearchQueryType.HYBRID, weight=1.0)
            )
            search_queries.append(
                SearchQuery(
                    text=f"{query} comparison differences features",
                    query_type=SearchQueryType.DENSE,
                    weight=0.7,
                )
            )
            return search_queries

        # Per-entity queries: give each entity enough semantic context to embed well
        for entity in comparison_entities:
            doc_id = entity.source_document_ids[0] if entity.source_document_ids else None

            # Core retrieval query
            search_queries.append(
                SearchQuery(
                    text=f"{entity.text} {topic} features capabilities overview".strip(),
                    target_entity=entity.text,
                    target_document_id=doc_id,
                    query_type=SearchQueryType.HYBRID,
                    weight=1.0,
                )
            )
            # Architecture / mechanism query
            search_queries.append(
                SearchQuery(
                    text=f"{entity.text} {topic} architecture mechanism design".strip(),
                    target_entity=entity.text,
                    target_document_id=doc_id,
                    query_type=SearchQueryType.HYBRID,
                    weight=0.7,
                )
            )

        # Cross-entity comparison query
        entity_names = " vs ".join(e.text for e in comparison_entities[:3])
        search_queries.append(
            SearchQuery(
                text=f"{entity_names} comparison differences {topic}".strip(),
                target_entity=None,
                query_type=SearchQueryType.HYBRID,
                weight=0.5,
            )
        )

        return search_queries

    def _expand_definition(
        self, query: str, entities: list[ExtractedEntity]
    ) -> list[SearchQuery]:
        """Expand a definition / exploratory query with topical variants.

        "What is AI?" →
        [
            "artificial intelligence definition overview introduction",
            "AI applications use cases examples",
            "What is AI?",  (original)
        ]
        """

        topic = self._strip_question_prefix(query)

        search_queries = [
            SearchQuery(
                text=f"{topic} definition overview introduction",
                query_type=SearchQueryType.HYBRID,
                weight=1.0,
            ),
            SearchQuery(
                text=f"{topic} applications use cases examples",
                query_type=SearchQueryType.BM25,
                weight=0.6,
            ),
            SearchQuery(
                text=query,
                query_type=SearchQueryType.DENSE,
                weight=0.8,
            ),
        ]
        return search_queries

    def _expand_exhaustive(
        self, query: str, entities: list[ExtractedEntity]
    ) -> list[SearchQuery]:
        """Expand for exhaustive retrieval across all selected documents."""

        return [
            SearchQuery(text=query, query_type=SearchQueryType.HYBRID, weight=1.0),
            SearchQuery(
                text=self._rephrase(query),
                query_type=SearchQueryType.DENSE,
                weight=0.7,
            ),
        ]

    def _expand_cross_document(
        self, query: str, entities: list[ExtractedEntity]
    ) -> list[SearchQuery]:
        """Expand for queries that reference entities across documents."""

        search_queries: list[SearchQuery] = []
        for entity in entities:
            doc_id = entity.source_document_ids[0] if entity.source_document_ids else None
            search_queries.append(
                SearchQuery(
                    text=f"{entity.text} {query}",
                    target_entity=entity.text,
                    target_document_id=doc_id,
                    query_type=SearchQueryType.HYBRID,
                    weight=1.0,
                )
            )

        # Always include the original query
        search_queries.append(
            SearchQuery(text=query, query_type=SearchQueryType.HYBRID, weight=0.8)
        )
        return search_queries

    def _expand_structured(
        self, query: str, entities: list[ExtractedEntity]
    ) -> list[SearchQuery]:
        """Expand for structured metadata lookups (PS, page, section)."""

        return [
            SearchQuery(text=query, query_type=SearchQueryType.METADATA, weight=1.0)
        ]

    def _expand_default(
        self, query: str, entities: list[ExtractedEntity]
    ) -> list[SearchQuery]:
        """Default expansion: original query + one rephrase."""

        search_queries = [
            SearchQuery(text=query, query_type=SearchQueryType.HYBRID, weight=1.0),
        ]

        # Add entity-enhanced query if entities were detected
        entity_names = " ".join(e.text for e in entities[:3] if e.confidence >= 0.7)
        if entity_names and entity_names.lower() not in query.lower():
            search_queries.append(
                SearchQuery(
                    text=f"{query} {entity_names}",
                    query_type=SearchQueryType.DENSE,
                    weight=0.6,
                )
            )

        return search_queries

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _extract_topic(query: str, entities: list[ExtractedEntity]) -> str:
        """Extract the topical context from a query, removing entity names and keywords."""

        topic = query
        # Remove comparison keywords
        topic = re.sub(
            r"\b(compare|comparison|versus|vs\.?|difference|between|and)\b",
            "",
            topic,
            flags=re.IGNORECASE,
        )
        # Remove entity names
        for entity in entities:
            topic = re.sub(re.escape(entity.text), "", topic, flags=re.IGNORECASE)

        topic = re.sub(r"\s+", " ", topic).strip()
        return topic if topic else "features properties characteristics"

    @staticmethod
    def _strip_question_prefix(query: str) -> str:
        """Remove common question prefixes to extract the topic."""

        topic = re.sub(
            r"^(explain|describe|what is|what are|tell me about|overview of|define)\s+",
            "",
            query,
            flags=re.IGNORECASE,
        ).strip().rstrip("?.")
        return topic if topic else query

    @staticmethod
    def _rephrase(query: str) -> str:
        """Create a simple rephrase of the query for diversity."""

        # Swap question form
        rephrased = re.sub(
            r"^(what is|what are)\s+",
            "explain ",
            query,
            flags=re.IGNORECASE,
        )
        if rephrased == query:
            rephrased = re.sub(
                r"^(how to|how do)\s+",
                "procedure for ",
                query,
                flags=re.IGNORECASE,
            )
        if rephrased == query:
            rephrased = f"information about {query}"

        return rephrased
