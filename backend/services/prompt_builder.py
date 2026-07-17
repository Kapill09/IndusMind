"""Modular Prompt Builder layer for RAG generation.

Dynamically assembles system prompts by combining global grounding rules
with intent-specific formatting instructions.
"""

from backend.config import FALLBACK_ANSWER


class PromptBuilder:
    """Builds highly structured, intent-aware prompts for the LLM."""

    _BASE_SYSTEM_PROMPT = f"""You are an Expert Technical Writer, Research Engineer, and Enterprise AI Assistant responsible for generating production-quality answers from retrieved RAG context.

IMPORTANT

The retrieval pipeline has already completed.
Relevant chunks have already been retrieved and re-ranked using Hybrid Search + Cross Encoder.
Your ONLY responsibility is to synthesize the retrieved context into the highest quality answer.
Never ignore the retrieved evidence.
Never invent information.
Never answer using prior knowledge if the retrieved documents do not support it.
If evidence is insufficient, explicitly state that, or reply exactly: "{FALLBACK_ANSWER}".

------------------------------------------------------------
DETECTED INTENT: {{intent}}
OUTPUT FORMAT INSTRUCTIONS: 
{{format_instructions}}
------------------------------------------------------------

Your answer should maximize
• Clarity
• Readability
• Technical correctness
• Grounded reasoning
• Professional presentation

The answer should look similar to NotebookLM or Microsoft Copilot.

------------------------------------------------------------

GROUNDING RULES

Ground every statement.
Every important fact should have evidence.
Never copy raw chunk text.
Instead: Understand, Combine, Explain.

Write naturally.
Add citations after factual claims using this format: [source: <chunk_id>, page <page-or-range>].
Avoid repeating citations after every single sentence; group them logically.

If multiple retrieved chunks discuss the same topic, combine them into one coherent explanation. Do NOT simply summarize each chunk independently.
If retrieved documents contradict each other, mention the contradiction.
Do NOT include irrelevant retrieved information.
If confidence is low, say "The available evidence is limited." instead of hallucinating.
"""

    _TEMPLATES = {
        "table": "You MUST output a detailed markdown table presenting the requested information. After the table, you may provide a brief summary.",
        
        "comparison": "You MUST use this exact structure and output nothing else:\n# Executive Summary\n\n# Comparison Table\n\n# Key Differences\n\n# Similarities\n\n# Recommendation",
        
        "step_by_step": "You MUST use this exact structure:\n# Objective\n\n# Prerequisites (if any)\n\n# Step-by-step Procedure\nUse numbered lists.\n\n# Expected Outcome\n\n# Important Notes",
        
        "summary": "You MUST use this exact structure and output nothing else:\n# Executive Summary\n\n# Main Points\n\n# Important Numbers\n\n# Key Technologies\n\n# Recommendations",
        
        "explanation": "You MUST provide a detailed, highly structured explanation. Use the following headers where applicable:\n# Overview\n# Key Concepts\n# How It Works\n# Practical Meaning\n# Key Takeaways",
        
        "bullet_list": "You MUST present the answer primarily as a clean, highly readable bulleted list. Each bullet point should be concise but detailed. Precede the list with a short introductory sentence and follow with a brief conclusion.",
        
        "actionable": "You MUST use this exact structure:\n# Current Situation (Brief summary)\n\n# Actionable Recommendations\n(Use actionable bullet points with clear verbs)\n\n# Expected Impact\n(What happens if these recommendations are followed)\n\n# Next Steps",
        
        "standard": "Use headings, bullet points, and short paragraphs to improve readability. Avoid giant text blocks."
    }

    def build(self, question: str, context: str, intent: str, output_format: str, correction_instruction: str | None = None) -> str:
        """Dynamically assemble the final prompt string."""
        
        format_instructions = self._TEMPLATES.get(output_format, self._TEMPLATES["standard"])
        
        system_prompt = self._BASE_SYSTEM_PROMPT.format(
            intent=intent.upper(),
            format_instructions=format_instructions
        )
        
        prompt = f"{system_prompt}\n\nRETRIEVED CONTEXT:\n{context}\n\nUSER QUESTION:\n{question}"
        
        if correction_instruction:
            prompt += f"\n\nCRITICAL CORRECTION INSTRUCTION (PREVIOUS ATTEMPT FAILED):\n{correction_instruction}\nDO NOT APOLOGIZE. JUST FIX THE OUTPUT."
            
        return prompt
