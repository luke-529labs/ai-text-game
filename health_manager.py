from langchain_openai import ChatOpenAI
from typing import Dict, Tuple, List, Any

class HealthManager:
    """Handles evaluation and updates of player health based on their actions and context."""
    
    # List of healing-related keywords to check in player actions
    HEALING_KEYWORDS = [
        'heal', 'rest', 'sleep', 'bandage', 'medicine', 'potion', 'cure',
        'treat', 'recover', 'meditate', 'bind wound', 'patch', 'doctor',
        'medical', 'first aid', 'healing', 'health', 'restore'
    ]
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def evaluate_health_change(self, action: str, context: Dict[str, Any]) -> Tuple[int, str, bool]:
        """
        Evaluate a player's action and determine health change.
        
        Args:
            action: The player's action/choice
            context: Dictionary containing relevant context (inventory, situation, etc.)
            
        Returns:
            Tuple of (health_change, explanation, is_fatal)
        """
        # Check if this is a healing attempt
        is_healing_attempt = any(keyword in action.lower() for keyword in self.HEALING_KEYWORDS)
        
        prompt = """
You are a health evaluator for a text-based RPG. Your job is to analyze player actions and determine how they should affect their health.

Current context:
Last gamemaster message: {last_message}
Player's action: {action}
Current situation: {situation}
Current inventory: {inventory}
Is healing attempt: {is_healing}

Consider the following factors:
1. Physical danger of the action
2. Current situation dangers
3. Available resources/items
4. Potential for injury
5. If healing attempt, effectiveness based on method and resources

Rules:
1. Health changes should be between -50 and +25
2. Only allow healing if player specifically takes healing action AND has appropriate resources
3. Dangerous actions should have consequences
4. Some actions might be instantly fatal
5. Consider inventory items that might help or harm
6. If a situation would not have an immediate effect on health, return a health change of 0

Based on this action, determine the health change and provide a brief explanation.
ONLY return your response in this exact format:
HEALTH_CHANGE: [number]
EXPLANATION: [one sentence explanation]
IS_FATAL: [true/false]
""".format(
            action=action,
            last_message=context.get('last_message', ''),
            situation=context.get('situation', ''),
            inventory=context.get('inventory', []),
            is_healing=is_healing_attempt
        )
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            
            # Parse response
            health_line = next(line for line in response.split('\n') if line.startswith('HEALTH_CHANGE:'))
            explanation_line = next(line for line in response.split('\n') if line.startswith('EXPLANATION:'))
            fatal_line = next(line for line in response.split('\n') if line.startswith('IS_FATAL:'))
            
            health_change = int(health_line.split(':')[1].strip())
            explanation = explanation_line.split(':')[1].strip()
            is_fatal = fatal_line.split(':')[1].strip().lower() == 'true'
            
            # Ensure health change is within bounds
            if is_fatal:
                health_change = -100  # Ensure fatal actions result in death
            else:
                health_change = max(-50, min(25, health_change))
            
            return health_change, explanation, is_fatal
            
        except Exception as e:
            print(f"Error evaluating health: {e}")
            return 0, "Unable to evaluate health change for this action.", False
    
    def calculate_final_health(self, current_health: int, health_change: int) -> int:
        """
        Calculate the final health value ensuring it stays within bounds.
        
        Args:
            current_health: Current health value
            health_change: Proposed health change
            
        Returns:
            New health value between 0 and 100
        """
        new_health = current_health + health_change
        return max(0, min(100, new_health))
    
    def is_healing_attempt(self, action: str) -> bool:
        """
        Determine if the player's action is attempting to heal.
        
        Args:
            action: The player's action
            
        Returns:
            True if the action appears to be a healing attempt
        """
        return any(keyword in action.lower() for keyword in self.HEALING_KEYWORDS) 