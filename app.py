import os
import json
import pickle
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
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
        with open("embeddings_by_section.pkl", "rb") as f:
            self.embeddings = pickle.load(f)

        # Load local embedder
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

        # Get all unique sections in embeddings
        self.sections = list(set(item["section"] for item in self.embeddings))
        print(f"Available sections: {self.sections}", flush=True)

        self.section_aliases = {
            "Experience": ["experience", "work", "job", "internship", "role", "position", "employment", "career"],
            "Projects": ["projects", "work", "built", "created", "developed"],
            "Education": ["education", "university", "degree", "courses", "academics"],
            "Skills": ["skills", "tech stack", "technologies", "tools"],
            "Certifications": ["certifications", "licenses"],
            "Recommendations": ["recommendations", "testimonials", "feedback"],
            "Contact": ["phone", "contact", "email", "linkedin", "github", "portfolio"]
        }

        # Prepare section embeddings by combining section names with aliases
        self.section_embeddings = {}
        for section in self.sections:
            aliases = self.section_aliases.get(section, [])
            combined_text = section + " " + " ".join(aliases)
            self.section_embeddings[section] = self.embedder.encode(combined_text).reshape(1, -1)

    def get_intent_section(self, query):
        # query_emb = self.embedder.encode(query).reshape(1, -1)
        # max_sim = -1
        # best_section = None
        # for section, emb in self.section_embeddings.items():
        #     sim = cosine_similarity(query_emb, emb)[0][0]
        #     if sim > max_sim:
        #         max_sim = sim
        #         best_section = section
        # return best_section
        system = "Classify the user's intent into one of:\n" + "\n".join(self.sections) + "\n\n" + \
                  "Respond with the section name that best matches the user's intent, in lowercase."
        response = self.openai.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": query}
            ]
        )
        return response.choices[0].message.content.strip().lower()
    
    def retrieve_relevant_chunks(self, query, top_k=5):
        intent_section = self.get_intent_section(query)
        print(f"Detected intent section: {intent_section}", flush=True)

        # Filter chunks by section detected from intent
        filtered = [item for item in self.embeddings if item["section"] == intent_section]

        # If no filtered chunks found (fallback), use all
        if not filtered:
            filtered = self.embeddings

        query_embedding = self.embedder.encode(query).reshape(1, -1)
        corpus_embeddings = np.array([item["embedding"] for item in filtered])
        similarities = cosine_similarity(query_embedding, corpus_embeddings)[0]
        top_indices = similarities.argsort()[::-1][:top_k]
        return [filtered[i]["chunk"] for i in top_indices]

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
        
        return f"""You are {self.name}, an expert professional representing yourself on your personal website.
        You answer visitors' questions about your career, skills, background, and personality.

        Guidelines for your responses:
        - Be friendly, thoughtful, and authentic in tone.
        - Let your natural excitement for learning and solving problems shine through.
        - Show curiosity when relevant, and speak as someone who genuinely enjoys building and growing.
        - Keep responses clear, concise, and warm—use a conversational tone, but stay professional.
        - Use the information provided in the <context> to inform your answers, but **do not** copy the text verbatim.
        - If the answer is not clear from the context, respond honestly with "I don't know" or "I'm not sure."
        - If the visitor shows interest in staying in touch, ask politely for their name and email address.
        - Whenever a visitor provides their email, use the `record_user_details` tool to save their information.
        - Never fabricate information or guess beyond the provided context.

        Here is the context you can use to answer:

        <context>
        {context}
        </context>

        Answer as if you are {self.name}, speaking directly and respectfully to a visitor.
        Format your response with \n\n as the paragraph separator.       """

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
            ["Tell me about yourself and your interests."],
            ["Tell me about your most recent experience."],
            ["Talk about your recent projects."],
            ["How can I connect with you on LinkedIn?"],
            ["What are your main technical skills?"],
            ["Can I get your email address to stay in touch?"],
            ["What motivates you in your career?"],
            ["Talk about a challenging situation you faced recently?"]
        ],
        theme="soft"
    ).launch()
    
