from uuid import uuid4

import pytest

from app.ingestion.chunking import create_chunks
from app.ingestion.models import SourceSegment


def test_chunking_preserves_source_metadata_and_overlap() -> None:
    text = " ".join(f"word-{index:03d}" for index in range(200))
    source = SourceSegment(text=text, location="page 3", metadata={"page": "3"})

    chunks = create_chunks(
        uuid4(),
        [source],
        target_characters=300,
        overlap_characters=50,
    )

    assert len(chunks) > 1
    assert all(chunk.location == "page 3" for chunk in chunks)
    assert all(chunk.metadata == {"page": "3"} for chunk in chunks)
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
    assert all(len(chunk.text) <= 300 for chunk in chunks)


@pytest.mark.parametrize(
    ("target", "overlap"),
    [(199, 10), (300, -1), (300, 300)],
)
def test_chunking_rejects_unsafe_configuration(target: int, overlap: int) -> None:
    source = SourceSegment(text="valid text", location="row 1")

    with pytest.raises(ValueError):
        create_chunks(
            uuid4(),
            [source],
            target_characters=target,
            overlap_characters=overlap,
        )

