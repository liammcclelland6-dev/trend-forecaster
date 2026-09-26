"""Optional local embedding provider for grouping related phrase mentions."""

from collections.abc import Iterable

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def cluster_phrases(
    phrases: Iterable[str],
    similarity_threshold: float = 0.72,
    model_name: str = MODEL_NAME,
) -> dict[str, tuple[str, ...]]:
    """Cluster phrase strings using cosine similarity from a local sentence encoder.

    The first call downloads the model into the standard Hugging Face cache.
    Greedy complete-link grouping requires each new phrase to meet the cutoff
    against every member, preventing weak similarity chains from joining groups.
    """
    if not 0.0 <= similarity_threshold <= 1.0:
        raise ValueError("similarity_threshold must be between 0 and 1")

    unique_phrases = sorted(set(phrases))
    if not unique_phrases:
        return {}
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError(
            "Semantic reports need the optional dependency. Install with "
            'python -m pip install -e ".[semantic]"'
        ) from error

    import numpy as np

    model = SentenceTransformer(model_name, device="cpu")
    embeddings = model.encode(
        [f"Fashion trend phrase: {phrase}" for phrase in unique_phrases],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    similarities = embeddings @ embeddings.T
    groups: list[list[int]] = []
    for index in range(len(unique_phrases)):
        best_group = None
        best_similarity = -1.0
        for group_index, members in enumerate(groups):
            member_similarities = similarities[index, members]
            minimum_similarity = float(member_similarities.min())
            if minimum_similarity >= similarity_threshold and minimum_similarity > best_similarity:
                best_group = group_index
                best_similarity = minimum_similarity
        if best_group is None:
            groups.append([index])
        else:
            groups[best_group].append(index)

    result: dict[str, tuple[str, ...]] = {}
    for indices in groups:
        cluster = tuple(unique_phrases[index] for index in indices)
        for phrase in cluster:
            result[phrase] = cluster
    return result
