"""
CareRAG — Grounded Generation Module (Gemini)
---------------------------------------------
Team: Sa3ayda Geeks
Uses Google's GenAI SDK (google-genai) with structured output to generate
grounded clinical answers based strictly on retrieved context.

Structured Output Schema:
{
  "recommendation": "...",
  "evidence": "...",
  "citations": [{"document": "...", "section": "...", "page": 1}],
  "confidence": "high | medium | low | insufficient"
}
"""
import json
import os
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

import config

logger = config.setup_logger()

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

try:
    import jsonschema
except ImportError:
    jsonschema = None


# --- Pydantic Schema for Gemini Structured Output (Pydantic v2) ---

class CitationModel(BaseModel):
    document: str = Field(description="Exact document name from metadata")
    section: str = Field(default="N/A", description="Section title or number if available, else 'N/A'")
    page: int = Field(description="Page number as an integer", ge=1)


class GroundedResponseModel(BaseModel):
    recommendation: str = Field(description="Direct clinical answer or refusal message")
    evidence: str = Field(default="", description="Exact supporting text excerpt, or empty string if insufficient")
    citations: List[CitationModel] = Field(default_factory=list, description="List of source citations, empty if insufficient")
    confidence: Literal["high", "medium", "low", "insufficient"] = Field(description="Confidence level")


# Path to project JSON schema for validation
SCHEMA_PATH = config.BASE_DIR / "schema" / "response_schema.json"


def load_response_schema() -> Optional[dict]:
    """Loads the JSON schema from schema/response_schema.json if available."""
    if SCHEMA_PATH.exists():
        try:
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load JSON schema from {SCHEMA_PATH}: {e}")
            return None
    return None


def format_context_for_prompt(retrieved_results: list) -> str:
    """Formats retrieved chunks with metadata for inclusion in the prompt."""
    context_blocks = []
    for doc, score in retrieved_results:
        meta = doc.metadata
        doc_name = meta.get("document_name", "Unknown Document")
        page = meta.get("page_number", 1)
        section = meta.get("section", "N/A")
        chunk_id = meta.get("chunk_id", "N/A")

        header = f"[Source Document='{doc_name}', Page={page}, Section='{section}', ChunkID='{chunk_id}']"
        context_blocks.append(f"{header}\n{doc.page_content.strip()}")

    return "\n\n".join(context_blocks)


def create_refusal_response(reason: str) -> dict:
    """Creates a standard refusal dictionary adhering to response_schema.json."""
    return {
        "recommendation": reason,
        "evidence": "",
        "citations": [],
        "confidence": "insufficient"
    }


def validate_citations(response: dict, retrieved_results: list) -> bool:
    """Validates that every citation returned by the LLM corresponds to a real
    document name and page number present in the retrieved chunks."""
    if response.get("confidence") == "insufficient":
        return True

    citations = response.get("citations", [])
    if not citations:
        return True

    valid_sources = set()
    for doc, _ in retrieved_results:
        meta = doc.metadata
        doc_name = meta.get("document_name")
        page_num = meta.get("page_number")
        if doc_name is not None and page_num is not None:
            valid_sources.add((str(doc_name), int(page_num)))

    for cit in citations:
        cit_doc = str(cit.get("document", ""))
        try:
            cit_page = int(cit.get("page", 0))
        except (ValueError, TypeError):
            logger.error(f"Citation Validation Error: Invalid page number format: {cit.get('page')}")
            return False

        if (cit_doc, cit_page) not in valid_sources:
            logger.error(f"Citation Validation Error: Hallucinated citation rejected: Document='{cit_doc}', Page={cit_page}")
            return False

    return True


def generate_grounded_answer(question: str, retrieved_results: list, chat_history: list = None) -> dict:
    """Generates a grounded answer using Gemini constrained by structured output
    and validates both the schema and citations before returning.
    Supports chat_history context for multi-turn clinical consultations.
    """
    api_key = config.GEMINI_API_KEY
    if not api_key:
        logger.warning("GEMINI_API_KEY is not set in environment.")
        logger.info("To generate answers with Gemini, add GEMINI_API_KEY to your .env file.")
        return create_refusal_response("GEMINI_API_KEY is missing. Please set GEMINI_API_KEY in your .env file to enable generation.")

    if genai is None:
        logger.error("google-genai package is missing.")
        return create_refusal_response("google-genai package is missing. Please run 'pip install google-genai'.")

    if not retrieved_results:
        return create_refusal_response("I cannot answer this question because no relevant context was found in the indexed documents.")

    context_str = format_context_for_prompt(retrieved_results)

    history_str = ""
    if chat_history:
        history_blocks = []
        for msg in chat_history:
            role = "User" if getattr(msg, "role", "user") == "user" else "Assistant"
            content = getattr(msg, "content", str(msg))
            history_blocks.append(f"{role}: {content}")
        history_str = "\nPrior Consultation History:\n" + "\n".join(history_blocks) + "\n"

    prompt = f"""You are a clinical decision support AI assistant for CareRAG. Your task is to answer the user's clinical question based strictly and ONLY on the provided Context below.

CRITICAL GROUNDING & LANGUAGE RULES:
1. Answer ONLY using facts directly stated in the Context.
2. Do NOT use outside medical knowledge, general background knowledge, or personal opinion.
3. Do NOT invent, extrapolate, or hallucinate medical advice, document names, section names, or page numbers.
4. LANGUAGE PROTOCOL: Detect the language of the Question. If the user asks in Arabic, generate the 'recommendation' in clear, professional Arabic medical terminology while maintaining 100% strict clinical grounding from the context. Keep JSON schema keys intact.
5. If the provided Context does NOT contain sufficient evidence to answer the question:
   - Set "confidence" to "insufficient"
   - Provide a concise refusal statement in "recommendation" explaining that the evidence in the source document is insufficient to answer the question (in Arabic if question was in Arabic).
   - Set "evidence" to "" (empty string)
   - Set "citations" to [] (empty array)
6. If sufficient evidence IS present:
   - Provide a direct answer in "recommendation".
   - Quote or lightly trim the exact supporting text in "evidence".
   - Include citations in "citations" using the exact "Document" name and "Page" number from the source metadata. If section name is unavailable or 'N/A' in metadata, use "N/A".
   - Set "confidence" to "high", "medium", or "low".

Context:
{context_str}
{history_str}
Question: {question}"""

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=GroundedResponseModel,
            )
        )

        response_text = response.text.strip()
        result = json.loads(response_text)

        schema = load_response_schema()
        if schema and jsonschema:
            try:
                jsonschema.validate(instance=result, schema=schema)
            except jsonschema.ValidationError as ve:
                logger.error(f"Validation Error: LLM output failed schema validation: {ve.message}")
                return create_refusal_response("The model response did not meet the required JSON schema.")

        if not validate_citations(result, retrieved_results):
            return create_refusal_response(
                "The generated response contained citation metadata that was not present in the retrieved evidence."
            )

        return result

    except json.JSONDecodeError:
        logger.error("Could not parse Gemini output as JSON.")
        return create_refusal_response("The model generated an invalid response format.")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Gemini API Error: {error_msg}")
        return create_refusal_response(f"Gemini API request failed: {error_msg}")


if __name__ == "__main__":
    print(f"\n{config.BRAND_HEADER}: Grounded Generation Module ===\n")
    logger.info("generate.py is a module. Run pipeline.py to test the end-to-end flow.")
