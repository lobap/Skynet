import asyncio
import os
import aiofiles

async def run_test_and_apply(test_path: str, target_path: str, source_code: str) -> str:
    """
    Safely applies code changes by first running a test script.
    1. Writes source_code to a temp file.
    2. Runs the test script at test_path.
    3. If test passes (exit code 0), overwrites target_path with source_code.
    """
    try:
        # 1. Write to temp file (or just keep in memory if we overwrite target directly after test? 
        # No, we need to test the NEW code. So we should probably write to target_path + ".tmp" 
        # and have the test import that? Or overwrite target_path, test, and revert if fail?
        # Reverting is safer.
        
        # Better approach for TDD:
        # The user provides the code they WANT to be in target_path.
        # We write it to target_path.tmp
        # We assume the test_path imports target_path. 
        # This is tricky because imports in Python are cached and based on filenames.
        
        # Simplified Robust TDD:
        # 1. Backup target_path if exists.
        # 2. Write source_code to target_path.
        # 3. Run test.
        # 4. If fail, restore backup.
        
        target_path = os.path.expanduser(target_path)
        test_path = os.path.expanduser(test_path)
        
        backup_path = target_path + ".bak"
        has_backup = False
        
        if os.path.exists(target_path):
            os.rename(target_path, backup_path)
            has_backup = True
            
        # Write new code
        async with aiofiles.open(target_path, 'w') as f:
            await f.write(source_code)
            
        # Run test
        # We use a subprocess to ensure clean import state
        proc = await asyncio.create_subprocess_shell(
            f"python {test_path}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            # Success
            if has_backup:
                os.remove(backup_path)
            return f"Success: Tests passed. Code applied to {target_path}.\nOutput: {stdout.decode()}"
        else:
            # Failure - Revert
            if has_backup:
                os.replace(backup_path, target_path)
            else:
                os.remove(target_path) # It was new, so delete it
                
            return f"Failure: Tests failed (Exit code {proc.returncode}). Changes reverted.\nStderr: {stderr.decode()}\nStdout: {stdout.decode()}"

    except Exception as e:
        # Emergency revert if python error
        if 'has_backup' in locals() and has_backup and os.path.exists(backup_path):
             os.replace(backup_path, target_path)
        return f"System Error in deployer: {str(e)}"
