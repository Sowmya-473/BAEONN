import gradio as gr
from openai import OpenAI

client = OpenAI(api_key="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", base_url="https://api.perplexity.ai")

system_prompt = {
    "role": "system",
    "content": (
        "You are an intelligent, conversational AI assistant like ChatGPT. "
        "You engage in multi-turn dialogue, remember the context of the conversation, "
        "and provide rich, helpful explanations in markdown. "
        "If a user asks for something that exists on the web (like products, articles, GitHub, LinkedIn, etc.), "
        "you MUST return real clickable links in the markdown format: [Title](https://...). "
        "Avoid vague references like [1] or [source]."
    )
}

def sonar_chat(message, chat_history):
    messages = [system_prompt]

    for user, bot in chat_history:
        messages.append({"role": "user", "content": user})
        messages.append({"role": "assistant", "content": bot})
    
    messages.append({"role": "user", "content": message})

    try:
        response = client.chat.completions.create(
            model="sonar-pro",
            messages=messages
        )
        bot_response = response.choices[0].message.content
    except Exception as e:
        bot_response = f"API Error: {str(e)}"

    return bot_response

chat_ui = gr.ChatInterface(
    fn=sonar_chat,
    title="BAEONN",
    description="Ask anything.",
    theme="soft",
)

chat_ui.launch()
