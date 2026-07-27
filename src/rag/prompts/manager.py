"""Version-controlled prompt registry for enterprise RAG use cases."""

from typing import Dict, List, Optional

from src.common.errors.exceptions import ResourceNotFoundError
from src.rag.prompts.template import PromptTemplate

INSUFFICIENT_CONTEXT_SENTINEL = "INSUFFICIENT_CONTEXT"

_GROUNDING_RULES = (
    "Answer ONLY from the provided context. "
    f"If the context is missing or inadequate, return exactly {INSUFFICIENT_CONTEXT_SENTINEL}. "
    "Do not use outside knowledge or fabricate citations."
)

_OUTPUT_INSTRUCTIONS = (
    "Provide a concise factual answer and cite supporting context with citation tags such as [1]."
)

_PROMPT_REGISTRY: Dict[str, Dict[str, PromptTemplate]] = {
    "clinical_qa": {
        "1.0": PromptTemplate(
            version="1.0",
            name="clinical_qa",
            purpose="Answer clinical guideline questions from retrieved clinical context.",
            grounding_rules=_GROUNDING_RULES,
            output_instructions=_OUTPUT_INSTRUCTIONS,
            system_prompt=(
                "You are an enterprise clinical knowledge assistant.\n\n"
                "GROUNDING RULES:\n{grounding_rules}\n\n"
                "OUTPUT INSTRUCTIONS:\n{output_instructions}\n\n"
                "CONTEXT:\n{context}\n\n"
                "QUESTION:\n{query}\n\n"
                "ANSWER:"
            ),
        )
    },
    "claims_analysis": {
        "1.0": PromptTemplate(
            version="1.0",
            name="claims_analysis",
            purpose="Analyze claims questions from retrieved policy and claims context.",
            grounding_rules=_GROUNDING_RULES,
            output_instructions=_OUTPUT_INSTRUCTIONS,
            system_prompt=(
                "You are an enterprise claims analysis assistant.\n\n"
                "GROUNDING RULES:\n{grounding_rules}\n\n"
                "OUTPUT INSTRUCTIONS:\n{output_instructions}\n\n"
                "CONTEXT:\n{context}\n\n"
                "QUESTION:\n{query}\n\n"
                "ANSWER:"
            ),
        )
    },
    "policy_qa": {
        "1.0": PromptTemplate(
            version="1.0",
            name="policy_qa",
            purpose="Answer policy and governance questions from retrieved policy context.",
            grounding_rules=_GROUNDING_RULES,
            output_instructions=_OUTPUT_INSTRUCTIONS,
            system_prompt=(
                "You are an enterprise policy compliance assistant.\n\n"
                "GROUNDING RULES:\n{grounding_rules}\n\n"
                "OUTPUT INSTRUCTIONS:\n{output_instructions}\n\n"
                "CONTEXT:\n{context}\n\n"
                "QUESTION:\n{query}\n\n"
                "ANSWER:"
            ),
        )
    },
}


class PromptManager:
    """Resolve versioned prompt templates by name and optional version."""

    @staticmethod
    def get_template(name: str = "clinical_qa", version: Optional[str] = None) -> PromptTemplate:
        """Return a named template version, defaulting to the latest registered version."""
        versions = _PROMPT_REGISTRY.get(name)
        if not versions:
            raise ResourceNotFoundError(message=f"Prompt template '{name}' was not found.")
        selected_version = version or sorted(versions.keys())[-1]
        template = versions.get(selected_version)
        if not template:
            raise ResourceNotFoundError(
                message=f"Prompt template '{name}' version '{selected_version}' was not found."
            )
        return template

    @staticmethod
    def render_prompt(
        context: str,
        query: str,
        name: str = "clinical_qa",
        version: Optional[str] = None,
    ) -> str:
        """Render a prompt from a registered template."""
        return PromptManager.get_template(name=name, version=version).render(context=context, query=query)

    @staticmethod
    def list_templates() -> Dict[str, List[str]]:
        """Return registered prompt names and available versions."""
        return {name: sorted(versions.keys()) for name, versions in _PROMPT_REGISTRY.items()}

    @staticmethod
    def is_available() -> bool:
        """Return true when the registry contains at least one usable template."""
        return any(_PROMPT_REGISTRY.values())
