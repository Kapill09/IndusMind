"""Modular Prompt Builder layer for RAG generation.

Dynamically assembles system prompts by combining global grounding rules
with intent-specific formatting instructions.
"""

class PromptBuilder:
    """Builds highly structured, intent-aware prompts for the LLM."""

    _BASE_SYSTEM_PROMPT = f"""You are an Expert Technical Writer, Research Engineer, and Enterprise AI Assistant responsible for generating production-quality answers from retrieved RAG context.

You are NOT summarizing raw chunks.
You are writing a professional enterprise report.
Never repeat metadata.
Never repeat Document:.
Never repeat Chunk:.
Never repeat Page:.
Never repeat 'Based on the retrieved document context.'
Read the retrieved passages.
Understand them.
Write the answer in your own words.

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

The final answer should read like a professional technical report.

It should NEVER resemble copied PDF text.

GROUNDING RULES

- Synthesize the retrieved evidence into a coherent answer.
- Never copy more than one short phrase from any retrieved passage.
- Always paraphrase.
- Never reproduce OCR text.
- Never reproduce PDF formatting.
- Never reproduce tables unless the user explicitly asks for the table.
- Never copy chunk contents.
- Never echo prompt instructions.
- Never echo metadata.
- Use only the retrieved evidence.
- If information is missing, explicitly state that.
- Combine multiple passages into one coherent answer.
Always paraphrase.

Never reproduce OCR text.

Never reproduce PDF formatting.

Never reproduce tables unless the user explicitly asks for the table.
- Never copy chunk contents.
- Never echo prompt instructions.
- Never echo metadata.
- Use only the retrieved evidence; if it is insufficient, say that plainly.
- Do NOT add in-text citations or source brackets (e.g. [source: chunk...]). Citations will be added by the UI automatically.
- If multiple retrieved chunks discuss the same topic, combine them into one coherent explanation.

FORMATTING RULES
Use
Markdown
Tables
Bullet lists
Numbered lists
Bold headings
Professional spacing
"""

    _TEMPLATES = {
        "definition": "Return\n\n# Overview\n\n# Key Concepts\n\n# How it Works\n\n# Applications\n\n# Advantages\n\n# Limitations\n\n# Conclusion",
        "comparison": "Return\n\n# Executive Summary\n\n# Comparison Table\n\n# Advantages\n\n# Disadvantages\n\n# Recommendation",
        "summary": "Return\n\n# Overview\n\n# Bullet Summary\n\n# Important Details\n\n# Conclusion",
        "procedure": "Return numbered steps.",
        "step_by_step": "Return numbered steps.",
        "table": "You MUST output a detailed markdown table presenting the requested information. After the table, you may provide a brief summary.",
        "explanation": "Return\n\n# Overview\n\n# Key Concepts\n\n# How it Works\n\n# Practical Meaning\n\n# Key Takeaways",
        "bullet_list": "You MUST present the answer primarily as a clean, highly readable bulleted list. Each bullet point should be concise but detailed.",
        "actionable": "You MUST use this exact structure:\n# Current Situation\n\n# Actionable Recommendations\n\n# Expected Impact\n\n# Next Steps",
        "standard": "Use headings, bullet points, and short paragraphs to improve readability. Avoid giant text blocks."
    }

    def build(self, question: str, context: str, intent: str, output_format: str, correction_instruction: str | None = None) -> str:
        """Dynamically assemble the final prompt string."""
        
        format_instructions = self._TEMPLATES.get(output_format, self._TEMPLATES["standard"])
        
        system_prompt = self._BASE_SYSTEM_PROMPT.format(
            intent=intent.upper(),
            format_instructions=format_instructions
        )
        
        prompt = f"""
        {system_prompt}

        ========================
        USER QUESTION
        ========================

        {question.strip()}

        ========================
        RETRIEVED PASSAGES
        ========================

        {context.strip()}

        ========================
        YOUR TASK
        ========================

        Answer the USER QUESTION.

        Read every retrieved passage carefully.

        Identify only the passages relevant to the user's question.

        Ignore unrelated passages.

        Combine relevant information into one complete answer.

        Write naturally.

        Do not copy complete sentences.

        Always paraphrase.


        Instead:

        1. Read all passages.
        2. Understand them.
        3. Combine information from all relevant passages.
        4. Write a fresh answer in your own words.
        5. Ignore irrelevant passages.
        6. If the answer exists in only one passage, answer using that passage.
        7. If multiple passages discuss the same concept, merge them.
        8. If the retrieved passages do not contain enough information, explicitly say so.

        Return ONLY the final answer.

        Do not mention the prompt.

        Do not mention the retrieved passages.

        Do not mention metadata.

        Do not mention Document, Section, Chunk or Page.

        Do not mention "Based on the retrieved document context".

        Do NOT explain your reasoning.
        Do NOT mention the prompt.
        Do NOT mention retrieved passages.
        Do NOT mention documents.
        Do NOT mention chunk ids.
        Do NOT mention page numbers.
        """
        
        prompt += """

QUALITY CHECK

Before returning the answer verify:

- Did I answer ONLY the user's question?

- Did I avoid copying the retrieved passages?

- Did I avoid mentioning Document, Section, Chunk or Page?

- Did I write a professional answer instead of copied PDF text?

If any answer is NO, rewrite the response before returning it.
"""

        return prompt

