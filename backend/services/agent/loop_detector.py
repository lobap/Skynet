from typing import Optional


class LoopDetector:
    """Detects infinite loops in agent tool calls."""
    
    def __init__(self, max_loops: int = 2, history_size: int = 6):
        self.max_loops = max_loops
        self.history_size = history_size
        self.recent_signatures: list[str] = []
        self.consecutive_loops = 0
        self.consecutive_empty_actions = 0
        self.total_failures = 0
        self.max_total_failures = 10
    
    def check_signature(self, signature: str) -> tuple[bool, Optional[str]]:
        """
        Check if a signature indicates a loop.
        Returns (is_loop, error_message).
        """
        if signature in self.recent_signatures[-2:]:
            self.consecutive_loops += 1
            if self.consecutive_loops > self.max_loops:
                return True, "CRITICAL: Infinite Loop Detected. Use 'reply_to_user' tool."
            return True, "Loop detected: same action attempted. Change strategy."
        
        self.consecutive_loops = 0
        self.recent_signatures.append(signature)
        if len(self.recent_signatures) > self.history_size:
            self.recent_signatures.pop(0)
        
        return False, None
    
    def record_empty_action(self) -> tuple[bool, str]:
        """Record an empty action and check if we should stop."""
        self.consecutive_empty_actions += 1
        if self.consecutive_empty_actions > 2:
            return True, "FORCE_STOP: No puedo procesar esta solicitud."
        return False, "No action specified."
    
    def record_valid_action(self) -> None:
        """Reset empty action counter on valid action."""
        self.consecutive_empty_actions = 0
    
    def record_failure(self, observation: str) -> bool:
        """Record a tool failure and check if we should stop."""
        failure_indicators = ["Error", "CRITICAL", "Failed", "does not exist", "BLOCKED"]
        if any(x in str(observation) for x in failure_indicators):
            self.total_failures += 1
        return self.total_failures >= self.max_total_failures
    
    def reset(self) -> None:
        """Reset all counters."""
        self.recent_signatures.clear()
        self.consecutive_loops = 0
        self.consecutive_empty_actions = 0
        self.total_failures = 0
