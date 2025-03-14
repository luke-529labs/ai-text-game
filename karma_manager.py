from langchain_openai import ChatOpenAI
from typing import Dict, Tuple

class KarmaManager:
    """Handles evaluation and updates of player karma based on their choices and actions."""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def evaluate_karma_change(self, action: str, context: Dict[str, str]) -> Tuple[int, str]:
        """
        Evaluate a player's action and determine karma change.
        
        Args:
            action: The player's action/choice
            context: Dictionary containing relevant context (last message, current situation, etc.)
            
        Returns:
            Tuple of (karma_change, explanation)
        """
        prompt = """
You are a karma evaluator for a text-based RPG. Your job is to analyze player actions and determine how they should affect their karma score.
Consider the following factors:
1. Moral implications of the choice
2. Impact on others
3. Intentions behind the action
4. Context of the situation
5. Long-term consequences

Current context:
Last gamemaster message: {last_message}
Player's action: {action}
Current situation: {situation}

Based on this action, determine the karma change (-15 to +15) and provide a brief explanation.
ONLY return your response in this exact format:
KARMA_CHANGE: [number]
EXPLANATION: [one sentence explanation]
""".format(
            action=action,
            last_message=context.get('last_message', ''),
            situation=context.get('situation', '')
        )
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            
            # Parse response
            karma_line = next(line for line in response.split('\n') if line.startswith('KARMA_CHANGE:'))
            explanation_line = next(line for line in response.split('\n') if line.startswith('EXPLANATION:'))
            
            karma_change = int(karma_line.split(':')[1].strip())
            explanation = explanation_line.split(':')[1].strip()
            
            # Ensure karma change is within bounds
            karma_change = max(-10, min(10, karma_change))
            
            return karma_change, explanation
            
        except Exception as e:
            print(f"Error evaluating karma: {e}")
            return 0, "Unable to evaluate karma change for this action."
    
    def calculate_final_karma(self, current_karma: int, karma_change: int) -> int:
        """
        Calculate the final karma value ensuring it stays within bounds.
        
        Args:
            current_karma: Current karma value
            karma_change: Proposed karma change
            
        Returns:
            New karma value between -100 and 100
        """
        new_karma = current_karma + karma_change
        return max(-100, min(100, new_karma)) 