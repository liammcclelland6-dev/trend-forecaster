"""Optional local embedding provider for grouping related phrase mentions."""

from collections.abc import Iterable

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def cluster_phrases(
    phrases: Iterable[str],
    similarity_threshold: float = 0.58,
    model_name: str = MODEL_NAME,
) -> dict[str, tuple[str, ...]]:
    """Cluster phrase strings using cosine similarity from a local sentence encoder.

    The first call downloads the model into the standard Hugging Face cache. The
    implementation uses connected components, so a chain of similar pairs can
    place phrases together even when the two endpoints are less similar.
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

    parents = list(range(len(unique_phrases)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    block_size = 128
    for start in range(0, len(unique_phrases), block_size):
        similarities = embeddings[start:start + block_size] @ embeddings.T
        for offset, row in enumerate(similarities):
            left = start + offset
            for right in np.flatnonzero(row >= similarity_threshold):
                if right > left:
                    union(left, int(right))

    groups: dict[int, list[str]] = {}
    for index, phrase in enumerate(unique_phrases):
        groups.setdefault(find(index), []).append(phrase)

    result: dict[str, tuple[str, ...]] = {}
    for members in groups.values():
        cluster = tuple(sorted(members))
        for phrase in members:
            result[phrase] = cluster
    return result
