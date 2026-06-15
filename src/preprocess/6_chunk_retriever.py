"""
청크 DB와 쿼리를 활용한 유사도 검색
Usage: python -m src.preprocess.6_chunk_retriever --category R1
"""
import os
import re
import json
import pandas as pd
import openai
import chromadb
import argparse
from tqdm import tqdm
from pathlib import Path


class ChunkRetriever:
    def __init__(self, project_root: str, api_key: str):
        self.project_root = Path(project_root)
        self.src_root = self.project_root / "src"
        
        # 경로 설정
        self.db_path = self.src_root / "data" / "orig" / "db"
        self.query_path = self.src_root / "data" / "queries"
        self.output_path = self.src_root / "data" / "contexts" / "retrieved_chunks" / "per_taxonomy_chunks"
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        openai.api_key = api_key
        self.db_client = chromadb.Client()
        
        self.ko_collection = None
        self.en_collection = None
        self.korean_chunks_df = pd.DataFrame()
        self.english_chunks_df = pd.DataFrame()

    def _get_embedding(self, text, model="text-embedding-3-large"):
        if not text or not isinstance(text, str) or not text.strip():
            return None
        try:
            text = text.replace("\n", " ")
            return openai.embeddings.create(input=[text], model=model).data[0].embedding
        except Exception as e:
            print(f"임베딩 오류: {e}")
            return None

    def _detect_language(self, text):
        if not isinstance(text, str) or not text.strip():
            return 'en'
        korean_chars = len(re.findall(r'[\uac00-\ud7a3]', text))
        korean_ratio = korean_chars / len(text) if len(text) > 0 else 0
        return 'ko' if korean_ratio > 0.3 else 'en'

    def setup_category(self, category_prefix: str):
        """카테고리별 데이터 로드 및 Vector DB 구축"""
        print(f"--- {category_prefix} 카테고리 설정 ---")
        
        r_num = category_prefix.split('_')[0]
        
        # CSV 로드
        doc_file = self.db_path / f"{category_prefix}_docs.csv"
        common_file = self.db_path / f"{r_num}_common_docs.csv"
        
        if not doc_file.exists() and not common_file.exists():
            print(f"오류: {doc_file}, {common_file} 없음")
            return False

        corpus_frames = []
        if doc_file.exists():
            doc_df = pd.read_csv(doc_file)
            doc_df['db_id'] = f"{category_prefix}_" + doc_df['chunk_idx'].astype(str)
            corpus_frames.append(doc_df)
        if common_file.exists():
            common_df = pd.read_csv(common_file)
            common_df['db_id'] = f"{r_num}_common_" + common_df['chunk_idx'].astype(str)
            corpus_frames.append(common_df)

        corpus_df = pd.concat(corpus_frames, ignore_index=True).drop_duplicates(subset=['db_id'])
        
        corpus_df.dropna(subset=['db_id', 'text'], inplace=True)
        corpus_df['lang'] = corpus_df['text'].apply(self._detect_language)
        
        self.korean_chunks_df = corpus_df[corpus_df['lang'] == 'ko']
        self.english_chunks_df = corpus_df[corpus_df['lang'] == 'en']
        
        print(f"한국어: {len(self.korean_chunks_df)}개, 영어: {len(self.english_chunks_df)}개")
        
        self._build_vector_db(category_prefix)
        return True

    def _build_vector_db(self, category_prefix):
        """Vector DB 구축"""
        for name in [f"{category_prefix}_ko", f"{category_prefix}_en"]:
            try:
                self.db_client.delete_collection(name=name)
            except:
                pass

        self.ko_collection = self.db_client.create_collection(name=f"{category_prefix}_ko")
        self.en_collection = self.db_client.create_collection(name=f"{category_prefix}_en")

        def embed_and_add(collection, df):
            if df.empty:
                return
            embeddings = [self._get_embedding(t) for t in tqdm(df['text'], desc=f"{collection.name}", leave=False)]
            valid_idx = [i for i, e in enumerate(embeddings) if e is not None]
            if valid_idx:
                collection.add(
                    embeddings=[embeddings[i] for i in valid_idx],
                    documents=df['text'].iloc[valid_idx].tolist(),
                    metadatas=[{'chunk_idx': str(row.chunk_idx)} for row in df.iloc[valid_idx].itertuples()],
                    ids=df['db_id'].iloc[valid_idx].tolist()
                )

        embed_and_add(self.ko_collection, self.korean_chunks_df)
        embed_and_add(self.en_collection, self.english_chunks_df)

    def retrieve_and_save(self, category_prefix: str, top_k: int = 10):
        """검색 수행 및 저장"""
        query_file = self.query_path / f"{category_prefix}_queries.csv"
        if not query_file.exists():
            print(f"쿼리 파일 없음: {query_file}")
            return
            
        query_df = pd.read_csv(query_file)
        results = []

        for idx, row in tqdm(query_df.iterrows(), total=len(query_df), desc=f"{category_prefix}"):
            ko_query = row.get('한국어 쿼리')
            en_query = row.get('영어 쿼리')
            
            combined = []
            
            # 한국어 검색
            if pd.notna(ko_query) and self.ko_collection.count() > 0:
                emb = self._get_embedding(ko_query)
                if emb:
                    res = self.ko_collection.query(query_embeddings=[emb], n_results=min(top_k, self.ko_collection.count()))
                    for i in range(len(res['ids'][0])):
                        combined.append({
                            'chunk_idx': res['metadatas'][0][i]['chunk_idx'],
                            'text': res['documents'][0][i],
                            'distance': res['distances'][0][i],
                            'lang': 'korean'
                        })

            # 영어 검색
            if pd.notna(en_query) and self.en_collection.count() > 0:
                emb = self._get_embedding(en_query)
                if emb:
                    res = self.en_collection.query(query_embeddings=[emb], n_results=min(top_k, self.en_collection.count()))
                    for i in range(len(res['ids'][0])):
                        combined.append({
                            'chunk_idx': res['metadatas'][0][i]['chunk_idx'],
                            'text': res['documents'][0][i],
                            'distance': res['distances'][0][i],
                            'lang': 'english'
                        })

            combined.sort(key=lambda x: x['distance'])
            
            results.append({
                "query_idx": idx,
                "korean_query": ko_query if pd.notna(ko_query) else "",
                "english_query": en_query if pd.notna(en_query) else "",
                "extracted_texts": [c['text'] for c in combined[:top_k]]
            })

        # 저장
        output_file = self.output_path / f"{category_prefix}_chunks.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"저장 완료: {output_file}")


def get_subcategories(category: str) -> list:
    mapping = {
        'R1': [f'R1_{i}' for i in range(1, 7)],
        'R2': [f'R2_{i}' for i in range(1, 6)],
        'R3': [f'R3_{i}' for i in range(1, 4)],
        'R4': [f'R4_{i}' for i in range(1, 6)],
        'R5': [f'R5_{i}' for i in range(1, 8)],
    }
    return mapping.get(category, [category])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project_root', type=str, default='/data/projects/chaeyun/rtm/FinRED')
    parser.add_argument('--category', type=str, required=True)
    parser.add_argument('--api_key', type=str, required=True, help='OpenAI API Key')
    parser.add_argument('--top_k', type=int, default=8)
    args = parser.parse_args()

    subcats = get_subcategories(args.category)
    
    for cat in subcats:
        retriever = ChunkRetriever(args.project_root, args.api_key)
        if retriever.setup_category(cat):
            retriever.retrieve_and_save(cat, args.top_k)
