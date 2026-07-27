"""Versioned prompt template domain model."""

from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    """Immutable prompt definition used by the RAG orchestration layer."""

    version: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    purpose: str = Field(..., min_length=1)
    system_prompt: str = Field(..., min_length=1)
    grounding_rules: str = Field(..., min_length=1)
    output_instructions: str = Field(..., min_length=1)

    model_config = {"frozen": True}

    def render(self, context: str, query: str) -> str:
        """Render a complete prompt for the supplied context and query."""
        return self.system_prompt.format(
            context=context,
            query=query,
            grounding_rules=self.grounding_rules,
            output_instructions=self.output_instructions,
            sentinel="INSUFFICIENT_CONTEXT",
        )
