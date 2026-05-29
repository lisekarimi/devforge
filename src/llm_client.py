"""Swappable LLM client. Supports OpenAI and Cerebras (OpenAI-compatible API)."""

from openai import OpenAI
import config


class LLMClient:
    """Thin wrapper so the rest of the code never imports openai directly."""

    def __init__(self):
        if config.LLM_PROVIDER == "openai":
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.model = config.OPENAI_MODEL
        elif config.LLM_PROVIDER == "cerebras":
            self.client = OpenAI(
                api_key=config.CEREBRAS_API_KEY,
                base_url="https://api.cerebras.ai/v1",
            )
            self.model = config.CEREBRAS_MODEL
        else:
            raise NotImplementedError(f"Provider {config.LLM_PROVIDER} not wired yet")

    def generate(self, system: str, user: str, temperature: float = 0.2) -> str:
        """Send a system + user prompt, return the assistant's text."""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content


if __name__ == "__main__":
    import config

    config.validate()
    llm = LLMClient()
    out = llm.generate(
        system="You are a terse assistant.",
        user="Say hello in exactly 3 words.",
    )
    print(out)
