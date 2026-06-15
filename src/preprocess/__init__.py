import importlib

PDFChunker = importlib.import_module("src.preprocess.1_chunking").PDFChunker # 숫자이름 이므로 해당 방식으로 임포트
ParsedDataProcessor = importlib.import_module("src.preprocess.2_parsed_to_csv").ParsedDataProcessor
CommonDataProcessor = importlib.import_module("src.preprocess.3_common_to_csv").CommonDataProcessor
ProductSummarizer = importlib.import_module("src.preprocess.4_product_summarizer").ProductSummarizer
SummaryExtractor = importlib.import_module("src.preprocess.5_summary_extractor").SummaryExtractor
ChunkRetriever = importlib.import_module("src.preprocess.6_chunk_retriever").ChunkRetriever
