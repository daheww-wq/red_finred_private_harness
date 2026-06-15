"""
PDF 문서를 의미론적 청크로 분할하여 JSON으로 저장
Usage: python -m src.preprocess.1_chunking --category R1

구조:
  parsed_docs/
  ├── Common/
  │   └── R1/
  │       ├── jsons/          # ← 청크 결과 저장
  │       └── *.pdf           # 원본 PDF
  └── R1/
      └── R1_1/
          ├── jsons/
          └── *.pdf
"""
import os
import json
import argparse
from pathlib import Path
from tqdm import tqdm
from unstructured.partition.auto import partition
from unstructured.chunking.title import chunk_by_title
from unstructured.chunking.basic import chunk_elements


# --- 설정 ---
MAX_CHUNK_LENGTH = 1200      # 최종 청크 최대 글자 수
COARSE_MAX_CHARS = 3600      # 1차 청킹 최대
COARSE_COMBINE_UNDER = 200   # 짧은 섹션 병합 기준
COARSE_NEW_AFTER = 2800      # 새 청크 시작 기준


class PDFChunker:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.parsed_docs_path = self.project_root / "src" / "data" / "orig" / "parsed_docs"

    def chunk_pdf(self, pdf_path: Path) -> list:
        """단일 PDF를 청크로 분할"""
        # 1. 의미론적 파싱
        try:
            elements = partition(
                filename=str(pdf_path),
                pdf_infer_table_structure=True,
                strategy="hi_res",
                languages=['kor', 'eng']
            )
        except Exception as e:
            print(f"\n  hi_res 파싱 실패, fast 파싱으로 재시도 [{pdf_path.name}]: {e}")
            elements = partition(
                filename=str(pdf_path),
                strategy="fast",
                languages=['kor', 'eng']
            )

        # 2. 제목 기준 1차 청킹 (Coarse-grained)
        coarse_chunks = chunk_by_title(
            elements,
            max_characters=COARSE_MAX_CHARS,
            combine_text_under_n_chars=COARSE_COMBINE_UNDER,
            new_after_n_chars=COARSE_NEW_AFTER
        )

        # 3. 긴 청크 재분할 (Fine-grained)
        final_chunks = []
        for chunk in coarse_chunks:
            if len(chunk.text) > MAX_CHUNK_LENGTH:
                # 원본 요소 기반 재분할
                if hasattr(chunk.metadata, 'orig_elements'):
                    orig_elements = chunk.metadata.orig_elements
                else:
                    orig_elements = [chunk]

                sub_chunks = chunk_elements(
                    elements=orig_elements,
                    max_characters=MAX_CHUNK_LENGTH,
                    new_after_n_chars=int(MAX_CHUNK_LENGTH * 0.8),
                    overlap=150
                )
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk)

        return final_chunks

    def chunks_to_json(self, chunks: list, pdf_name: str) -> list:
        """청크를 JSON 형식으로 변환"""
        result = []
        for i, chunk in enumerate(chunks):
            result.append({
                "chunk_idx": i,
                "text": chunk.text,
                "metadata": {
                    "filename": pdf_name,
                    "element_type": type(chunk).__name__
                }
            })
        return result

    def process_directory(self, target_dir: Path):
        """디렉토리 내 모든 PDF 처리"""
        pdf_files = list(target_dir.glob('*.pdf'))
        if not pdf_files:
            print(f"  PDF 파일 없음: {target_dir}")
            return

        # jsons 폴더 생성
        jsons_dir = target_dir / 'jsons'
        jsons_dir.mkdir(exist_ok=True)

        for pdf_file in tqdm(pdf_files, desc=f"  {target_dir.name}", leave=False):
            output_file = jsons_dir / f"{pdf_file.stem}.json"
            
            # 이미 처리된 파일 스킵
            if output_file.exists():
                continue

            try:
                chunks = self.chunk_pdf(pdf_file)
                json_data = self.chunks_to_json(chunks, pdf_file.name)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                    
            except Exception as e:
                print(f"\n  오류 [{pdf_file.name}]: {e}")

    def run_category(self, category: str):
        """카테고리별 처리 (R1, R2, ...)"""
        print(f"\n{'='*50}")
        print(f"카테고리 {category} 처리 시작")
        print(f"{'='*50}")

        # 1. Common 폴더 처리
        common_dir = self.parsed_docs_path / "Common" / category
        if common_dir.exists():
            print(f"\n[Common/{category}]")
            self.process_directory(common_dir)
        else:
            print(f"\n[Common/{category}] 폴더 없음, 스킵")

        # 2. 서브카테고리 처리 (R1_1, R1_2, ...)
        category_base = self.parsed_docs_path / category
        if not category_base.exists():
            print(f"[{category}] 폴더 없음")
            return

        subcats = self._get_subcategories(category)
        for subcat in subcats:
            subcat_dir = category_base / subcat
            if subcat_dir.exists():
                print(f"\n[{subcat}]")
                self.process_directory(subcat_dir)

    def _get_subcategories(self, category: str) -> list:
        mapping = {
            'R1': [f'R1_{i}' for i in range(1, 7)],
            'R2': [f'R2_{i}' for i in range(1, 6)],
            'R3': [f'R3_{i}' for i in range(1, 4)],
            'R4': [f'R4_{i}' for i in range(1, 6)],
            'R5': [f'R5_{i}' for i in range(1, 8)],
        }
        return mapping.get(category, [])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project_root', type=str, default='/data/projects/chaeyun/rtm/FinRED')
    parser.add_argument('--category', type=str, required=True, help='R1, R2, R3, R4, R5 또는 all')
    args = parser.parse_args()

    chunker = PDFChunker(args.project_root)
    
    if args.category == 'all':
        for cat in ['R1', 'R2', 'R3', 'R4', 'R5']:
            chunker.run_category(cat)
    else:
        chunker.run_category(args.category)
    
    print("\n청킹 완료!")
