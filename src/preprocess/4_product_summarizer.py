"""
R3 금융상품 PDF에서 추출된 텍스트를 vLLM으로 요약
Usage: 
    export CUDA_VISIBLE_DEVICES=6
    python -m src.preprocess.4_product_summarizer --category R3
"""
import os
import json
import gc
import argparse
from pathlib import Path
from tqdm import tqdm
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM


# --- 설정 ---
DEFAULT_MODEL = "LGAI-EXAONE/EXAONE-3.5-32B-Instruct"
MODEL_MAX_LENGTH = 32768
MAX_NEW_TOKENS = 8192


PROMPT_TEMPLATE = """
### ROLE
너는 대한민국 금융상품 설명서를 분석하여, 주어진 형식에 따라 핵심 정보만을 정확하게 추출하고 요약하는 매우 꼼꼼한 전문 금융 애널리스트다. 너의 임무는 사실 확인(Fact-Checking)을 위한 데이터를 만드는 것이므로, 정확성은 무엇보다 중요하다.

### INSTRUCTIONS
> **가장 중요한 원칙**: 너의 유일한 정보 출처는 아래 `# CONTEXT`에 제공된 문서 내용뿐이다. 너의 사전 지식이나 외부 정보를 절대 사용해서는 안 된다.

1.  **정확한 정보 추출**: `# SCHEMA`에 명시된 각 "요약 키워드"에 해당하는 정보를 `# CONTEXT` 본문에서 찾아 그대로 추출한다.
2.  **누락 정보 처리**: 만약 특정 키워드에 해당하는 내용이 본문에 명확하게 없다면, 반드시 **"해당 정보 없음"**이라고 명시한다. 절대로 비워두거나 다른 정보로 대체하지 않는다.
3.  **정보 조작 절대 금지**: 내용을 임의로 해석, 추론, 요약하거나 없는 정보를 만들어내서는 안 된다. 모든 결과는 반드시 원본 문서에 근거해야 한다.
4.  **형식 엄수**: `# ONE-SHOT EXAMPLE`을 참고하여, 최종 결과는 `# OUTPUT` 형식과 완벽하게 일치해야 한다.

### SCHEMA (요약 키워드):
- 1) 상품 기본 정보: 상품명, 상품 유형(펀드/ELS/DLS 등), 운용사/발행사, 판매사, 설정일/발행일, 만기일, 최소 투자금액
- 2) 수익 구조: 기초자산, 수익 조건, 조기상환 조건, 만기 상환 조건, 예상 수익률, 손익 분기점
- 3) 위험 정보: 투자위험등급, 원금손실 가능성, 주요 투자위험 요인, 녹인(Knock-In) 배리어, 최대 손실률
- 4) 비용 및 수수료: 총 보수, 선취/후취 수수료, 환매 수수료, 성과 보수
- 5) 기타 유의사항: 중도환매 제한, 세금 관련 사항, 예금자보호 여부

위 내용들이 있다면, 있는 대로 최대한 자세히 나열하시오. 만약 해당 정보가 없다면, "해당 정보 없음"이라고 명시하시오.

---

### OUTPUT FORMAT: 아래처럼 <summary> 태그된 결과물만 리턴하시오.
<summary>
- **1) 상품 기본 정보**: ...
- **2) 수익 구조**: ...
- **3) 위험 정보**: ...
- **4) 비용 및 수수료**: ...
- **5) 기타 유의사항**: ...
</summary>

---

# YOUR INPUT:
{document_text}

# OUTPUT
"""


class ProductSummarizer:
    def __init__(self, project_root: str, model_path: str = DEFAULT_MODEL):
        self.project_root = Path(project_root)
        self.src_root = self.project_root / "src"
        
        # 경로 설정
        self.input_path = self.src_root / "data" / "orig" / "investinfo"
        self.output_path = self.src_root / "data" / "orig" / "investinfo_sum"
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # 모델 로드
        print(f"모델 로딩 중: {model_path}")
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
            device_map="auto"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        print("✅ 모델 로딩 완료!")
        
        # 프롬프트 토큰 수 계산 (문서 내용 제외)
        self.prompt_base_tokens = len(self.tokenizer.encode(PROMPT_TEMPLATE.format(document_text='')))

    def _truncate_content(self, text: str) -> str:
        """토큰 길이 제한에 맞게 텍스트 자르기"""
        available_tokens = MODEL_MAX_LENGTH - self.prompt_base_tokens - MAX_NEW_TOKENS - 50
        content_tokens = self.tokenizer.encode(text)
        
        if len(content_tokens) > available_tokens:
            half = available_tokens // 2
            truncated_tokens = content_tokens[:half] + content_tokens[-half:]
            return self.tokenizer.decode(truncated_tokens)
        return text

    def summarize_file(self, input_file: Path) -> dict:
        """단일 파일 요약"""
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        text_content = data.get('text', '')
        if not text_content:
            return None
        
        # 토큰 길이 제어
        text_content = self._truncate_content(text_content)
        
        # 프롬프트 생성
        prompt = PROMPT_TEMPLATE.format(document_text=text_content)
        messages = [{"role": "user", "content": prompt}]
        
        input_ids = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt"
        ).to(self.model.device)

        outputs = self.model.generate(
            input_ids,
            eos_token_id=self.tokenizer.eos_token_id,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=0.2,
            top_p=0.95
        )
        
        response = self.tokenizer.decode(outputs[0][input_ids.shape[-1]:], skip_special_tokens=True)
        data['summary'] = response.strip()
        
        # 메모리 해제
        del input_ids, outputs
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        return data

    def run(self):
        """전체 파일 처리"""
        json_files = list(self.input_path.glob('*_extracted.json'))
        print(f"\n총 {len(json_files)}개의 JSON 파일 처리 시작")

        for json_file in tqdm(json_files, desc="요약 처리 중"):
            output_filename = json_file.name.replace("_extracted.json", "_sum.json")
            output_file = self.output_path / output_filename

            if output_file.exists():
                continue

            try:
                result = self.summarize_file(json_file)
                if result:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=4)
                        
            except Exception as e:
                print(f"\n'{json_file.name}' 처리 중 오류: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project_root', type=str, default='/data/projects/chaeyun/rtm/FinRED')
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL, help='모델 경로')
    args = parser.parse_args()

    summarizer = ProductSummarizer(args.project_root, args.model)
    summarizer.run()