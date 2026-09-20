import os

from dotenv import load_dotenv


load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "openai/gpt-oss-120b")
CHUNK_WORDS = 500
TOP_CHUNKS_PER_QUESTION = 3
MAX_CONTEXT_CHARACTERS = 18000

STOPWORDS = {
    "i", "a", "oraz", "lub", "czy", "jest", "są", "być",
    "do", "od", "na", "w", "we", "z", "ze", "za", "dla",
    "po", "przy", "o", "u", "nad", "pod", "przez",
    "jaki", "jaka", "jakie", "jakich", "jakim", "jaką",
    "co", "czego", "który", "która", "które", "których",
    "ten", "ta", "to", "te", "tych",
    "się", "nie", "tak", "ma", "mieć",
    "wynosi", "dotyczy", "należy", "może",
}


if not GROQ_API_KEY:
    raise RuntimeError("Brak GROQ_API_KEY w pliku .env")
