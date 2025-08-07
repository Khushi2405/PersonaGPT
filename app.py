import os
import json
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr
import certifi
from supabase import create_client
import re

load_dotenv(override=True)
os.environ['SSL_CERT_FILE'] = certifi.where()

def split_by_sections():
    with open("me/details.txt", "r", encoding="utf-8") as f:
        full_text = f.read()
    pattern = r"(=== .*? ===)"
    parts = re.split(pattern, full_text)
    
    # Combine section titles with content
    sections = []
    for i in range(1, len(parts), 2):
        title = parts[i].strip("= ").strip().lower()
        content = parts[i + 1].strip()
        sections.append({
            "title" : title,
            "content" : content
            })
    return sections

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
        
        self.details = split_by_sections()
        # Get all unique sections in embeddings
        self.sections = [item["title"] for item in self.details]

        print(f"Available sections: {self.sections}", flush=True)

        # Load saved answers
        with open("me/saved_answers.json", "r") as f:
            self.example_answers = json.load(f)


    def get_intent_section(self, query):
        system = "Classify the user's intent into one of:\n" + "\n".join(self.sections) + "\n" + "behavioral" + "\n\n" + \
                  "Respond with the section name that best matches the user's intent, in lowercase."
        
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
        return [item["content"] for item in self.details if item["title"].lower() == intent_section]
    
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
        
        return f"""You are {self.name}, a seasoned professional sharing your career story with curiosity, warmth, and professionalism. You are answering career-related questions from recruiters, peers, or potential employers.

    You respond to questions about your skills, experience, challenges, motivations, and personality. Always speak directly, with clarity and warmth—like you would in a thoughtful one-on-one conversation.

    **When answering behavioral questions** (e.g., teamwork, leadership, conflict, growth):
    - Follow the STAR format (Situation, Task, Action, Result), but weave it into a fluid narrative. Don’t label each section explicitly.
    - If you haven't faced the exact situation, begin with: “I haven’t encountered that exact situation yet, but here’s how I’d approach it...” and continue with a realistic, relevant plan based on your experience and thinking.

    **Tone & Style Guidelines:**
    - Use a natural storytelling style, not a scripted or robotic one.
    - Be authentic, friendly but professional, raw, thoughtful and engaging.
    - Show your natural enthusiasm for learning, solving problems, and collaborating.
    - Keep responses concise but insightful. Aim for clarity and flow.
    - Keep the conversation flowing, ask follow-up questions to keep the user engaged.
    - Use emojis very rarely to add warmth, but not in subsequent messages.
    - Format with two line breaks between paragraphs \n\n for readability.

    **Important Notes:**
    - Use the <context> section only for reference to formulate your response,**never copy it verbatim.**
    - If something isn't clear from the context, say “I’m not sure,” or “I don’t know.”
    - If someone asks for any contact info, invite them to stay in touch and ask for their name and email.
    - If they provide their details, use the `record_user_details` tool and send a friendly confirmation (suggest checking spam just in case).
    - Never invent details or go beyond the context provided.

    <context>
    {context}
    </context>

    Answer in the voice of {self.name}, speaking directly to the person asking. Make sure your response reads naturally and is well-formatted with paragraph breaks using `\\n\\n`.
    """
    def chat(self, message, history):
        global tools
        print(f"History: {history}", flush=True)
        if message.strip() in self.example_answers:
            print(f"Using example answer for: {message.strip()}", flush=True)
            return self.example_answers[message.strip()]
        try:
            relevant_content = self.get_intent_section(message)
        except Exception as e:
            print(f"Error getting intent section: {e}", flush=True)
            return "❌ I couldn't understand your question. Please try rephrasing it or ask something else."
        
        print(f"Relevant chunks: {relevant_content}", flush=True)
        messages = [{"role": "system", "content": self.system_prompt(relevant_content)}] + history + [{"role": "user", "content": message}]
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
                print(f"Error during chat completion: {e}", flush=True)
                return "❌ This conversation has reached the maximum length. Please start a new one."
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
            *[ [question] for question in me.example_answers.keys() ]
        ],
        theme="soft"
    ).launch()
    
