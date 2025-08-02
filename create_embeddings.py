import pickle
from sentence_transformers import SentenceTransformer


# Initialize sentence transformer model
model = SentenceTransformer("all-MiniLM-L6-v2")  # or another embedding model

def chunk_text(text, max_length=500):
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) < max_length:
            current_chunk += para + "\n\n"
        else:
            chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def main():
    # Load your documents
    with open("me/linkedin.txt", "r", encoding="utf-8") as f:
        linkedin_text = f.read()
    with open("me/resume.txt", "r", encoding="utf-8") as f:
        resume_text = f.read()
    with open("me/about_me.txt", "r", encoding="utf-8") as f:
        about_me_text = f.read()

    all_text = linkedin_text + "\n\n" + resume_text + "\n\n" + about_me_text
    chunks = chunk_text(all_text)

    data = []
    for chunk in chunks:
        embedding = model.encode(chunk).tolist()
        data.append({
            "chunk": chunk,
            "embedding": embedding
        })

    with open("embeddings.pkl", "wb") as f:
        pickle.dump(data, f)

    print(f"Created and saved {len(data)} embeddings.")

if __name__ == "__main__":
    main()
