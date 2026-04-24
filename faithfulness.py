"""
Faithfulness-Messung via Claim-Extraktion + NLI-Check (batched).

Methode:
1. Aus Antwort atomare Claims extrahieren (Mistral Medium)
2. Alle Claims × Chunks als Batch durch NLI (DeBERTa-v3-large, cross-encoder)
3. Aggregation: supported_rate, contradiction_rate, ungrounded_rate

Basis: RAGAS Faithfulness (Es et al. 2023) + FActScore (Min et al. 2023),
adaptiert für deutsches Legal-Text mit DeBERTa-v3-large.

Performance: Batched NLI statt per-pair — ~10x schneller auf CPU.
"""
import os
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

_NLI_MODEL_NAME = os.getenv(
    "OPENLEX_FAITHFULNESS_MODEL",
    "cross-encoder/nli-deberta-v3-large",
)

# Singleton NLI-Pipeline
_nli_model = None
_nli_tokenizer = None
_nli_device = None


def _load_nli():
    global _nli_model, _nli_tokenizer, _nli_device
    if _nli_model is not None:
        return
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    _nli_device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Loading NLI model {_NLI_MODEL_NAME} on {_nli_device}")
    print(f"  Loading NLI model {_NLI_MODEL_NAME} on {_nli_device}...")
    _nli_tokenizer = AutoTokenizer.from_pretrained(_NLI_MODEL_NAME)
    _nli_model = AutoModelForSequenceClassification.from_pretrained(_NLI_MODEL_NAME)
    _nli_model.to(_nli_device)
    _nli_model.eval()
    print(f"  NLI model loaded. Labels: {_nli_model.config.id2label}")


# === Claim-Extraktion via Mistral ===
_CLAIM_EXTRACTION_PROMPT = """Du bekommst eine juristische Antwort zu deutschem Datenschutzrecht.
Zerlege sie in atomare Behauptungen — eine klare, nachprüfbare Aussage pro Zeile.

Regeln:
1. Jede Behauptung steht für sich und enthält nur EINE Aussage.
2. Normverweise (z.B. "Art. 6 DSGVO") werden jeweils als eigene Behauptung erfasst.
3. Meta-Aussagen ("Nach meiner Einschätzung ...", "Vertiefende Prüfung wäre nötig") ausschließen.
4. Rein stilistische/sprachliche Elemente ausschließen.
5. Ausgabe: nur Behauptungen, eine pro Zeile, kein Präambel, keine Aufzählungsnummern.
6. Maximal 10 Behauptungen — wähle die inhaltlich wichtigsten.

Beispiel-Eingabe:
"Die Einwilligung nach Art. 6 Abs. 1 lit. a DSGVO muss freiwillig sein. Art. 7 DSGVO regelt die Bedingungen. Sie kann jederzeit widerrufen werden."

Beispiel-Ausgabe:
Die Einwilligung nach Art. 6 Abs. 1 lit. a DSGVO muss freiwillig sein.
Art. 7 DSGVO regelt die Bedingungen der Einwilligung.
Die Einwilligung kann jederzeit widerrufen werden.

Eingabe-Antwort:
{answer}

Behauptungen:"""


def extract_claims(answer: str, max_claims: int = 10) -> list:
    """Extrahiert atomare Claims via Mistral Medium (v2 SDK, MISTRAL_KEY)."""
    from mistralai.client import Mistral

    api_key = os.getenv("MISTRAL_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_KEY nicht gesetzt")

    client = Mistral(api_key=api_key, timeout_ms=20000)
    prompt = _CLAIM_EXTRACTION_PROMPT.format(answer=answer)

    response = client.chat.complete(
        model="mistral-medium-latest",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=800,
    )

    text = (response.choices[0].message.content or "").strip()
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    cleaned = []
    for line in lines:
        line = line.lstrip("0123456789.-*\u2022 )")
        line = line.strip()
        if line and len(line) > 10:
            cleaned.append(line)

    return cleaned[:max_claims]


# === NLI-Check (batched) ===
@dataclass
class ClaimVerdict:
    claim: str
    label: str          # "entailment", "neutral", "contradiction"
    score: float        # Konfidenz für Label
    evidence_excerpt: Optional[str] = None


def _nli_classify_batch(pairs: list, batch_size: int = 32) -> list:
    """
    Klassifiziert eine Liste von (premise, hypothesis)-Paaren als Batch.
    Returns: list of (label, score) tuples.

    ~10x schneller als per-pair auf CPU wegen amortisierter Tokenizer/Device-Overhead.
    """
    import torch
    _load_nli()

    all_results = []
    for start in range(0, len(pairs), batch_size):
        batch = pairs[start : start + batch_size]
        premises = [p[:800] for p, _ in batch]
        hypotheses = [h for _, h in batch]

        inputs = _nli_tokenizer(
            premises,
            hypotheses,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        ).to(_nli_device)

        with torch.no_grad():
            logits = _nli_model(**inputs).logits  # (batch, 3)

        probs = torch.softmax(logits, dim=-1).cpu()
        id2label = _nli_model.config.id2label

        for i in range(len(batch)):
            top_idx = int(torch.argmax(logits[i]).cpu())
            top_label = id2label[top_idx].lower()
            top_score = float(probs[i][top_idx])

            if "entail" in top_label:
                all_results.append(("entailment", top_score))
            elif "contradict" in top_label:
                all_results.append(("contradiction", top_score))
            else:
                all_results.append(("neutral", top_score))

    return all_results


def _nli_classify(premise: str, hypothesis: str) -> tuple:
    """Single-pair wrapper (für Tests)."""
    return _nli_classify_batch([(premise, hypothesis)])[0]


def check_claim_against_context(
    claim: str,
    context_chunks: list,
    entailment_threshold: float = 0.5,
) -> ClaimVerdict:
    """Prüft einen Claim gegen alle Context-Chunks. Bestes Entailment gewinnt."""
    pairs = [(chunk[:800], claim) for chunk in context_chunks if chunk and chunk.strip()]
    if not pairs:
        return ClaimVerdict(claim=claim, label="neutral", score=0.0)

    batch_results = _nli_classify_batch(pairs)

    best_entail_score = 0.0
    best_entail_excerpt = None
    any_contradict_score = 0.0
    any_contradict_excerpt = None

    for (chunk, _), (label, score) in zip(pairs, batch_results):
        if label == "entailment" and score > best_entail_score:
            best_entail_score = score
            best_entail_excerpt = chunk[:200]
        elif label == "contradiction" and score > any_contradict_score:
            any_contradict_score = score
            any_contradict_excerpt = chunk[:200]

    if best_entail_score >= entailment_threshold:
        return ClaimVerdict(claim, "entailment", best_entail_score, best_entail_excerpt)
    if any_contradict_score >= entailment_threshold:
        return ClaimVerdict(claim, "contradiction", any_contradict_score, any_contradict_excerpt)
    return ClaimVerdict(claim, "neutral", max(best_entail_score, any_contradict_score))


# === Aggregation ===
@dataclass
class FaithfulnessResult:
    total_claims: int
    supported: int
    contradicted: int
    ungrounded: int
    supported_rate: float
    contradiction_rate: float
    ungrounded_rate: float
    verdicts: list = field(default_factory=list)


def measure_faithfulness(
    answer: str,
    context_chunks: list,
    max_chunks: int = 5,
) -> FaithfulnessResult:
    """
    Misst Faithfulness einer Antwort gegen den genutzten Kontext.

    Alle (claim × chunk)-Paare werden als ein Batch durch NLI geschickt.

    Args:
        answer: LLM-generierte Antwort
        context_chunks: Liste von Chunk-Texten (top-N retrieved)
        max_chunks: Maximal so viele Chunks prüfen (default 5)
    """
    claims = extract_claims(answer)
    if not claims:
        return FaithfulnessResult(
            total_claims=0,
            supported=0, contradicted=0, ungrounded=0,
            supported_rate=0.0, contradiction_rate=0.0, ungrounded_rate=0.0,
            verdicts=[],
        )

    chunks_to_check = [c for c in context_chunks if c and c.strip()][:max_chunks]

    if not chunks_to_check:
        return FaithfulnessResult(
            total_claims=len(claims),
            supported=0, contradicted=0, ungrounded=len(claims),
            supported_rate=0.0, contradiction_rate=0.0, ungrounded_rate=1.0,
            verdicts=[ClaimVerdict(c, "neutral", 0.0) for c in claims],
        )

    # Alle (claim × chunk)-Paare als ein Batch
    # Layout: claim0×chunk0, claim0×chunk1, ..., claimN×chunkM
    all_pairs = []
    for claim in claims:
        for chunk in chunks_to_check:
            all_pairs.append((chunk[:800], claim))

    n_chunks = len(chunks_to_check)
    batch_labels = _nli_classify_batch(all_pairs)

    verdicts = []
    for ci, claim in enumerate(claims):
        best_entail_score = 0.0
        best_entail_excerpt = None
        any_contradict_score = 0.0
        any_contradict_excerpt = None

        for ki, chunk in enumerate(chunks_to_check):
            idx = ci * n_chunks + ki
            label, score = batch_labels[idx]
            if label == "entailment" and score > best_entail_score:
                best_entail_score = score
                best_entail_excerpt = chunk[:200]
            elif label == "contradiction" and score > any_contradict_score:
                any_contradict_score = score
                any_contradict_excerpt = chunk[:200]

        threshold = 0.5
        if best_entail_score >= threshold:
            verdicts.append(ClaimVerdict(claim, "entailment", best_entail_score, best_entail_excerpt))
        elif any_contradict_score >= threshold:
            verdicts.append(ClaimVerdict(claim, "contradiction", any_contradict_score, any_contradict_excerpt))
        else:
            verdicts.append(ClaimVerdict(claim, "neutral", max(best_entail_score, any_contradict_score)))

    supported = sum(1 for v in verdicts if v.label == "entailment")
    contradicted = sum(1 for v in verdicts if v.label == "contradiction")
    ungrounded = sum(1 for v in verdicts if v.label == "neutral")
    total = len(verdicts)

    return FaithfulnessResult(
        total_claims=total,
        supported=supported,
        contradicted=contradicted,
        ungrounded=ungrounded,
        supported_rate=round(supported / total, 4),
        contradiction_rate=round(contradicted / total, 4),
        ungrounded_rate=round(ungrounded / total, 4),
        verdicts=verdicts,
    )


# === generate_answer helper (für eval_faithfulness.py) ===
def generate_answer_from_chunks(question: str, chunks: list) -> str:
    """
    Thin wrapper: nimmt question + retrieved chunks, gibt vollständige LLM-Antwort zurück.
    Nutzt die bestehende stream_with_fallback-Pipeline aus app.py.
    """
    import sys
    sys.path.insert(0, "/opt/openlex-mvp")
    from app import _build_llm_messages, format_context, stream_with_fallback

    context = format_context(chunks)
    messages = _build_llm_messages(question, context, [])

    full_response = ""
    for token, _ in stream_with_fallback(messages):
        full_response += token

    return full_response.strip()
