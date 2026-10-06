"""One-time model download into the ignored local workspace; runtime stays offline."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from sentence_transformers import SentenceTransformer
from server.knowledge import MODEL_DIR

def main():
    MODEL_DIR.parent.mkdir(parents=True,exist_ok=True)
    if (MODEL_DIR/'modules.json').exists():
        print('Embedding model already present:',MODEL_DIR)
        return
    model=SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2',device='cpu',cache_folder=str(MODEL_DIR.parent/'cache'))
    model.save_pretrained(str(MODEL_DIR))
    print('Saved local embedding model:',MODEL_DIR)
    print('Vector dimensions:',model.get_sentence_embedding_dimension())

if __name__=='__main__': main()
