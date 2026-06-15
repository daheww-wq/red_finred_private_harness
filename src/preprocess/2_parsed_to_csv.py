"""
Parse된 JSON 청크들을 DB용 CSV로 변환
Usage: python -m src.preprocess.2_parsed_to_csv --category R1
"""
import os
import json
import pandas as pd
import argparse
from pathlib import Path


class ParsedDataProcessor:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.output_path = self.project_root / "src" / "data" / "orig" / "db"
        self.output_path.mkdir(parents=True, exist_ok=True)

    def process_category(self, parsed_data_path: str, lv1_name: str, sub_dirs: list):
        """
        지정된 하위 디렉토리 각각에 대해 JSON 파일들을 읽어 개별 CSV 파일을 생성
        """
        base_path = Path(parsed_data_path)
        
        for lv2_name in sub_dirs:
            print(f"--- '{lv2_name}' 폴더 작업 시작 ---")
            
            json_folder_path = base_path / lv2_name / 'jsons'
            
            if not json_folder_path.is_dir():
                print(f"경고: '{json_folder_path}'를 찾을 수 없습니다.")
                continue

            all_rows = []
            chunk_idx_counter = 0

            json_files = list(json_folder_path.glob('*.json'))
            print(f"총 {len(json_files)}개의 JSON 파일을 찾았습니다.")

            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
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
                            'lv2_name': lv2_name,
                            'lv1_name': lv1_name
                        })
                        chunk_idx_counter += 1
                        
                except Exception as e:
                    print(f"'{json_file.name}' 처리 중 오류: {e}")

            if all_rows:
                df = pd.DataFrame(all_rows)
                df = df[['chunk_idx', 'text', 'filename', 'is_rule', 'lv2_name', 'lv1_name']]
                
                output_file = self.output_path / f"{lv2_name}_docs.csv"
                df.to_csv(output_file, index=False, encoding='utf-8-sig')
                print(f"성공: {len(df)}개 행 → '{output_file}'")

    def _extract_elements(self, data):
        if isinstance(data, dict):
            return list(data.values())
        elif isinstance(data, list):
            return data
        return []


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
    parser.add_argument('--parsed_data_path', type=str, required=True, help='Parse된 데이터 경로')
    parser.add_argument('--category', type=str, required=True, help='R1, R2, R3, R4, R5')
    args = parser.parse_args()

    processor = ParsedDataProcessor(args.project_root)
    subcats = get_subcategories(args.category)
    processor.process_category(args.parsed_data_path, args.category, subcats)