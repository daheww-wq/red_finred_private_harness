import os
import json
import pandas as pd
import glob
import instructor
import google.generativeai as genai
from pydantic import BaseModel, create_model
from tqdm import tqdm
from pathlib import Path
from typing import List, Any
import argparse
import yaml



# --- 프롬프트 임포트 ---
with open("./prompts/step2.yaml", "r", encoding="utf-8") as f:
    PROMPT_FACTORY_KO = yaml.safe_load(f)
with open("./prompts/step2_eng.yaml", "r", encoding="utf-8") as f:
    PROMPT_FACTORY_ENG = yaml.safe_load(f)


USER_PROMPT_KO = PROMPT_FACTORY_KO['common']['user_prompt']
USER_PROMPT_EN = PROMPT_FACTORY_ENG['common']['user_prompt']

class RedTeamingPromptGenerator:
    def __init__(self, project_root: str, output_path: str, category_name: str, num_prompts: int, api_key: str, lang: str = 'ko', model_name : str="models/gemini-2.5-pro"):
        self.project_root = Path(project_root)
        self.src_root = self.project_root / "src"
        self.output_path = Path(output_path)
        self.category_name = category_name
        self.k_value = num_prompts
        self.lang = lang
        
        # Gemini 클라이언트 초기화
        genai.configure(api_key=api_key)
        self.client = instructor.from_gemini(
            client=genai.GenerativeModel(model_name=model_name)
        )

        # --- 경로 설정 ---
        # 1. 스키마 경로 (언어별 분기)
        if self.lang == 'ko':
            self.schema_path = self.src_root / "data/schemas/ko"
        else:
            self.schema_path = self.src_root / "data/schemas/en"

        # 2. 시나리오 경로 (Step 1의 결과물 위치)
        self.scenario_path = self.src_root / "outputs/scenarios"

    def _create_dynamic_prompt_model(self, num_prompts: int) -> BaseModel:
        """생성할 프롬프트 개수(K)에 맞춰 Pydantic 모델을 동적으로 생성"""
        fields = {}
        for i in range(1, num_prompts + 1):
            fields[f"prompt_{i}"] = (str, ...)
            fields[f"prompt_{i}_optionalelements"] = (List[str], ...)
        
        return create_model("OutputPromptFormat", **fields)

    def _get_system_prompt(self, category_prefix: str):
        """언어 및 카테고리에 맞는 시스템 프롬프트 반환"""
        group = category_prefix.split('_')[0]
        
        if self.lang == 'ko':
            prompts = {
                'R1': PROMPT_FACTORY_KO['R1']['system_prompt'], 'R2': PROMPT_FACTORY_KO['R2']['system_prompt'], 'R3': PROMPT_FACTORY_KO['R3']['system_prompt'], 
                'R4': PROMPT_FACTORY_KO['R4']['system_prompt'], 'R5': PROMPT_FACTORY_KO['R5']['system_prompt']
            }
        else:
            prompts = {
                'R1': PROMPT_FACTORY_ENG['R1']['system_prompt'], 'R2': PROMPT_FACTORY_ENG['R2']['system_prompt'], 'R3': PROMPT_FACTORY_ENG['R3']['system_prompt'], 
                'R4': PROMPT_FACTORY_ENG['R4']['system_prompt'], 'R5': PROMPT_FACTORY_ENG['R5']['system_prompt']
            }
        
        return prompts.get(group, prompts.get('R1'))

    def _load_schema(self, category_prefix: str) -> tuple[dict, str, list]:
        """스키마 로드 및 Few-shot 예시 추출"""
        schema_file = self.schema_path / f"{category_prefix}.json"
        
        if not schema_file.exists():
            print(f"[오류] 스키마 파일 {schema_file}을 찾을 수 없습니다.")
            return {}, "Description not found", ""
            
        with open(schema_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 언어에 따라 few-shot 키 선택
        seed_key = 'few_shot_seeds' if self.lang == 'ko' else 'few_shot_seeds_eng'
        few_shot_seeds = data.get(seed_key, "").strip()
        
        return data['Schema'], data['Description'], few_shot_seeds

    def _load_scenario_list(self, category_prefix: str) -> list:
        """Step 1에서 생성된 시나리오 파일 목록 로드"""
        target_dir = self.scenario_path / category_prefix
        if not target_dir.exists():
            print(f"[오류] 시나리오 디렉토리 {target_dir}가 존재하지 않습니다.")
            return []
            
        scenario_files = sorted(list(target_dir.glob(f"*_{category_prefix}_scenario.json")))
        return scenario_files

    def run(self, category_prefix: str):
        print(f"--- {category_prefix} 프롬프트 생성 시작 (언어: {self.lang}, K={self.k_value}) ---")
        
        schema, schema_desc, few_shot_examples = self._load_schema(category_prefix)
        scenario_files = self._load_scenario_list(category_prefix)
        
        if not scenario_files:
            print(f"[경고] {category_prefix}에 대한 시나리오 파일이 없습니다.")
            return

        # 출력 디렉토리 준비
        category_output_path = self.output_path / category_prefix
        category_output_path.mkdir(parents=True, exist_ok=True)
        
        system_prompt = self._get_system_prompt(category_prefix)
        user_prompt_template = USER_PROMPT_KO if self.lang == 'ko' else USER_PROMPT_EN
        
        # 동적 모델 생성 (K값에 따라 필드 자동 생성)
        DynamicOutputModel = self._create_dynamic_prompt_model(self.k_value)
        
        # JSON 스키마 추출
        try:
            # Pydantic V2
            schema_dict = DynamicOutputModel.model_json_schema()
        except AttributeError:
            # Pydantic V1
            schema_dict = DynamicOutputModel.schema()
            
        schema_json_str = json.dumps(schema_dict, indent=4, ensure_ascii=False)
        
        all_results = []
        error_results = []

        for i, scenario_file in enumerate(tqdm(scenario_files, desc=f"[{category_prefix}]")):
            with open(scenario_file, 'r', encoding='utf-8') as f:
                scenario_json = json.load(f)
            
            usr_prompt = user_prompt_template.format(
                schema_description=schema_desc,
                scenario_json=json.dumps(scenario_json, ensure_ascii=False, indent=4),
                few_shot_examples=few_shot_examples,
                k_value=self.k_value,
                schema_structure_json=schema_json_str
            )
            
            try:
                response = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": usr_prompt},
                    ],
                    response_model=DynamicOutputModel
                )
                output_data = response.model_dump()
                
                # 1. 개별 JSON 저장
                out_name = f"{scenario_file.stem.replace('_scenario', '')}_prompts.json"
                with open(category_output_path / out_name, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=4)
                
                # 2. CSV용 데이터 수집
                row = {
                    'index': i,
                    'category_prefix': category_prefix,
                    'scenario_file': str(scenario_file)
                }
                row.update(output_data)
                all_results.append(row)
                
            except Exception as e:
                error_message = f"{type(e).__name__}: {e}"
                print(f"[오류] {scenario_file.name} 처리 중 에러: {error_message}")
                error_results.append({
                    "scenario_file": str(scenario_file),
                    "error": error_message
                })


        # CSV 통합 저장
        if all_results:
            df = pd.DataFrame(all_results)
            # 컬럼 순서 정렬
            cols = ['index', 'category_prefix', 'scenario_file'] + \
                [c for c in df.columns if c not in ['index', 'category_prefix', 'scenario_file']]
            df = df[cols]
            
            csv_path = self.output_path / f"{category_prefix}_prompts_all.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"[완료] CSV 저장됨: {csv_path}")
        elif error_results:
            error_path = self.output_path / f"{category_prefix}_step2_errors.json"
            with open(error_path, 'w', encoding='utf-8') as f:
                json.dump(error_results, f, ensure_ascii=False, indent=4)
            print(f"[오류] 생성된 프롬프트가 없습니다. 에러 로그 저장됨: {error_path}")
        

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="FinRED Step 2: Seed Prompt Generator")
    
    parser.add_argument('--project_root', type=str, default="/home/chaeyun/data/projects/chaeyun/rtm/FinRED", help='프로젝트 루트 경로')
    parser.add_argument('--output_path', type=str, default="/home/chaeyun/data/projects/chaeyun/rtm/FinRED/outputs/prompts", help='결과 저장 경로')
    parser.add_argument('--category', type=str, required=True, help='타겟 카테고리 (예: R1, R5)')
    parser.add_argument('--lang', type=str, default='ko', choices=['ko', 'en'], help='생성 언어 (ko/en)')
    parser.add_argument('--num_prompts', type=int, default=3, help='생성할 프롬프트 개수 (K)')
    parser.add_argument('--api_key', type=str, required=True, help='Gemini API Key')
    
    args = parser.parse_args()

    # 카테고리 확장 로직
    if args.category in ['R1', 'R2', 'R3', 'R4', 'R5']:
        if args.category == 'R1': targets = [f"R1_{k}" for k in range(1, 7)]
        elif args.category == 'R2': targets = [f"R2_{k}" for k in range(1, 6)]
        elif args.category == 'R3': targets = [f"R3_{k}" for k in range(1, 4)]
        elif args.category == 'R4': targets = [f"R4_{k}" for k in range(1, 6)]
        elif args.category == 'R5': targets = [f"R5_{k}" for k in range(1, 8)]
    else:
        targets = [args.category]

    generator = RedTeamingPromptGenerator(
        project_root=args.project_root,
        output_path=args.output_path,
        category_name=args.category,
        num_prompts=args.num_prompts,
        api_key=args.api_key,
        lang=args.lang
    )

    for target in targets:
        generator.run(target)   
