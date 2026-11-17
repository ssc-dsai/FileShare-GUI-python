# How does classification work

- Load `fcp_CSV-UTF.csv`: **Yes**
- Prefer summary descriptions for embedding: **Yes**
- Cache hierarchy embeddings on disk: **Yes (optional)**
- Chunk long documents (~100 tokens, overlap): **Yes**
- Hierarchical match (Function → Sub-Function → Records): **Yes**
- 500-char match excerpts from the document: **Yes**
- Fully offline local MiniLM: **Yes**