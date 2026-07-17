"""Query understanding engine for INDUS MIND retrieval.

Features an Intent Classifier and a Query Router to map user questions
to optimal retrieval strategies and presentation formats.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from google import genai
from google.genai import types

from backend.services.entity_extractor import (
    EntityExtractor,
    EntityType,
    ExtractedEntity,
)
from backend.services.query_expander import QueryExpander, SearchQuery
from backend.services.document_selector import (
    DocumentScope,
    DocumentSelection,
    DocumentSelector,
)
from backend.services.knowledge_graph_service import KnowledgeGraphService

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    """Classified intent of a user query."""

    DEFINITION = "definition"
    EXPLANATION = "explanation"
    SUMMARIZATION = "summarization"
    COMPARISON = "comparison"
    ADVANTAGES = "advantages"
    DISADVANTAGES = "disadvantages"
    WORKFLOW = "workflow"
    PROCEDURE = "procedure"
    TABLE_REQUEST = "table_request"
    STEP_BY_STEP_GUIDE = "step_by_step_guide"
    CROSS_DOCUMENT_COMPARISON = "cross_document_comparison"
    COMMON_CONCEPTS = "common_concepts"
    PROBLEM_SOLUTION_MAPPING = "problem_solution_mapping"
    RECOMMENDATION = "recommendation"
    TROUBLESHOOTING = "troubleshooting"
    STRUCTURAL_LOOKUP = "structural_lookup"


class RetrievalStrategy(str, Enum):
    """How the retrieval executor should orchestrate search channels."""

    SINGLE = "single"              
    MULTI_QUERY = "multi_query"    
    STRUCTURED = "structured"      
    EXHAUSTIVE = "exhaustive"      


@dataclass
class QueryPlan:
    """Complete analysis of a user query — the contract between query
    understanding and retrieval execution.
    """

    original_query: str
    intent: QueryIntent
    confidence: float
    entities: list[ExtractedEntity]
    documents_referenced: list[str]
    search_queries: list[SearchQuery]
    retrieval_strategy: RetrievalStrategy
    output_format: str
    document_selection: DocumentSelection
    num_retrievals: int
    is_multi_document: bool
    requires_comparison: bool
    requires_table: bool

    @property
    def is_multi_query(self) -> bool:
        return self.retrieval_strategy == RetrievalStrategy.MULTI_QUERY

    @property
    def is_structured(self) -> bool:
        return self.retrieval_strategy == RetrievalStrategy.STRUCTURED

    @property
    def is_comparison(self) -> bool:
        return self.requires_comparison

    @property
    def comparison_entities(self) -> list[ExtractedEntity]:
        """Entities involved in a comparison."""
        return [
            e for e in self.entities
            if e.entity_type not in (
                EntityType.PAGE, EntityType.SECTION, EntityType.CHAPTER,
                EntityType.FIGURE, EntityType.TABLE, EntityType.STANDARD,
            )
        ]


class IntentClassifier:
    """Classifies user query intent using rules and an optional LLM fallback."""
    
    def __init__(self) -> None:
        self._COMPARISON_RE = re.compile(r"\b(compare|comparison|versus|vs\.?|differ|difference|between)\b", re.IGNORECASE)
        self._PROCEDURE_RE = re.compile(r"\b(how to|steps|procedure|method|instructions)\b", re.IGNORECASE)
        self._STEP_GUIDE_RE = re.compile(r"\b(step-by-step|step by step|guide)\b", re.IGNORECASE)
        self._TABLE_RE = re.compile(r"\b(table|tabular|matrix|grid)\b", re.IGNORECASE)
        self._ADVANTAGES_RE = re.compile(r"\b(advantage|advantages|benefit|benefits|pros)\b", re.IGNORECASE)
        self._DISADVANTAGES_RE = re.compile(r"\b(disadvantage|disadvantages|drawback|drawbacks|cons|limitations)\b", re.IGNORECASE)
        self._WORKFLOW_RE = re.compile(r"\b(workflow|flow|pipeline|architecture)\b", re.IGNORECASE)
        self._SUMMARIZATION_RE = re.compile(r"\b(summarize|summary|summarise|brief|overview)\b", re.IGNORECASE)
        self._TROUBLESHOOTING_RE = re.compile(r"\b(troubleshoot|fix|error|issue|problem|broken|fail|failure|fault)\b", re.IGNORECASE)
        self._RECOMMENDATION_RE = re.compile(r"\b(recommend|recommendation|suggest|best practice|advice)\b", re.IGNORECASE)
        self._PROBLEM_SOLUTION_RE = re.compile(r"\b(solution|solve|resolve|mitigate)\b", re.IGNORECASE)
        self._COMMON_CONCEPTS_RE = re.compile(r"\b(common|shared|similarities|both)\b", re.IGNORECASE)
        self._DEFINITION_RE = re.compile(r"^(what is|what are|define|meaning of)\b", re.IGNORECASE)
        
        api_key = os.getenv("GEMINI_API_KEY")
        self.llm_client = genai.Client(api_key=api_key) if api_key else None
        
    def classify(self, query: str, entities: list[ExtractedEntity], doc_sources: set[str]) -> tuple[QueryIntent, float]:
        structural_types = {EntityType.PROBLEM_STATEMENT, EntityType.PAGE, EntityType.SECTION, EntityType.CHAPTER, EntityType.FIGURE, EntityType.TABLE}
        if any(e.entity_type in structural_types for e in entities):
            if self._PROBLEM_SOLUTION_RE.search(query):
                return QueryIntent.PROBLEM_SOLUTION_MAPPING, 0.9
            return QueryIntent.STRUCTURAL_LOOKUP, 0.95

        is_cross_doc = len(doc_sources) > 1

        if self._TABLE_RE.search(query):
            return QueryIntent.TABLE_REQUEST, 0.9

        has_comparison = bool(self._COMPARISON_RE.search(query))
        comparison_entities = [e for e in entities if e.entity_type not in structural_types and e.confidence >= 0.5]
        
        if has_comparison or len(comparison_entities) >= 2:
            if is_cross_doc:
                return QueryIntent.CROSS_DOCUMENT_COMPARISON, 0.9
            return QueryIntent.COMPARISON, 0.85

        if self._STEP_GUIDE_RE.search(query):
            return QueryIntent.STEP_BY_STEP_GUIDE, 0.9
            
        if self._PROCEDURE_RE.search(query):
            return QueryIntent.PROCEDURE, 0.85

        if self._TROUBLESHOOTING_RE.search(query):
            return QueryIntent.TROUBLESHOOTING, 0.85
            
        if self._RECOMMENDATION_RE.search(query):
            return QueryIntent.RECOMMENDATION, 0.85
            
        if self._WORKFLOW_RE.search(query):
            return QueryIntent.WORKFLOW, 0.85

        if self._ADVANTAGES_RE.search(query):
            return QueryIntent.ADVANTAGES, 0.85
            
        if self._DISADVANTAGES_RE.search(query):
            return QueryIntent.DISADVANTAGES, 0.85
            
        if self._COMMON_CONCEPTS_RE.search(query):
            return QueryIntent.COMMON_CONCEPTS, 0.8
            
        if self._SUMMARIZATION_RE.search(query):
            return QueryIntent.SUMMARIZATION, 0.85

        if self._DEFINITION_RE.search(query):
            return QueryIntent.DEFINITION, 0.8
            
        if self._PROBLEM_SOLUTION_RE.search(query):
            return QueryIntent.PROBLEM_SOLUTION_MAPPING, 0.8
            
        if self.llm_client:
            llm_intent, llm_conf = self._llm_fallback(query)
            if llm_intent:
                return llm_intent, llm_conf

        return QueryIntent.EXPLANATION, 0.5
        
    def _llm_fallback(self, query: str) -> tuple[QueryIntent | None, float]:
        try:
            prompt = f"Classify the following query into exactly one of these intents: Definition, Explanation, Summarization, Comparison, Advantages, Disadvantages, Workflow, Procedure, Table Request, Step-by-step Guide, Cross-document Comparison, Common Concepts, Problem-Solution Mapping, Recommendation, Troubleshooting.\n\nQuery: '{query}'\n\nReturn ONLY the exact intent name."
            response = self.llm_client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=10)
            )
            intent_text = response.text.strip().lower().replace(" ", "_").replace("-", "_")
            for intent in QueryIntent:
                if intent.value == intent_text:
                    return intent, 0.7
        except Exception as exc:
            logger.warning("LLM fallback classification failed: %s", exc)
        return None, 0.0


class QueryRouter:
    """Decides retrieval execution and formatting parameters based on intent."""
    
    def route(self, intent: QueryIntent, is_scoped: bool, is_cross_doc: bool) -> tuple[RetrievalStrategy, int, str, bool, bool, bool]:
        strategy = RetrievalStrategy.SINGLE
        num_retrievals = 5
        output_format = "standard"
        requires_comparison = False
        requires_table = False
        is_multi_document = is_cross_doc
        
        if intent == QueryIntent.STRUCTURAL_LOOKUP:
            strategy = RetrievalStrategy.STRUCTURED
            
        elif intent in (QueryIntent.COMPARISON, QueryIntent.CROSS_DOCUMENT_COMPARISON, QueryIntent.ADVANTAGES, QueryIntent.DISADVANTAGES, QueryIntent.COMMON_CONCEPTS):
            strategy = RetrievalStrategy.MULTI_QUERY
            requires_comparison = True
            num_retrievals = 8
            
        elif intent in (QueryIntent.SUMMARIZATION, QueryIntent.EXPLANATION, QueryIntent.DEFINITION) and is_scoped:
            strategy = RetrievalStrategy.EXHAUSTIVE
            num_retrievals = 10
            
        if intent == QueryIntent.TABLE_REQUEST:
            requires_table = True
            output_format = "table"
            num_retrievals = 8
        elif intent in (QueryIntent.PROCEDURE, QueryIntent.STEP_BY_STEP_GUIDE, QueryIntent.WORKFLOW, QueryIntent.TROUBLESHOOTING):
            output_format = "step_by_step"
            num_retrievals = 6
        elif intent in (QueryIntent.ADVANTAGES, QueryIntent.DISADVANTAGES):
            output_format = "bullet_list"
            requires_comparison = False
        elif intent == QueryIntent.RECOMMENDATION:
            output_format = "actionable"
        elif intent in (QueryIntent.EXPLANATION, QueryIntent.DEFINITION):
            output_format = "explanation"
        elif requires_comparison:
            output_format = "comparison"
        elif intent == QueryIntent.SUMMARIZATION:
            output_format = "summary"
            
        return strategy, num_retrievals, output_format, is_multi_document, requires_comparison, requires_table


class QueryUnderstandingEngine:
    """Multi-stage query analysis pipeline integrating the Intent Classifier and Router."""

    def __init__(
        self,
        entity_extractor: EntityExtractor | None = None,
        query_expander: QueryExpander | None = None,
        document_selector: DocumentSelector | None = None,
    ) -> None:
        self.entity_extractor = entity_extractor or EntityExtractor()
        kg_service = KnowledgeGraphService()
        self.query_expander = query_expander or QueryExpander(kg_service=kg_service)
        self.document_selector = document_selector or DocumentSelector()
        self.intent_classifier = IntentClassifier()
        self.router = QueryRouter()

    def analyze(
        self,
        query: str,
        user_selected_ids: list[str] | None = None,
    ) -> QueryPlan:
        clean_query = query.strip()

        entities = self.entity_extractor.extract(clean_query)
        doc_sources: set[str] = set()
        for entity in entities:
            doc_sources.update(entity.source_document_ids)

        intent, confidence = self.intent_classifier.classify(clean_query, entities, doc_sources)

        document_selection = self.document_selector.select(
            user_selected_ids, entities, intent.value
        )

        is_cross_doc = len(document_selection.selected_ids or []) > 1
        (
            strategy, 
            num_retrievals, 
            output_format, 
            is_multi_doc, 
            req_comparison, 
            req_table
        ) = self.router.route(intent, document_selection.is_scoped, is_cross_doc)

        search_queries = self.query_expander.expand(
            clean_query, intent.value, entities, strategy.value
        )

        plan = QueryPlan(
            original_query=clean_query,
            intent=intent,
            confidence=confidence,
            entities=entities,
            documents_referenced=list(doc_sources),
            search_queries=search_queries,
            retrieval_strategy=strategy,
            output_format=output_format,
            document_selection=document_selection,
            num_retrievals=num_retrievals,
            is_multi_document=is_multi_doc,
            requires_comparison=req_comparison,
            requires_table=req_table
        )
        
        print("\n[RAG DEBUG] ====================================================")
        print("[RAG DEBUG] STEP 2 - Query Understanding")
        print(f"[RAG DEBUG] Expanded Query: {[sq.text for sq in search_queries]}")
        print(f"[RAG DEBUG] Intent: {intent.value}")
        print(f"[RAG DEBUG] Entities: {[e.text for e in entities]}")
        print(f"[RAG DEBUG] Comparison Targets: {[e.text for e in plan.comparison_entities]}")
        print(f"[RAG DEBUG] Target Document IDs: {document_selection.selected_ids}")
        print(f"[RAG DEBUG] Need Comparison: {'Yes' if req_comparison else 'No'}")
        print("[RAG DEBUG] ====================================================\n")

        logger.info(
            "QueryPlan built: intent=%s conf=%.2f strategy=%s docs=%s top_k=%d format=%s",
            plan.intent.value,
            plan.confidence,
            plan.retrieval_strategy.value,
            plan.documents_referenced,
            plan.num_retrievals,
            plan.output_format
        )

        return plan
