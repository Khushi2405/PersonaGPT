import os
import json
import pickle
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from openai import OpenAI
import gradio as gr
import certifi
import smtplib, ssl
from email.message import EmailMessage
from supabase import create_client

load_dotenv(override=True)
os.environ['SSL_CERT_FILE'] = certifi.where()

def log_email_db(name : str, email : str):
    try:
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY")
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        data = {
            "name": name,
            "email": email
        }
    
        response = supabase.table("emails_sent").insert(data).execute()
        print(f"Supabase insert successful: {response} ", flush=True)
    except Exception as e:
        print(f"Error inserting into Supabase: {e}", flush=True)


def record_user_details(email, name):
    print(f"Recording user details: {name}, {email}", flush=True)
    if name is None or name.strip() == "":
        name = email.split('@')[0]
    log_email_db(name, email)
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
        self.sections = [item["section"] for item in self.embeddings]
        self.behavioral_sections = ["Experience", "Projects", "Recommendations", "About Me"]

        print(f"Available sections: {self.sections}", flush=True)


    def get_intent_section(self, query):
        system = "Classify the user's intent into one of:\n" + "\n".join(self.sections) + "\n" + "behavioral" + "\n\n" + \
                  "Respond with the section name that best matches the user's intent, in lowercase."
        try:
            response = self.openai.chat.completions.create(
                model="gemini-2.0-flash",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": query}
                ]
            )
            intent_section = response.choices[0].message.content.strip().lower()
            if intent_section not in [s.lower() for s in self.sections] + ["behavioral"]:
                raise ValueError("Invalid intent from LLM")
        except Exception as e:
            print(f"LLM intent classification failed: {e}, falling back to embedding similarity", flush=True)

            # Fallback: embedding similarity to find intent section
            query_embedding = self.embedder.encode(query).reshape(1, -1)
            section_embeddings = []
            section_names = []
            for item in self.embeddings:
                # One embedding per section, so avoid duplicates
                if item["section"] not in section_names:
                    section_names.append(item["section"])
                    section_embeddings.append(np.array(item["embedding"]))
            corpus_embeddings = np.vstack(section_embeddings)
            similarities = cosine_similarity(query_embedding, corpus_embeddings)[0]
            max_idx = similarities.argmax()
            intent_section = section_names[max_idx].lower()
        return intent_section
    
    def retrieve_relevant_chunks(self, query, top_k=5):
        intent_section = self.get_intent_section(query)
        print(f"Detected intent section: {intent_section}", flush=True)

        if intent_section == "behavioral":
        # For behavioral questions, retrieve from multiple sections
            filtered = [item for item in self.embeddings if item["section"] in self.behavioral_sections]
        else:
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
        
        return f"""You are {self.name}, an expert professional representing yourself to recruiters.
        You answer visitors' questions about your career, skills, background, and personality. 
        When answering behavioral questions (e.g., about teamwork, challenges, leadership, motivation), do NOT use scripted stories. Instead, synthesize examples from your experience, projects, recommendations, and about me sections in the context.
        Answer in a natural, storytelling style that highlights the (STAR format) Situation, Task, Action, and Result.
        If you don't find any relevant situation to answer a behavioral question start with "I haven’t encountered that exact situation yet, but here’s how I would approach it" and the continue with the approachh which is relevant to me.
        
        Guidelines for your responses:
        - Be friendly, thoughtful, and authentic in tone.
        - Let your natural excitement for learning and solving problems shine through.
        - Show curiosity when relevant, and speak as someone who genuinely enjoys building and growing.
        - Keep responses clear, concise, and warm—use a conversational tone, but stay professional.
        - Use the information provided in the <context> to inform your answers, but **do not** copy the text verbatim.
        - If the answer is not clear from the context, respond honestly with "I don't know" or "I'm not sure."
        - Try to keep the conversation going naturally.
        - Prompt the visitor to stay in touch when appropriate, especially if they ask for any contact information.
        - If the visitor shows interest in staying in touch, ask politely for their name and email address.
        - Whenever a visitor provides their email, use the `record_user_details` tool to save their information.
        - If you have just used the `record_user_details` tool to save a visitor's email, reply with a warm thank you message and let them know you will send them a follow-up email. Be sure to mention to check their spam folder just in case.
        - Never fabricate information or guess beyond the provided context.
        Here is the context you can use to answer:

        <context>
        {context}
        </context>

        Answer as if you are {self.name}, speaking directly and respectfully to a visitor.
        Format your response with \n\n as the paragraph separator.       
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
    
