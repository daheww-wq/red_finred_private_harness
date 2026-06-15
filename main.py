import argparse
import sys
from pathlib import Path
# src 폴더 내의 모듈 임포트
from src.Step1_build import ScenarioGenerator
from src.Step2_build import RedTeamingPromptGenerator

current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir / "src"))

def get_project_paths():
    """
    main.py 위치를 기준으로 프로젝트 루트 및 출력 경로를 설정합니다.
    """
    from pathlib import Path
    
    # main.py가 있는 곳이 바로 프로젝트 루트 (FinRED/)
    project_root = Path(__file__).resolve().parent
    
    return {
        "project_root": project_root,
        "output_scenarios": project_root / "src" / "outputs" / "scenarios",
        "output_prompts": project_root / "src" / "outputs" / "prompts"
    }

def get_target_categories(category_group):
    """카테고리 그룹(R1, R2...)에 따른 세부 카테고리 리스트 반환"""
    if category_group == 'R1': return [f"R1_{k}" for k in range(1, 7)]
    elif category_group == 'R2': return [f"R2_{k}" for k in range(1, 6)]
    elif category_group == 'R3': return [f"R3_{k}" for k in range(1, 4)]
    elif category_group == 'R4': return [f"R4_{k}" for k in range(1, 6)]
    elif category_group == 'R5': return [f"R5_{k}" for k in range(1, 8)]
    else: return [category_group] # 단일 카테고리 입력 시 (예: R1_1)

def main():
    parser = argparse.ArgumentParser(description="FinRED 통합 파이프라인 실행기")
    
    # 실행 모드 설정
    parser.add_argument('--step', type=str, choices=['1', '2', 'all'], required=True, help='실행할 단계 (1: 시나리오 생성, 2: 프롬프트 생성, all: 순차 실행)')
    
    # 공통 설정
    parser.add_argument('--category', type=str, required=True, help='타겟 카테고리 그룹 (예: R1, R2, R5)')
    parser.add_argument('--openai_api_key', type=str, help='Step 1용 OpenAI API Key')
    parser.add_argument('--gemini_api_key', type=str, help='Step 2용 Gemini API Key')
    
    # Step 2 전용 설정
    parser.add_argument('--lang', type=str, default='ko', choices=['ko', 'en'], help='Step 2 프롬프트 생성 언어 (기본: ko)')
    parser.add_argument('--num_prompts', type=int, default=3, help='Step 2 생성 프롬프트 개수 (K값)')
    parser.add_argument('--model_name', type=str, default='gpt-4.1-mini', help='FinRED step1 에서는 gpt-4.1 로 진행, step2 에서는 gemini-2.5-pro로 진행함.')

    args = parser.parse_args()

    # 경로 및 타겟 설정
    paths = get_project_paths()
    print(paths)
    target_categories = get_target_categories(args.category)
    
    print(f"[*] Project Root: {paths['project_root']}")
    print(f"[*] Targets: {target_categories}")

    # --- Step 1: 시나리오 생성 ---
    if args.step in ['1', 'all']:
        if not args.openai_api_key:
            raise ValueError("Step 1 실행을 위해 --openai_api_key가 필요합니다.")
            
        print(f"\n[Step 1] 시나리오 생성 시작 (Category: {args.category})")
        
        for cat in target_categories:
            # Step 1 클래스는 인스턴스 생성 시 project_root와 output_path를 받습니다.
            step1_runner = ScenarioGenerator(
                project_root=str(paths['project_root']),
                output_path=str(paths['output_scenarios']),
                category_name=cat,
                api_key=args.openai_api_key,
                model_name=args.model_name # gpt 계열
            )
            step1_runner.run(cat)

    # --- Step 2: 시드 프롬프트 생성 ---
    if args.step in ['2', 'all']:
        if not args.gemini_api_key:
            raise ValueError("Step 2 실행을 위해 --gemini_api_key가 필요합니다.")
            
        print(f"\n[Step 2] 시드 프롬프트 생성 시작 (Category: {args.category}, Lang: {args.lang})")
        
        for cat in target_categories:
            # Step 2 클래스 인스턴스 생성
            step2_runner = RedTeamingPromptGenerator(
                project_root=str(paths['project_root']),
                output_path=str(paths['output_prompts']),
                category_name=cat,
                num_prompts=args.num_prompts,
                api_key=args.gemini_api_key,
                lang=args.lang,
                model_name=args.model_name # gemini 계열
            )
            step2_runner.run(cat)

if __name__ == "__main__":
    main()
    # 전체 실행 (R1 카테고리, 한국어)
    # python src/main.py --step all --category R1 --openai_api_key "sk-..." --gemini_api_key "AIza..."
    # Step 2만 실행 (R5 카테고리, 영어, 프롬프트 5개)
    # python src/main.py --step 2 --category R5 --lang en --num_prompts 5 --gemini_api_key "AIza..."


    # python main.py --step all --category R1 --openai_api_key "sk-proj-..." --gemini_api_key "AIza..."
    
    # python main.py --step 2 --category R1_1 --num_prompts 3 --gemini_api_key "AIza..."
