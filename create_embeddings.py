import re
from sentence_transformers import SentenceTransformer
import pickle

model = SentenceTransformer("all-MiniLM-L6-v2")

def split_by_sections(text):
    pattern = r"(=== .*? ===)"
    parts = re.split(pattern, text)
    
    # Combine section titles with content
    sections = []
    for i in range(1, len(parts), 2):
        title = parts[i].strip("= ").strip()
        content = parts[i + 1].strip()
        sections.append((title, content))
    return sections

def main():
    with open("me/details.txt", "r", encoding="utf-8") as f:
        full_text = f.read()

    sections = split_by_sections(full_text)

    data = []
    for title, content in sections:
        embedding = model.encode(content).tolist()
        data.append({
            "section": title,
            "chunk": content,
            "embedding": embedding
        })

    with open("embeddings_by_section.pkl", "wb") as f:
        pickle.dump(data, f)

    print(f"Created {len(data)} section-based embeddings.")

if __name__ == "__main__":
    main()
