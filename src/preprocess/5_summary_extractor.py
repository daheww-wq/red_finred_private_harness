"""
vLLM 요약 결과에서 summary만 추출하여 R3_products로 이동
Usage: python -m src.preprocess.5_summary_extractor
"""
import os
import json
import argparse
from pathlib import Path
from tqdm import tqdm


class SummaryExtractor:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.src_root = self.project_root / "src"
        
        # 경로 설정
        self.input_path = self.src_root / "data" / "orig" / "investinfo_sum"
        self.output_path = self.src_root / "data" / "contexts" / "R3_products"
        self.output_path.mkdir(parents=True, exist_ok=True)

    def extract_summary(self, input_file: Path) -> dict:
        """원본에서 text 제거하고 summary만 유지"""
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # text 키 제거 (용량 절약)
        if 'text' in data:
            del data['text']
        
        return data

    def run(self):
        """전체 파일 처리"""
        if not self.input_path.exists():
            print(f"오류: 입력 경로가 없습니다 - {self.input_path}")
            return
            
        json_files = list(self.input_path.glob('*_sum.json'))
        print(f"총 {len(json_files)}개의 요약 파일 처리")

        for json_file in tqdm(json_files, desc="Summary 추출 중"):
            output_file = self.output_path / json_file.name

            try:
                result = self.extract_summary(json_file)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=4)
                    
            except Exception as e:
                print(f"'{json_file.name}' 처리 중 오류: {e}")

        print(f"\n✅ 완료: {self.output_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project_root', type=str, default='/data/projects/chaeyun/rtm/FinRED')
    args = parser.parse_args()

    extractor = SummaryExtractor(args.project_root)
    extractor.run()