import os
import json
import pandas as pd
import random
import glob
import instructor
from pydantic import BaseModel, create_model
from tqdm import tqdm
from pathlib import Path
from openai import OpenAI
from typing import Any, Dict, List
import argparse
import yaml

# 프롬프트 매핑
with open("./prompts/step1.yaml", "r", encoding="utf-8") as f:
    PROMPT_FACTORY = yaml.safe_load(f)
    
PROMPT_MAP = {
    "R1": (PROMPT_FACTORY["R1"]["system_prompt"], PROMPT_FACTORY["R1"]["user_prompt"]),
    "R2": (PROMPT_FACTORY["R2"]["system_prompt"], PROMPT_FACTORY["R2"]["user_prompt"]),
    "R3": (PROMPT_FACTORY["R3"]["system_prompt"], PROMPT_FACTORY["R3"]["user_prompt"]),
    "R4": (PROMPT_FACTORY["R4"]["system_prompt"], PROMPT_FACTORY["R4"]["user_prompt"]),
    "R5": (PROMPT_FACTORY["R5"]["system_prompt"], PROMPT_FACTORY["R5"]["user_prompt"]),
}

class ScenarioGenerator:
    def __init__(self, project_root: str, output_path: str, category_name: str, api_key: str = None, model_name: str = "gpt-4.1-2025-04-14"):
        self.project_root = Path(project_root)
        self.output_path = Path(output_path)
        self.category_name = category_name
        self.category_group = category_name.split('_')[0] # R1, R2, ...
        self.api_key = api_key
        self.model_name = model_name
        self.client = self._init_client(api_key)

        # --- 경로 정의 (요청사항 반영) ---
        self.src_root = self.project_root / "src"
        
        # 1. 스키마 경로
        self.schema_path = self.src_root / "data/schemas/ko"
        
        # 2. 쿼리 경로
        self.query_path = self.src_root / "data/queries"

        # 3. 컨텍스트 및 상품 정보 경로 (R3 분기 처리)
        if self.category_group == 'R3':
            self.context_path = self.src_root / "data/contexts/retrieved_chunks/common_R3"
            self.product_path = self.src_root / "data/contexts/R3_products"
        else:
            self.context_path = self.src_root / "data/contexts/retrieved_chunks/per_taxonomy_chunks"
            self.product_path = None

    def _init_client(self, api_key):
        if not api_key:
            raise ValueError("API 키가 제공되지 않았습니다.")
        return instructor.from_openai(OpenAI(api_key=api_key))

    def _create_dynamic_model(self, model_name: str, schema_dict: Dict[str, Any]) -> BaseModel:
        """JSON 스키마 딕셔너리를 기반으로 동적 Pydantic 모델 생성"""
        fields = {key: (Any, ...) for key in schema_dict.keys()}
        return create_model(model_name, **fields)

    def _load_schema(self, category_prefix: str) -> tuple[dict, str, list]:
        """스키마 파일 로드"""
        schema_file = self.schema_path / f"{category_prefix}.json"
        if not schema_file.exists():
            print(f"[오류] 스키마 파일 {schema_file}을 찾을 수 없습니다.")
            return {}, "", ["", ""]
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        few_shot_good = data.get('few_shot_good_examples', '').rstrip()
        few_shot_schema = data.get('few_shot_schema_examples', '').rstrip()
        
        return data['Schema'], data['Description'], [few_shot_good, few_shot_schema]

    def _load_queries(self, category_prefix: str) -> list:
        """R3용 쿼리 리스트 로드"""
        query_file = self.query_path / f"{category_prefix}_queries.csv"
        if not query_file.exists():
            print(f"[오류] 쿼리 파일 {query_file}을 찾을 수 없습니다.")
            return []
        query_df = pd.read_csv(query_file)
        return query_df['한국어 쿼리'].dropna().tolist()

    def _load_contexts(self, category_prefix: str):
        """컨텍스트 파일 로드 (R3는 dict, 나머지는 list 반환)"""
        if self.category_group == 'R3':
            # R3: 공통 컨텍스트 파일 (예: R3_contents.json 또는 category_prefix_contents.json)
            context_file = self.context_path / f"{category_prefix}_contents.json"
            if not context_file.exists():
                # fallback: R3_contents.json 시도
                context_file = self.context_path / "R3_contents.json"
        else:
            # Others: 쿼리별 청크 파일
            context_file = self.context_path / f"{category_prefix}_chunks.json"

        if not context_file.exists():
            print(f"[오류] 컨텍스트 파일 {context_file}을 찾을 수 없습니다.")
            return [] if self.category_group != 'R3' else {}

        with open(context_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_financial_products(self) -> list:
        """R3용 금융 상품 요약 정보 로드"""
        if not self.product_path or not self.product_path.exists():
            print(f"[오류] 금융 상품 경로 {self.product_path}이 존재하지 않습니다.")
            return []

        product_files = sorted(glob.glob(str(self.product_path / '*_sum.json')))
        summaries = []  
        for p_file in product_files:
            with open(p_file, 'r', encoding='utf-8') as f:
                product_data = json.load(f)
            summaries.append(product_data.get('summary', '요약 정보 없음'))
        return summaries

    def generate(self, system_prompt, usr_prompt, formatting_fn):
        response = self.client.messages.create(
            model=self.model_name, # 모델명은 사용 가능한 최신 모델로 유지
            max_tokens=16384,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": usr_prompt}
            ],
            response_model=formatting_fn
        )
        return response.model_dump()

    def run(self, category_prefix: str):
        print(f"--- {category_prefix} 시나리오 생성 시작 ---")
        
        # 1. 프롬프트 및 스키마 준비
        sys_tmpl, usr_tmpl = PROMPT_MAP.get(self.category_group, (None, None))
        if not sys_tmpl:
            print(f"[오류] 지원하지 않는 카테고리 그룹: {self.category_group}")
            return

        schema_template, schema_description, few_shot_examples = self._load_schema(category_prefix)
        if not schema_template: return

        # 동적 모델 생성
        DynamicScenarioFormat = self._create_dynamic_model(f"{category_prefix}Model", schema_template)
        
        # 시스템 프롬프트 완성
        system_prompt = sys_tmpl.format(
            few_shot_good_examples=few_shot_examples[0],
            few_shot_schema_examples=few_shot_examples[1]
        )

        # 출력 디렉토리 생성
        category_output_path = self.output_path / category_prefix
        category_output_path.mkdir(parents=True, exist_ok=True)

        # 2. 데이터 로드 및 생성 루프 (R3 vs Others 분기)
        if self.category_group == 'R3':
            self._run_r3_logic(category_prefix, system_prompt, usr_tmpl, schema_description, schema_template, DynamicScenarioFormat, category_output_path)
        else:
            self._run_general_logic(category_prefix, system_prompt, usr_tmpl, schema_description, schema_template, DynamicScenarioFormat, category_output_path)

        print(f"--- {category_prefix} 시나리오 생성 완료 ---\n")

    def _run_r3_logic(self, category_prefix, system_prompt, usr_tmpl, schema_desc, schema_json, model, output_path):
        """R3 전용 로직: 상품 정보 + 쿼리 매핑 + 공통 컨텍스트"""
        queries = self._load_queries(category_prefix)
        contexts = self._load_contexts(category_prefix) # dict 반환 예상
        product_summaries = self._load_financial_products()
        
        if not product_summaries:
            print("[경고] 처리할 금융 상품 정보가 없습니다.")
            return

        required_contexts = [c['text'] for c in contexts.get('required', [])] if isinstance(contexts, dict) else []

        for i, prod_sum in enumerate(tqdm(product_summaries, desc=f"[{category_prefix}] 상품별 생성")):
            # 쿼리 매핑 (Round-robin)
            current_query = queries[i % len(queries)] if queries else "금융 상품 불완전 판매 시나리오 생성"
            
            # 컨텍스트 샘플링
            combined_context = list(required_contexts)
            if isinstance(contexts, dict):
                if contexts.get('first_chunk'):
                    combined_context.append(random.choice(contexts['first_chunk'])['text'])
                if contexts.get('second_chunk'):
                    combined_context.append(random.choice(contexts['second_chunk'])['text'])
            
            context_text = "\n\n---\n".join(combined_context)

            # 프롬프트 구성
            final_prompt = usr_tmpl.format(
                product_summary=prod_sum,
                mapped_query=current_query,
                sampled_context=context_text,
                schema_description=schema_desc,
                schema_structure_json=json.dumps(schema_json, indent=4, ensure_ascii=False)
            )

            self._generate_and_save(i, category_prefix, system_prompt, final_prompt, model, output_path)

    def _run_general_logic(self, category_prefix, system_prompt, usr_tmpl, schema_desc, schema_json, model, output_path):
        """R1, R2, R4, R5 로직: 쿼리별 청크 파일 기반"""
        query_context_data = self._load_contexts(category_prefix) # list 반환 예상
        
        if not query_context_data:
            print(f"[경고] {category_prefix}에 대한 컨텍스트 데이터가 없습니다.")
            return

        for i, item in enumerate(tqdm(query_context_data, desc=f"[{category_prefix}] 쿼리별 생성")):
            all_chunks = item.get('extracted_texts', [])
            if not all_chunks: continue

            # 컨텍스트 샘플링 (기존 로직 유지)
            if len(all_chunks) < 2:
                sampled_chunks = all_chunks
            else:
                initial = all_chunks[:4]
                later = all_chunks[4:]
                mandatory = random.sample(initial, min(2, len(initial)))
                remaining = [c for c in initial if c not in mandatory] + later
                random_sel = random.sample(remaining, min(random.randint(1, 2), len(remaining))) if remaining else []
                sampled_chunks = mandatory + random_sel
            
            context_text = "\n\n---\n\n".join(sampled_chunks)

            # 프롬프트 구성
            final_prompt = usr_tmpl.format(
                korean_query=item.get('korean_query', ''),
                english_query=item.get('english_query', ''),
                sampled_context=context_text,
                schema_description=schema_desc,
                schema_structure_json=json.dumps(schema_json, indent=4, ensure_ascii=False)
            )

            self._generate_and_save(i, category_prefix, system_prompt, final_prompt, model, output_path)

    def _generate_and_save(self, index, prefix, sys_prompt, usr_prompt, model, output_path):
        output_file = output_path / f"{index:04d}_{prefix}_scenario.json"
        try:
            result = self.generate(sys_prompt, usr_prompt, model)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"\n[오류] {index}번 항목 생성 실패: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project_root', type=str, default="/home/chaeyun/data/projects/chaeyun/rtm/FinRED", help='프로젝트 루트 경로')
    parser.add_argument('--output_path', type=str, default="/home/chaeyun/data/projects/chaeyun/rtm/FinRED/outputs/scenarios", help='결과 저장 경로')
    parser.add_argument('--category', type=str, required=True, help='타겟 카테고리 (예: R1, R2_1)')
    parser.add_argument('--api_key', type=str, required=True, help='OpenAI API Key')
    
    args = parser.parse_args()

    
    # 카테고리 확장 (R1 입력 시 R1_1 ~ R1_6 자동 확장)
    if args.category in ['R1', 'R2', 'R3', 'R4', 'R5']:
        if args.category == 'R1': targets = [f"R1_{k}" for k in range(1, 7)]
        elif args.category == 'R2': targets = [f"R2_{k}" for k in range(1, 6)]
        elif args.category == 'R3': targets = [f"R3_{k}" for k in range(1, 4)]
        elif args.category == 'R4': targets = [f"R4_{k}" for k in range(1, 6)]
        elif args.category == 'R5': targets = [f"R5_{k}" for k in range(1, 8)]
    else:
        targets = [args.category]

    generator = ScenarioGenerator(
        project_root=args.project_root,
        output_path=args.output_path,
        category_name=args.category, # 대표 카테고리 이름 전달
        api_key=args.api_key
    )

    for target in targets:
        generator.run(target)
        
    
    # How to run the .py file
    # python src/Step1_build.py --category R1 --api_key YOUR_API_KEY