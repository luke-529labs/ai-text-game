from langchain_openai import ChatOpenAI
import random
import re
from typing import Dict, List, Optional, Any, Tuple


class GameState:
    """Represents the current state of the game and player."""
    def __init__(self, name: str):
        self.name: str = name
        self.health: int = 100
        self.karma: int = 0
        self.inventory: List[str] = []
        self.turn: int = 0
        self.last_gamemaster_message: str = ""
        self.last_player_message: str = ""
        self.turn_summary: str = ""
        self.chosen_setting: str = ""


class StoryGenerator:
    """Handles generation of narrative elements and story progression."""
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def generate_initial_situation(self, setting: str) -> str:
        """Generate the initial situation for a new life."""
        prompt = """
You are a dungeon master for a text based RPG. You are given a setting and you need to generate a new situation for the player. 
The player has just reincarnated into a new life and wakes up with no memories in the following setting: {setting}. 
Give the player a brief intro based on the setting and a few directions that they might go with their new life. Be consise yet descriptive and ensure there are some unique choices which could lead to action. 
Everything should be written in the second person. Please return only a player-facing message and nothing else.
""".format(setting=setting)
        return self.llm.invoke(prompt).content

    def generate_narrative_element(self, state: GameState) -> Dict[str, str]:
        """Generate a context-aware narrative element to advance the story."""
        element_type = random.choice(["CHOICE", "CHARACTER", "ACTION"])
        
        prompt = """
You are a narrative designer for a text-based RPG. Based on the current context, generate a {element_type}.

Current context:
Last gamemaster message: {last_message}
Player's last action: {last_action}
Current inventory: {inventory}
Current location/situation: {setting}

{specific_instructions}

Return only the narrative element, nothing else. Be concise but compelling.
""".format(
            element_type=element_type,
            last_message=state.last_gamemaster_message,
            last_action=state.last_player_message,
            inventory=state.inventory,
            setting=state.chosen_setting,
            specific_instructions={
                "CHOICE": "Create a dilemma or choice the player must face. Format: 'You must decide: [brief compelling choice]'",
                "CHARACTER": "Introduce a new character with a line of dialogue. Format: '[Character description]: \"[intriguing dialogue]\"'",
                "ACTION": "Create a sudden action that demands player response. Format: 'Suddenly, [unexpected event or action]'"
            }[element_type]
        )
        
        return {
            'type': element_type,
            'content': self.llm.invoke(prompt).content.strip()
        }


class TurbulenceSystem:
    """Handles generation and management of turbulence events."""
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def should_add_turbulence(self, turn: int) -> bool:
        """Determine if turbulence should be added based on turn number."""
        if turn < 1:
            return False
        
        # Turbulence chance increases with turns
        if turn <= 5:
            chance = 0.10
        elif turn <= 10:
            chance = 0.20
        else:
            chance = 0.30
        
        return random.random() < chance
    
    def generate_turbulence_event(self, state: GameState) -> Dict[str, Any]:
        """Generate a turbulence event based on current game state."""
        # Calculate lethality chance based on karma
        karma_factor = (state.karma + 100) / 200
        lethal_chance = 0.80 - (karma_factor * 0.75)
        
        # Determine if event should be lethal
        is_lethal = self._determine_lethality(state, lethal_chance)
        
        # Generate the event description
        event = self._generate_event_description(state, is_lethal)
        
        return {
            'event': event,
            'is_lethal': is_lethal
        }
    
    def _determine_lethality(self, state: GameState, lethal_chance: float) -> bool:
        """Determine if the turbulence should be lethal."""
        prompt = """
You are a fate-determining AI for a text-based RPG. Based on the following context, determine if this turbulence event should be lethal.

Current game state:
- Player's karma: {karma} (-100 to 100)
- Current turn: {turn}
- Player's health: {health}
- Current inventory: {inventory}
- Last action: {last_action}

Mathematical chance of lethality based on karma: {lethal_chance:.1%}

Additional factors to consider:
1. Player's recent actions and choices
2. Current story context
3. Dramatic timing
4. Current inventory items that might help survival

Should this turbulence event be lethal? Respond with only 'YES' or 'NO'.
""".format(
            karma=state.karma,
            turn=state.turn,
            health=state.health,
            inventory=state.inventory,
            last_action=state.last_player_message,
            lethal_chance=lethal_chance
        )
        
        return self.llm.invoke(prompt).content.strip().upper() == 'YES'
    
    def _generate_event_description(self, state: GameState, is_lethal: bool) -> str:
        """Generate the description of the turbulence event."""
        prompt = """
You are a dungeon master creating a dynamic event in a text-based RPG. Generate a context-appropriate conflict or challenge based on the current situation.

Current context:
Last gamemaster message: {last_message}
Player's last action: {last_action}
Current inventory: {inventory}
Current health: {health}
Karma: {karma}

{lethality_instruction}

Generate a single sentence describing a sudden event that creates conflict or danger. The event should:
1. Feel natural within the current context
2. Create immediate tension
3. Connect to the current story if possible
4. Not reveal if it's lethal or not in its description

Return only the event description, nothing else.
""".format(
            last_message=state.last_gamemaster_message,
            last_action=state.last_player_message,
            inventory=state.inventory,
            health=state.health,
            karma=state.karma,
            lethality_instruction="IMPORTANT: This event MUST result in the player's death this turn." if is_lethal else "This event should create significant danger but survival should be possible."
        )
        
        return self.llm.invoke(prompt).content.strip()


class ResponseParser:
    """Handles parsing and validation of LLM responses."""
    @staticmethod
    def parse_response(response: Any, current_state: GameState) -> Dict[str, Any]:
        """Parse the LLM response and extract game state variables."""
        try:
            if not hasattr(response, 'content'):
                return ResponseParser._get_default_response(current_state)

            content_match = re.search(r'START_LLM_GENERATED_CONTENT:(.*?)END_LLM_GENERATED_CONTENT', 
                                    response.content, re.DOTALL)
            
            if not content_match:
                return ResponseParser._handle_malformed_response(response.content, current_state)
            
            content = content_match.group(1)
            results = ResponseParser._extract_components(content, current_state)
            return ResponseParser._clean_and_validate_results(results, current_state)
            
        except Exception as e:
            print(f"\nError parsing LLM response: {e}")
            return ResponseParser._get_default_response(current_state)
    
    @staticmethod
    def _extract_components(content: str, current_state: GameState) -> Dict[str, Any]:
        """Extract individual components from the response content."""
        patterns = {
            'health': r'\*\*\*health:\s*(\d+)',
            'inventory': r'\*\*\*inventory:\s*(.*?)(?:\n|$)',
            'karma': r'\*\*\*karma:\s*(-?\d+)',
            'gamemaster_message': r'\*\*\*gamemaster_message:\s*(.*?)(?:\n|$)',
            'image_prompt': r'\*\*\*image_prompt:\s*(.*?)(?:\n|$)',
            'turn_summary': r'\*\*\*turn_summary:\s*(.*?)(?:\n|$)'
        }
        
        results = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.DOTALL)
            if not match:
                results[key] = ResponseParser._get_default_value(key, current_state)
            else:
                results[key] = match.group(1).strip()
        
        return results
    
    @staticmethod
    def _clean_and_validate_results(results: Dict[str, Any], current_state: GameState) -> Dict[str, Any]:
        """Clean and validate the parsed results."""
        try:
            results['health'] = min(100, max(0, int(results['health'])))
            results['karma'] = min(100, max(-100, int(results['karma'])))
            
            # Clean up inventory
            inventory_str = results['inventory']
            inventory_str = re.sub(r'[\[\]\'"\\]+', '', inventory_str)
            inventory_items = [
                item.strip() for item in inventory_str.split(',')
                if item.strip() and not item.strip().startswith('[') and not item.strip().startswith(']')
            ]
            seen = set()
            results['inventory'] = [x for x in inventory_items if not (x in seen or seen.add(x))]
            
        except ValueError:
            results['health'] = current_state.health
            results['karma'] = current_state.karma
            results['inventory'] = current_state.inventory
        
        return results
    
    @staticmethod
    def _get_default_value(key: str, state: GameState) -> str:
        """Get default value for a specific field."""
        defaults = {
            'health': str(state.health),
            'inventory': ','.join(state.inventory) if state.inventory else '',
            'karma': str(state.karma),
            'gamemaster_message': "I'm having trouble understanding what happened. Please try again.",
            'image_prompt': "A mysterious scene",
            'turn_summary': state.turn_summary if state.turn_summary else "The adventure begins..."
        }
        return defaults.get(key, '')
    
    @staticmethod
    def _get_default_response(state: GameState) -> Dict[str, Any]:
        """Get a complete default response."""
        return {
            'health': state.health,
            'inventory': state.inventory,
            'karma': state.karma,
            'gamemaster_message': "I apologize, but I'm having trouble processing what happened. Please try your action again.",
            'image_prompt': "A mysterious scene",
            'turn_summary': state.turn_summary if state.turn_summary else "The adventure begins..."
        }
    
    @staticmethod
    def _handle_malformed_response(content: str, state: GameState) -> Dict[str, Any]:
        """Handle malformed responses by preserving any useful content."""
        response = ResponseParser._get_default_response(state)
        if content:
            response['gamemaster_message'] = content.strip()
            response['turn_summary'] = f"{state.turn_summary}\nTurn {state.turn + 1}: {state.last_player_message}"
        return response


class Game:
    """Main game class that coordinates all game components."""
    def __init__(self):
        self.llm = ChatOpenAI()
        self.story_generator = StoryGenerator(self.llm)
        self.turbulence_system = TurbulenceSystem(self.llm)
        self.state: Optional[GameState] = None
    
    def start_new_game(self):
        """Start a new game session."""
        print("Welcome to the Text-Based RPG!")
        player_name = input("Enter your character name: ")
        self.state = GameState(player_name)
        self._start_new_situation()
        
        try:
            while True:
                self._process_turn()
        except KeyboardInterrupt:
            print("\nThanks for playing!")
    
    def _start_new_situation(self):
        """Initialize a new situation/life for the player."""
        self._load_random_setting()
        situation = self.story_generator.generate_initial_situation(self.state.chosen_setting)
        print("\nNew Situation:")
        print(situation)
        print("\n")
        self.state.last_gamemaster_message = situation
        self._get_player_input()
    
    def _load_random_setting(self):
        """Load a random setting from the settings file."""
        with open('situations.txt', 'r') as f:
            settings = [line.rstrip() for line in f.readlines()]
        self.state.chosen_setting = random.choice(settings)
    
    def _process_turn(self):
        """Process a single game turn."""
        # Generate narrative element
        narrative_element = self.story_generator.generate_narrative_element(self.state)
        
        # Check for turbulence
        turbulence_result = self._handle_turbulence()
        
        # Generate and process response
        response = self._generate_turn_response(narrative_element, turbulence_result)
        parsed_response = ResponseParser.parse_response(response, self.state)
        self._update_game_state(parsed_response)
        
        # Check for death
        if self.state.health <= 0:
            print("\nYou have died! Reincarnating into a new life...\n")
            self._start_new_situation()
        else:
            self._get_player_input()
    
    def _handle_turbulence(self) -> Optional[Dict[str, Any]]:
        """Handle turbulence events if they occur."""
        if self.turbulence_system.should_add_turbulence(self.state.turn):
            result = self.turbulence_system.generate_turbulence_event(self.state)
            print("\n⚠️ UNEXPECTED EVENT! ⚠️")
            return result
        return None
    
    def _generate_turn_response(self, narrative_element: Dict[str, str], 
                              turbulence_result: Optional[Dict[str, Any]]) -> Any:
        """Generate the turn response from the LLM."""
        # Format inventory for prompt
        inventory_str = ", ".join(self.state.inventory) if self.state.inventory else "empty"
        
        # Build turbulence components if present
        turbulence = ""
        turbulence_instruction = ""
        if turbulence_result:
            turbulence = f"\nSUDDEN EVENT: {turbulence_result['event']}\n"
            if turbulence_result['is_lethal']:
                turbulence_instruction = "IMPORTANT: This event is lethal. You MUST end this turn with the player's death (set health to 0) and describe their demise in a narratively satisfying way."
            else:
                turbulence_instruction = "IMPORTANT: A sudden event has occurred! Incorporate this event into your response with appropriate consequences and challenges."
        
        # Generate the prompt
        prompt = self._build_turn_prompt(
            narrative_element, inventory_str, turbulence, turbulence_instruction
        )
        
        return self.llm.invoke(prompt)
    
    def _build_turn_prompt(self, narrative_element: Dict[str, str], inventory_str: str,
                          turbulence: str, turbulence_instruction: str) -> str:
        """Build the prompt for the turn."""
        return """
You are a skilled dungeon master for a text-based RPG. Your job is to create an engaging and dynamic story that responds to player choices while maintaining appropriate challenge and consequences.

NARRATIVE ELEMENT: {narrative_element}
ELEMENT TYPE: {element_type}

IMPORTANT RULES:
1. Your response MUST incorporate and directly address the narrative element above
2. Keep the story moving forward - don't stay in one place or situation too long
3. Actions should have clear consequences for health and karma
4. Maintain narrative continuity with previous events
5. Be concise but descriptive
6. For inventory items, use simple comma-separated text (e.g., "rusty sword, health potion, map")

IMPORTANT: You must respond in the exact format specified below. Do not deviate from this format:

The player is named {name}, they have {health}/100 health and the following items in their inventory: {inventory}. Their karma is {karma} (scale of -100 to 100) which will determine their luck and change based on their choices.
It is turn {turn}. 

Here is context of the last turn:
Gamemaster: {last_gamemaster_message}
Player: {last_player_message}{turbulence}

Here is a summary of the player's turns so far: {turn_summary}

{turbulence_instruction}

YOU MUST RESPOND IN THIS EXACT FORMAT:
START_LLM_GENERATED_CONTENT:
***health: [number between 0-100]
***inventory: [simple comma-separated list of items, no brackets or quotes]
***karma: [number between -100 and 100]
***gamemaster_message: [your response to the player's action]
***image_prompt: [brief scene description]
***turn_summary: [summary including this turn]
END_LLM_GENERATED_CONTENT
""".format(
            name=self.state.name,
            health=self.state.health,
            inventory=inventory_str,
            karma=self.state.karma,
            turn=self.state.turn,
            last_gamemaster_message=self.state.last_gamemaster_message,
            last_player_message=self.state.last_player_message,
            turn_summary=self.state.turn_summary,
            turbulence=turbulence,
            turbulence_instruction=turbulence_instruction,
            narrative_element=narrative_element['content'],
            element_type=narrative_element['type']
        )
    
    def _update_game_state(self, parsed_response: Dict[str, Any]):
        """Update the game state with the parsed response."""
        self.state.health = parsed_response['health']
        self.state.inventory = parsed_response['inventory']
        self.state.karma = parsed_response['karma']
        self.state.last_gamemaster_message = parsed_response['gamemaster_message']
        self.state.turn_summary = parsed_response['turn_summary']
        self.state.turn += 1
        
        # Display current state to player
        print("\nGamemaster:", self.state.last_gamemaster_message)
        print(f"\nStatus - Health: {self.state.health} | Karma: {self.state.karma}")
        if self.state.inventory:
            print("Inventory:", ", ".join(self.state.inventory))
        print("\n")
    
    def _get_player_input(self):
        """Get input from the player."""
        self.state.last_player_message = input("What do you want to do? ")


if __name__ == "__main__":
    game = Game()
    game.start_new_game()