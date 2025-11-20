import os
from ..ai_utils import consult_ai
from .dev_tools import run_safe_edit, inspect_code

MODEL_REASONING = os.getenv("MODEL_REASONING", "deepseek-r1:1.5b")
MODEL_CODING = os.getenv("MODEL_CODING", "qwen2.5-coder:1.5b")

async def attempt_fix(file_path: str, error_trace: str) -> str:
    """
    Autonomous Debugger.
    1. Analyzes the error with DeepSeek (Reasoning).
    2. Generates a fix with Qwen (Coding).
    3. Applies and verifies the fix safely.
    """
    try:
        # 1. Read Code
        code_info = inspect_code(file_path)
        if "Error" in code_info and not code_info.startswith("FILE:"):
            return f"Could not read file: {code_info}"

        # 2. Analyze with Reasoning Model
        analysis_prompt = """You are an Expert Debugger.
        Analyze the provided code and error trace.
        Identify the ROOT CAUSE of the failure.
        Propose a logical, step-by-step solution.
        """
        analysis_input = f"Code:\n{code_info}\n\nError Trace:\n{error_trace}"
        analysis = await consult_ai(MODEL_REASONING, analysis_prompt, analysis_input)

        # 3. Generate Fix with Coding Model
        coding_prompt = """You are a Senior Software Engineer.
        Based on the analysis, rewrite the FULL file code to fix the error.
        - Return ONLY the code block. No markdown.
        - Ensure all imports are present.
        """
        coding_input = f"Original Code:\n{code_info}\n\nAnalysis:\n{analysis}\n\nGenerate fixed code."
        fixed_code = await consult_ai(MODEL_CODING, coding_prompt, coding_input)
        fixed_code = fixed_code.replace("```python", "").replace("```", "").strip()

        # 4. Generate Verification Test
        test_gen_prompt = """Generate a standalone python test script (using assert or unittest) to verify the fix for the code above.
        It should import the module (assume it's in the same directory or python path) and test the failing case.
        Return ONLY the code block. No markdown.
        """
        test_code = await consult_ai(MODEL_CODING, test_gen_prompt, f"Fixed Code:\n{fixed_code}")
        test_code = test_code.replace("```python", "").replace("```", "").strip()

        # 5. Apply Fix
        result = run_safe_edit(file_path, fixed_code, test_code)
        return f"Debug Attempt Result:\nAnalysis: {analysis[:200]}...\n{result}"
        
    except Exception as e:
        return f"Error in auto-debugger: {str(e)}"

async def analyze_error_and_fix(file_path: str, error_log: str) -> str:
    # Alias for backward compatibility
    return await attempt_fix(file_path, error_log)
