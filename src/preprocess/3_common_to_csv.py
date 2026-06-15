"""
Common 디렉토리의 공통 문서들을 CSV로 변환
Usage: python -m src.preprocess.3_common_to_csv --category R1
"""
import os
import json
import pandas as pd
import argparse
from pathlib import Path


class CommonDataProcessor:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.output_path = self.project_root / "src" / "data" / "orig" / "db"
        self.output_path.mkdir(parents=True, exist_ok=True)

    def process_common(self, common_base_path: str, lv1_name: str):
        """공통 디렉토리의 JSON 파일들을 단일 CSV로 변환"""
        print(f"--- '{lv1_name}' 공통 폴더 작업 시작 ---")
        
        json_folder_path = Path(common_base_path) / lv1_name / 'jsons'
        
        if not json_folder_path.is_dir():
            print(f"경고: '{json_folder_path}'를 찾을 수 없습니다.")
            return

        all_rows = []
        chunk_idx_counter = 0

        json_files = list(json_folder_path.glob('*.json'))
        print(f"총 {len(json_files)}개의 JSON 파일을 찾았습니다.")

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 일반 처리
                elements = self._extract_elements(data)
                for element in elements:
                    if not isinstance(element, dict):
                        continue

                    text = element.get('text', '')
                    is_rule = 'metadata' not in element
                    filename = element.get('metadata', {}).get('filename') or json_file.name
                    
                    all_rows.append({
                        'chunk_idx': chunk_idx_counter,
                        'text': text,
                        'filename': filename,
                        'is_rule': is_rule,
                        'lv1_name': lv1_name
                    })
                    chunk_idx_counter += 1
                    
            except Exception as e:
                print(f"'{json_file.name}' 처리 중 오류: {e}")

        if all_rows:
            df = pd.DataFrame(all_rows)
            output_file = self.output_path / f"{lv1_name}_common_docs.csv"
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"성공: {len(df)}개 행 → '{output_file}'")

    def _extract_elements(self, data):
        if isinstance(data, dict):
            return list(data.values())
        elif isinstance(data, list):
            return data
        return []


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project_root', type=str, default='/data/projects/chaeyun/rtm/FinRED')
    parser.add_argument('--common_path', type=str, required=True, help='Common 데이터 경로')
    parser.add_argument('--category', type=str, required=True, help='R1, R2, R5 등')
    args = parser.parse_args()

    processor = CommonDataProcessor(args.project_root)
    processor.process_common(args.common_path, args.category)