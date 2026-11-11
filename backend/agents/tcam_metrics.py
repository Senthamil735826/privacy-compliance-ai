"""
Automated evidence-quality and task-complexity metric calculator for TCAM.

Computes:
1. Inherent Difficulty (H) calibrated from benchmark empirical difficulty and rule taxonomy.
2. Evidence Recall / Coverage Proxy (R) without conflating max similarity with true recall.
3. Evidence Dispersion (D) measuring spatial and structural chunk spread across document.
4. Semantic Ambiguity (A) using similarity distribution flatness, hedging, and conflicts.
"""

from dataclasses import asdict, dataclass
import math
import re
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# 1. BENCHMARK-CALIBRATED INHERENT DIFFICULTY (H_i)
# ============================================================================

# Calibrated using empirical benchmark validation (evaluation_dataset.json & rule complexity)
# Scale: 0.0 (trivial, explicit metadata) to 1.0 (highly subjective, multi-jurisdictional legal interpretation)
CALIBRATED_INHERENT_DIFFICULTY: Dict[str, float] = {
    # Primary Category A1: Document Metadata & Identity (Low difficulty)
    "B1": 0.15,   # Privacy Policy Name (explicit header)
    "B2": 0.35,   # Technical Data Collection
    "B3": 0.15,   # Effective Date (explicit timestamp/date)
    "B4": 0.20,   # Version Number
    "B5": 0.25,   # Scope / Applicability
    "B6": 0.20,   # Contact Information (email, address)

    # Primary Category A2: Data Collection & Purposes (Moderate difficulty)
    "B7": 0.40,   # User Account Credentials / Personal Identifiers
    "B8": 0.45,   # Device Identifiers (IMEI, MAC, IP)
    "B9": 0.35,   # Cookies and Tracking SDKs
    "B10": 0.45,  # Geolocation Data
    "B11": 0.55,  # Biometric / Health Data (Sensitive)
    "B12": 0.45,  # Purpose Specification

    # Primary Category A3: Legal Basis & Consent (High difficulty)
    "B13": 0.75,  # Legal Basis (GDPR Art 6, Legitimate Interests)
    "B14": 0.65,  # Consent Mechanisms & Revocation
    "B15": 0.80,  # Cross-Border Data Transfers (SCCs, Adequacy)

    # Primary Category A4: Retention & Storage (Moderate to High)
    "B16": 0.60,  # Specific Retention Durations
    "B17": 0.55,  # Deletion Procedures
    "B18": 0.50,  # Storage Location
    "B19": 0.60,  # Inactive Account Purging
    "B20": 0.45,  # Data Minimization
    "B21": 0.50,  # Security Safeguards
    "B22": 0.70,  # Security Incident & Breach Notification

    # Primary Category A5: Sharing & Third Parties
    "B23": 0.60,  # Third-Party Categories
    "B24": 0.65,  # Analytics Providers
    "B25": 0.70,  # Advertising Networks
    "B26": 0.75,  # Sale of Personal Information (CCPA/CPRA)
    "B27": 0.70,  # Law Enforcement Disclosure

    # Primary Category A6: User Rights & Redress
    "B28": 0.50,  # Right to Access
    "B29": 0.50,  # Right to Rectification
    "B30": 0.55,  # Right to Erasure / Deletion
    "B31": 0.60,  # Right to Data Portability
    "B32": 0.65,  # Right to Restrict Processing
    "B33": 0.65,  # Right to Object
    "B34": 0.55,  # Right to Lodge Complaint

    # Primary Category A7: Special Protections
    "B35": 0.70,  # Children's Privacy (COPPA)
    "B36": 0.75,  # Policy Change Notification
    "B37": 0.80,  # Automated Decision Making / Profiling
    "B38": 0.75,  # Do Not Track Signals
    "B39": 0.70,  # Third-Party Links
    "B40": 0.60,  # Data Protection Officer Details
}

# Fallback by primary category when secondary ID is unlisted
PRIMARY_DIFFICULTY_FALLBACK: Dict[str, float] = {
    "A1": 0.20,  # Metadata
    "A2": 0.45,  # Data Collection & Use
    "A3": 0.70,  # Legal Basis
    "A4": 0.55,  # Retention & Security
    "A5": 0.68,  # Third-Party Disclosures
    "A6": 0.55,  # Subject Rights
    "A7": 0.72,  # Special Protections
}


# ============================================================================
# 2. LINGUISTIC HEDGE & AMBIGUITY LEXICON
# ============================================================================

LEGAL_HEDGES = [
    r"\bmay\b",
    r"\bmight\b",
    r"\bcould\b",
    r"\bwhere applicable\b",
    r"\bfrom time to time\b",
    r"\bas reasonably necessary\b",
    r"\bto the extent permitted\b",
    r"\bat our discretion\b",
    r"\bcertain circumstances\b",
    r"\bincluding but not limited to\b",
    r"\bperiodic(?:ally)?\b",
    r"\bwhere feasible\b",
    r"\bsubject to\b",
    r"\bsome\b",
]

CONTRADICTION_PAIRS = [
    (r"\bdo not collect\b", r"\bcollect\b"),
    (r"\bnever share\b", r"\bshare\b"),
    (r"\bdo not sell\b", r"\bsell\b"),
    (r"\bno personal data\b", r"\bpersonal data\b"),
]


# ============================================================================
# 3. STRUCTURED DATA TRANSFER OBJECTS
# ============================================================================

@dataclass(frozen=True)
class TCAMMetricExplanation:
    """Detailed mathematical explanation of calculated TCAM metrics."""

    inherent_difficulty: float
    inherent_difficulty_rationale: str

    evidence_recall: float
    evidence_recall_rationale: str
    lexical_coverage_score: float
    semantic_density_score: float

    evidence_dispersion: float
    evidence_dispersion_rationale: str
    chunk_span: float
    referenced_chunks: List[int]

    semantic_ambiguity: float
    semantic_ambiguity_rationale: str
    distribution_entropy: float
    hedge_density: float

    evidence_scarcity: float
    complexity_score: float
    routing_decision: int
    complexity_level: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# 4. METRIC COMPUTATION LOGIC
# ============================================================================

def get_calibrated_inherent_difficulty(
    indicator_id: str,
    primary_indicator_id: str = "A1"
) -> Tuple[float, str]:
    """Retrieve calibrated difficulty score with explanation."""
    clean_id = (indicator_id or "").strip().upper()
    clean_prim = (primary_indicator_id or "A1").strip().upper()

    if clean_id in CALIBRATED_INHERENT_DIFFICULTY:
        score = CALIBRATED_INHERENT_DIFFICULTY[clean_id]
        rationale = (
            f"Indicator {clean_id} calibrated inherent difficulty is {score:.2f} "
            f"based on empirical benchmark evaluation and statutory complexity."
        )
        return score, rationale

    score = PRIMARY_DIFFICULTY_FALLBACK.get(clean_prim, 0.50)
    rationale = (
        f"Indicator {clean_id} assigned fallback difficulty {score:.2f} "
        f"from primary statutory category {clean_prim}."
    )
    return score, rationale


def extract_concept_keywords(indicator_description: str) -> List[str]:
    """Extract substantive legal/compliance terms from indicator description."""
    if not indicator_description:
        return []
    words = re.findall(r"\b[A-Za-z]{3,}\b", indicator_description.lower())
    stopwords = {
        "the", "and", "for", "with", "that", "this", "from", "are", "which",
        "does", "policy", "state", "user", "data", "information", "provides",
        "specifies", "identifies", "discloses", "procedures", "affected"
    }
    concepts = [w for w in words if w not in stopwords]
    return list(dict.fromkeys(concepts))  # preserve order unique


def calculate_evidence_recall_proxy(
    *,
    evidence_text: str,
    indicator_description: str,
    retrieved_chunks: Optional[List[Dict[str, Any]]] = None,
    relevance_threshold: float = 0.35,
) -> Tuple[float, float, float, str]:
    """
    Calculate Evidence Coverage Proxy without equating max cosine similarity to true recall.

    Coverage Proxy = 0.5 * LexicalConceptCoverage + 0.5 * SemanticQualityDensity
    """
    clean_ev = (evidence_text or "").strip().lower()
    if not clean_ev:
        return 0.0, 0.0, 0.0, "Evidence is empty; coverage proxy is 0.0."

    # 1. Lexical Concept Coverage
    concepts = extract_concept_keywords(indicator_description)
    if concepts:
        matched_concepts = [c for c in concepts if c in clean_ev]
        lexical_cov = len(matched_concepts) / len(concepts)
    else:
        # Fallback if no specific keywords: evaluate text richness
        lexical_cov = min(1.0, len(clean_ev.split()) / 40.0)

    # 2. Semantic Quality Density
    if retrieved_chunks:
        # Extract similarities
        similarities = [
            float(c.get("similarity", 0.0))
            for c in retrieved_chunks
            if isinstance(c.get("similarity"), (int, float))
        ]
        if similarities:
            # Fraction of chunks exceeding baseline relevance
            relevant_sims = [s for s in similarities if s >= relevance_threshold]
            if relevant_sims:
                avg_rel = sum(relevant_sims) / len(relevant_sims)
                # Normalized between relevance_threshold (0.35) and ideal upper bound (0.80)
                sem_density = min(1.0, max(0.0, (avg_rel - relevance_threshold) / (0.80 - relevance_threshold)))
            else:
                sem_density = max(0.0, max(similarities) * 0.5)
        else:
            sem_density = 0.5
    else:
        # Standalone evidence passage without FAISS vector index
        # Proxy semantic density using word count and sentence completeness
        words = clean_ev.split()
        sem_density = min(1.0, len(words) / 30.0)

    recall_proxy = min(1.0, max(0.0, 0.5 * lexical_cov + 0.5 * sem_density))
    rationale = (
        f"Coverage proxy R={recall_proxy:.2f} derived from {len(matched_concepts if concepts else [])}/"
        f"{len(concepts)} statutory concepts ({lexical_cov:.2f}) and semantic evidence density ({sem_density:.2f})."
    )
    return recall_proxy, lexical_cov, sem_density, rationale


def calculate_evidence_dispersion(
    *,
    evidence_text: str,
    retrieved_chunks: Optional[List[Dict[str, Any]]] = None,
    total_document_chunks: Optional[int] = None,
) -> Tuple[float, float, List[int], str]:
    """
    Calculate evidence dispersion across document chunks and pages.

    D = 0.0 if evidence is localized in 1 chunk.
    D -> 1.0 if supporting evidence is fragmented across multiple far-apart document locations.
    """
    chunk_ids: List[int] = []

    if retrieved_chunks:
        for c in retrieved_chunks:
            cid = c.get("chunk_id")
            sim = float(c.get("similarity", 0.0))
            # Include chunks that have positive relevance
            if cid is not None and sim >= 0.30:
                try:
                    chunk_ids.append(int(cid))
                except (ValueError, TypeError):
                    pass

    if not chunk_ids:
        # Evaluate passage paragraphs if no FAISS chunks are provided
        paragraphs = [p for p in (evidence_text or "").split("\n\n") if p.strip()]
        if len(paragraphs) <= 1:
            return 0.0, 0.0, [], "Evidence localized within a single passage (dispersion D=0.00)."
        
        para_disp = min(1.0, (len(paragraphs) - 1) / 5.0)
        return (
            para_disp,
            para_disp,
            [],
            f"Evidence dispersed across {len(paragraphs)} separate paragraphs (dispersion D={para_disp:.2f})."
        )

    chunk_ids = sorted(list(set(chunk_ids)))
    if len(chunk_ids) <= 1:
        return 0.0, 0.0, chunk_ids, f"Evidence concentrated in chunk {chunk_ids[0]} (dispersion D=0.00)."

    tot = total_document_chunks or max(max(chunk_ids), 10)
    norm_positions = [cid / tot for cid in chunk_ids]
    span = max(norm_positions) - min(norm_positions)

    # Compute standard deviation of positions
    mean_pos = sum(norm_positions) / len(norm_positions)
    variance = sum((p - mean_pos) ** 2 for p in norm_positions) / len(norm_positions)
    std_dev = math.sqrt(variance)

    # Scale dispersion: span (60%) + std_dev normalized by max 0.5 (40%)
    dispersion = min(1.0, max(0.0, 0.6 * span + 0.4 * (std_dev / 0.5)))
    rationale = (
        f"Evidence scattered across chunks {chunk_ids} spanning {span * 100:.1f}% of document "
        f"(dispersion D={dispersion:.2f})."
    )
    return dispersion, span, chunk_ids, rationale


def calculate_semantic_ambiguity(
    *,
    evidence_text: str,
    retrieved_chunks: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[float, float, float, str]:
    """
    Calculate semantic ambiguity from similarity distributions, hedging, and contradictions.

    A -> 1.0 when similarity scores are flat/ambiguous and legal language contains strong hedges.
    A -> 0.0 when top similarity has a decisive margin and explicit declarative phrasing.
    """
    clean_ev = (evidence_text or "").strip().lower()
    if not clean_ev:
        return 1.0, 1.0, 1.0, "Evidence is absent; semantic ambiguity is maximized (A=1.00)."

    # 1. Similarity score flatness / margin
    sim_ambiguity = 0.5
    if retrieved_chunks and len(retrieved_chunks) >= 2:
        sims = [
            float(c.get("similarity", 0.0))
            for c in retrieved_chunks
            if isinstance(c.get("similarity"), (int, float))
        ]
        if len(sims) >= 2:
            top_sim = max(sims)
            second_sim = sorted(sims, reverse=True)[1]
            margin = top_sim - second_sim  # Larger margin -> less ambiguity
            # Margin of 0.20+ indicates decisive top candidate
            sim_ambiguity = min(1.0, max(0.0, 1.0 - (margin / 0.20)))

    # 2. Linguistic hedges
    hedge_count = 0
    for hedge_pattern in LEGAL_HEDGES:
        hedge_count += len(re.findall(hedge_pattern, clean_ev))

    sentences = [s for s in re.split(r"[.!?]+", clean_ev) if s.strip()]
    sentence_count = max(1, len(sentences))
    hedge_density = min(1.0, hedge_count / (sentence_count * 2.0))

    # 3. Contradiction check
    has_contradiction = False
    for pos_pat, neg_pat in CONTRADICTION_PAIRS:
        if re.search(pos_pat, clean_ev) and re.search(neg_pat, clean_ev):
            has_contradiction = True
            break
    conflict_factor = 0.35 if has_contradiction else 0.0

    ambiguity = min(1.0, max(0.0, 0.45 * sim_ambiguity + 0.45 * hedge_density + conflict_factor))
    rationale = (
        f"Ambiguity A={ambiguity:.2f} (similarity margin flatness: {sim_ambiguity:.2f}, "
        f"hedge count: {hedge_count} in {sentence_count} sentences, "
        f"contradiction: {'detected' if has_contradiction else 'none'})."
    )
    return ambiguity, sim_ambiguity, hedge_density, rationale


# ============================================================================
# 5. MASTER INTEGRATOR FUNCTION
# ============================================================================

def compute_automated_tcam_metrics(
    *,
    indicator_id: str,
    indicator_description: str,
    primary_indicator_id: str,
    evidence_text: str,
    retrieved_chunks: Optional[List[Dict[str, Any]]] = None,
    total_document_chunks: Optional[int] = None,
) -> TCAMMetricExplanation:
    """
    Orchestrate full automated metric calculation and TCAM complexity routing.
    """
    # 1. Inherent Difficulty
    difficulty, diff_rationale = get_calibrated_inherent_difficulty(
        indicator_id=indicator_id,
        primary_indicator_id=primary_indicator_id,
    )

    # 2. Evidence Recall / Coverage Proxy
    recall, lex_cov, sem_dens, rec_rationale = calculate_evidence_recall_proxy(
        evidence_text=evidence_text,
        indicator_description=indicator_description,
        retrieved_chunks=retrieved_chunks,
    )

    # 3. Evidence Dispersion
    dispersion, span, chunk_ids, disp_rationale = calculate_evidence_dispersion(
        evidence_text=evidence_text,
        retrieved_chunks=retrieved_chunks,
        total_document_chunks=total_document_chunks,
    )

    # 4. Semantic Ambiguity
    ambiguity, sim_amb, hedge_dens, amb_rationale = calculate_semantic_ambiguity(
        evidence_text=evidence_text,
        retrieved_chunks=retrieved_chunks,
    )

    # 5. TCAM Scarcity & Complexity Equations
    # S_i = 1 - [1/3*R + 1/3*(1-D) + 1/3*(1-A)]
    evidence_scarcity = 1.0 - (
        (1.0 / 3.0) * recall
        + (1.0 / 3.0) * (1.0 - dispersion)
        + (1.0 / 3.0) * (1.0 - ambiguity)
    )
    evidence_scarcity = min(1.0, max(0.0, evidence_scarcity))

    # theta = 0.5 * H + 0.5 * S
    complexity = 0.5 * difficulty + 0.5 * evidence_scarcity
    complexity = min(1.0, max(0.0, complexity))

    # Threshold routing
    if complexity < 0.40:
        routing = 1
        level = "low"
    elif complexity < 0.70:
        routing = 3
        level = "medium"
    else:
        routing = 5
        level = "high"

    return TCAMMetricExplanation(
        inherent_difficulty=round(difficulty, 4),
        inherent_difficulty_rationale=diff_rationale,
        evidence_recall=round(recall, 4),
        evidence_recall_rationale=rec_rationale,
        lexical_coverage_score=round(lex_cov, 4),
        semantic_density_score=round(sem_dens, 4),
        evidence_dispersion=round(dispersion, 4),
        evidence_dispersion_rationale=disp_rationale,
        chunk_span=round(span, 4),
        referenced_chunks=chunk_ids,
        semantic_ambiguity=round(ambiguity, 4),
        semantic_ambiguity_rationale=amb_rationale,
        distribution_entropy=round(sim_amb, 4),
        hedge_density=round(hedge_dens, 4),
        evidence_scarcity=round(evidence_scarcity, 4),
        complexity_score=round(complexity, 4),
        routing_decision=routing,
        complexity_level=level,
    )

