import os
import json
import pickle
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import gradio as gr
import requests

load_dotenv(override=True)

def push(name, email, notes):
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not slack_webhook_url:
        print("SLACK_WEBHOOK_URL not set", flush=True)
        return
    payload = {
        "text": f"New user interest recorded:\nName: {name}\nEmail: {email}\nNotes: {notes}",
    }
    try:
        response = requests.post(slack_webhook_url, json=payload)
        if response.status_code == 200:
            print("Slack notification sent", flush=True)
        else:
            print(f"Slack notification failed: {response.text}", flush=True)
    except Exception as e:
        print(f"Error sending Slack notification: {e}", flush=True)


def record_user_details(email, name="Name not provided", notes="not provided"):
    push(name, email, notes)
    return {"recorded": "ok"}

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            }
            ,
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": record_user_details_json}]

class Me:
    def __init__(self):
        self.openai = OpenAI(
            api_key=os.getenv("GOOGLE_API_KEY"), 
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.name = "Khushi Gandhi"

        # Load embeddings
        with open("embeddings.pkl", "rb") as f:
            self.embeddings = pickle.load(f)

        # Load local embedder
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

    def retrieve_relevant_chunks(self, query, top_k=5):
        query_embedding = self.embedder.encode(query)
        scores = []
        for item in self.embeddings:
            score = np.dot(query_embedding, item["embedding"])
            scores.append((score, item["chunk"]))
        scores.sort(reverse=True)
        return [chunk for _, chunk in scores[:top_k]]

    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results

    def system_prompt(self, retrieved_chunks):
        context = "\n\n".join(retrieved_chunks)
        contact_info = (
        "Name: Khushi Gandhi\n"
        "Email: khushiigandhi2405@gmail.com.com\n"
        "LinkedIn: https://www.linkedin.com/in/khushi2405/\n"
        "GitHub: https://github.com/Khushi2405\n"
        "Portfolio: https://khushi2405.github.io/my-portfolio/\n"
        "Resume: https://khushi2405.github.io/my-portfolio/assets/Khushi_Gandhi_Resume.pdf\n"
    )
        return f"""You are {self.name}, an expert professional representing yourself on your personal website.
        You answer visitors' questions about your career, skills, background, and personality.

        Guidelines for your responses:
        - Be approachable, knowledgeable, and professional.
        - Keep your answers formal, concise, and directly relevant to the question.
        - Use the information provided in the <context> to inform your answers, but **do not** copy the text verbatim.
        - If the answer is not clear from the context, respond honestly with "I don't know" or "I'm not sure."
        - If the visitor shows interest in staying in touch, ask politely for their name and email address.
        - Whenever a visitor provides their email, use the `record_user_details` tool to save their information.
        -- If the user asks for any contact information about you (your name, email, LinkedIn, GitHub, resume, etc.), reply with the following exact contact details:

        <contact_info>
        {contact_info}
        </contact_info>
        - Never fabricate information or guess beyond the provided context.

        Here is the context you can use to answer:

        <context>
        {context}
        </context>

        Answer as if you are {self.name}, speaking directly and respectfully to a visitor.
        """

    def chat(self, message, history):
        global tools
        relevant_chunks = self.retrieve_relevant_chunks(message)
        messages = [{"role": "system", "content": self.system_prompt(relevant_chunks)}] + history + [{"role": "user", "content": message}]
        done = False
        while not done:
            try:
                response = self.openai.chat.completions.create(
                    model="gemini-2.0-flash",
                    messages=messages,
                    tools=tools
                )

                if response.choices[0].finish_reason == "tool_calls":
                    message = response.choices[0].message
                    tool_calls = message.tool_calls
                    results = self.handle_tool_call(tool_calls)
                    messages.append(message)
                    messages.extend(results)
                else:
                    done = True

            except Exception as e:
                if "429" in str(e):
                    return "⚠️ Free tier usage limit reached. Please come back tomorrow."
                else:
                    return f"❌ An unexpected error occurred: {str(e)}"
        return response.choices[0].message.content
    

if __name__ == "__main__":
    me = Me()
    # Some available Gradio themes:
    # "default", "soft", "monochrome", "seafoam", "grass", "dracula", "huggingface", "freddyaboulton/dracula_revamped", "gstaff/xkcd", "gradio/monochrome"
    gr.ChatInterface(
        me.chat, 
        type="messages",
        title="Khushi Gandhi's Personal Assistant",
        description="<div style='text-align:center;'>Ask me anything about Khushi Gandhi's career, skills, and background. If you're interested in staying in touch, please provide your name and email address.</div>",
        examples=[
            ["Tell me about yourself."],
            ["Tell me about your most recent experience."],
            ["Talk about your recent projects."],
            ["How can I connect with you on LinkedIn?"],
            ["What are your main technical skills?"],
            ["Can I get your email address to stay in touch?"],
            ["What motivates you in your career?"],
            ["Talk about a challenging situation you faced recently?"]
        ],
        theme="grass"
    ).launch()
    
