"""
Evaluator Module - Provides tools for evaluating AI governor proposals
"""

import json
import logging
import re
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("ashoka.evaluator")

# Criteria descriptions for evaluation
CRITERIA_DESCRIPTIONS = {
    "comprehensiveness": "Addresses all aspects of the problem, considers multiple perspectives",
    "practicality": "Proposal is implementable with available resources and constraints",
    "clarity": "Clear communication, well-structured, easy to understand",
    "ethics": "Considers all stakeholders, aligns with community values, fair",
}

# Keywords associated with quality in each criterion
QUALITY_INDICATORS = {
    "comprehensiveness": [
        "multiple options",
        "alternatives",
        "trade-offs",
        "stakeholder",
        "perspective",
        "holistic",
        "comprehensive",
        "factors",
        "considerations",
    ],
    "practicality": [
        "implementation",
        "timeline",
        "milestones",
        "resources",
        "budget",
        "feasible",
        "practical",
        "realistic",
        "steps",
        "measurable",
    ],
    "clarity": [
        "structure",
        "outline",
        "summary",
        "conclusion",
        "introduction",
        "section",
        "breakdown",
        "clear",
        "concise",
        "objective",
    ],
    "ethics": [
        "fair",
        "equitable",
        "inclusive",
        "transparent",
        "accountable",
        "minority",
        "diversity",
        "ethical",
        "sustainable",
        "responsible",
    ],
}


def evaluate_proposal(
    proposal: Dict[str, str], criteria: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Evaluate a governance proposal against predefined criteria.

    Args:
        proposal: Dict containing 'title' and 'content' of the proposal
        criteria: Dict of criteria names and their weights (should sum to 1.0)

    Returns:
        Dict containing scores, feedback, and overall assessment
    """
    criteria = criteria or {
        "comprehensiveness": 0.25,
        "practicality": 0.25,
        "clarity": 0.25,
        "ethics": 0.25,
    }

    # Initialize scores and feedback
    scores = {}
    feedback = []

    # Simple heuristic scoring
    for criterion, weight in criteria.items():
        score, criterion_feedback = _score_criterion(proposal, criterion)
        scores[criterion] = score
        feedback.append(f"{criterion.capitalize()}: {criterion_feedback}")

    # Calculate weighted total
    total_score = sum(scores[c] * criteria[c] for c in criteria)

    # Scale to 0-10
    total_score = total_score * 10

    return {
        "total_score": total_score,
        "scores": scores,
        "feedback": "\n".join(feedback),
        "summary": _generate_summary(total_score, scores),
    }


def _score_criterion(proposal: Dict[str, str], criterion: str) -> Tuple[float, str]:
    """Score a proposal on a specific criterion using heuristics."""
    content = proposal["content"].lower()
    title = proposal["title"].lower()
    full_text = f"{title} {content}"

    # Count keyword occurrences
    indicators = QUALITY_INDICATORS.get(criterion, [])
    matches = sum(1 for keyword in indicators if keyword in full_text)
    keyword_score = min(matches / len(indicators), 1.0)

    # Check for section structure (if applicable for criterion)
    structure_score = 0.0
    if criterion == "clarity":
        has_sections = bool(re.search(r"#+\s+\w+|section|part \d", content))
        has_intro = bool(
            re.search(
                r"introduction|summary|overview|context", content[: len(content) // 3]
            )
        )
        has_conclusion = bool(
            re.search(
                r"conclusion|summary|recommendation", content[2 * len(content) // 3 :]
            )
        )
        structure_score = (has_sections + has_intro + has_conclusion) / 3

    # Check for length/depth (rough heuristic)
    length_score = min(len(content) / 1500, 1.0)

    # Different weighting based on criterion
    if criterion == "comprehensiveness":
        final_score = 0.6 * keyword_score + 0.4 * length_score
        feedback = _generate_feedback(criterion, final_score, keyword_score)
    elif criterion == "practicality":
        final_score = 0.8 * keyword_score + 0.2 * length_score
        feedback = _generate_feedback(criterion, final_score, keyword_score)
    elif criterion == "clarity":
        final_score = 0.4 * keyword_score + 0.6 * structure_score
        feedback = _generate_feedback(criterion, final_score, structure_score)
    elif criterion == "ethics":
        final_score = 0.9 * keyword_score + 0.1 * length_score
        feedback = _generate_feedback(criterion, final_score, keyword_score)
    else:
        final_score = keyword_score
        feedback = "Unknown criterion"

    return final_score, feedback


def _generate_feedback(criterion: str, score: float, sub_score: float) -> str:
    """Generate specific feedback based on the score for a criterion."""
    if score >= 0.8:
        return f"Excellent. {CRITERIA_DESCRIPTIONS[criterion]}"
    elif score >= 0.6:
        return f"Good. {CRITERIA_DESCRIPTIONS[criterion]}"
    elif score >= 0.4:
        return f"Adequate. Could improve on: {CRITERIA_DESCRIPTIONS[criterion]}"
    else:
        return f"Needs improvement. Missing: {CRITERIA_DESCRIPTIONS[criterion]}"


def _generate_summary(total_score: float, scores: Dict[str, float]) -> str:
    """Generate an overall summary of the proposal quality."""
    if total_score >= 8.5:
        return (
            "Outstanding proposal. Well-structured, comprehensive, and implementable."
        )
    elif total_score >= 7.0:
        return (
            "Strong proposal. Some minor improvements possible but generally effective."
        )
    elif total_score >= 5.5:
        return "Solid proposal with good elements. Would benefit from more detail and structure."
    elif total_score >= 4.0:
        return "Basic proposal that requires significant improvement in multiple areas."
    else:
        return "Insufficient proposal. Needs complete reworking to be effective."


def evaluate_proposal_with_llm(
    proposal: Dict[str, str], ollama_client
) -> Dict[str, Any]:
    """
    Use an LLM to evaluate another LLM's proposal.
    This meta-evaluation can be more nuanced than heuristic approaches.

    Args:
        proposal: Dict containing 'title' and 'content' of the proposal
        ollama_client: Instance of OllamaClient to use for evaluation

    Returns:
        Dict containing scores and feedback
    """
    prompt = f"""
    You are an expert in governance systems evaluation. Please evaluate the following proposal
    and score it on a scale of 0-10 for each criterion: comprehensiveness, practicality, clarity, and ethics.
    
    PROPOSAL TITLE: {proposal['title']}
    
    PROPOSAL CONTENT:
    {proposal['content']}
    
    Provide your evaluation in JSON format:
    {{
        "scores": {{
            "comprehensiveness": <score>,
            "practicality": <score>,
            "clarity": <score>,
            "ethics": <score>
        }},
        "total_score": <average_score>,
        "feedback": "<detailed_feedback>",
        "summary": "<overall_assessment>"
    }}
    """

    response = ollama_client.send_prompt(prompt)

    try:
        # Extract JSON from response
        json_start = response.find("{")
        json_end = response.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            return json.loads(json_str)
        else:
            # Fallback to heuristic evaluation
            logger.warning(
                "Could not extract JSON from LLM evaluation response, using heuristic evaluation"
            )
            return evaluate_proposal(proposal)

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error parsing LLM evaluation: {str(e)}")
        # Fallback to heuristic evaluation
        return evaluate_proposal(proposal)
