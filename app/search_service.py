import re
from collections import Counter

from .config import (
    CHUNK_WORDS,
    MAX_CONTEXT_CHARACTERS,
    STOPWORDS,
    TOP_CHUNKS_PER_QUESTION,
)


def split_into_chunks(text: str, words_per_chunk: int = CHUNK_WORDS) -> list[str]:
    words = text.split()
    chunks = []
    for index in range(0, len(words), words_per_chunk):
        chunk = " ".join(words[index:index + words_per_chunk])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def tokenize(text: str) -> list[str]:
    words = re.findall(
        r"[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ0-9]+",
        text.lower(),
    )
    return [
        word
        for word in words
        if len(word) >= 3 and word not in STOPWORDS
    ]


def score_chunk(question_words: list[str], chunk_words: list[str]) -> float:
    if not question_words or not chunk_words:
        return 0

    counter = Counter(chunk_words)
    score = 0
    for word in question_words:
        if word in counter:
            score += 1
            score += min(counter[word] - 1, 2) * 0.25
    return score


def find_relevant_chunks(question: str, chunks: list[str]) -> list[str]:
    question_words = tokenize(question)
    scored = [
        (score_chunk(question_words, tokenize(chunk)), chunk)
        for chunk in chunks
    ]
    scored.sort(key=lambda item: item[0], reverse=True)

    if not scored:
        return []
    if scored[0][0] == 0:
        return chunks[:TOP_CHUNKS_PER_QUESTION]
    return [chunk for score, chunk in scored[:TOP_CHUNKS_PER_QUESTION]]


def build_context(questions: list[str], chunks: list[str]) -> str:
    contexts = []
    already_used = set()
    separator = "\n\n---\n\n"

    for number, question in enumerate(questions, start=1):
        question_context = []
        for chunk in find_relevant_chunks(question, chunks):
            chunk_id = hash(chunk)
            if chunk_id in already_used:
                continue
            already_used.add(chunk_id)
            question_context.append(chunk)

        contexts.append(
            f"""
===== PYTANIE {number} =====

{question}

RELEVANTNE FRAGMENTY:

{separator.join(question_context)}
"""
        )

    return "\n".join(contexts)[:MAX_CONTEXT_CHARACTERS]
