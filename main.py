from langchain_openai import ChatOpenAI
import random
import re
import os
import requests
import pygame
import threading
from typing import Dict, List, Optional, Any, Tuple
from game_ui import GameUI
from image_generator import ImageGenerator
from karma_manager import KarmaManager
from health_manager import HealthManager


class GameState:
    """Represents the current state of the game and player."""
    def __init__(self, name: str):
        self.name: str = name
        self.karma: int = 0  # Karma is initialized only once and persists between lives
        self.chosen_setting: str = ""
        self.reset_life_values()
    
    def reset_life_values(self):
        """Reset values that should start fresh with each new life."""
        self.health: int = 100
        self.inventory: List[str] = []
        self.turn: int = 0
        self.last_gamemaster_message: str = ""
        self.last_player_message: str = ""
        self.turn_summary: str = ""
        self.image_prompt: str = ""
        self.current_image: Optional[pygame.Surface] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for UI updates."""
        return {
            'name': self.name,
            'health': self.health,
            'karma': self.karma,
            'inventory': self.inventory,
            'turn': self.turn,
            'last_message': self.last_gamemaster_message,
            'image_prompt': self.image_prompt
        }


class StoryGenerator:
    """Handles generation of narrative elements and story progression."""
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def generate_initial_situation(self, setting: str) -> str:
        """Generate the initial situation for a new life."""
        prompt = """
You are a narrative guide for an immersive text adventure. Given a setting, create an engaging initial situation for the player.
The player has just reincarnated into a new life and wakes up with no memories in the following setting: {setting}. 
Describe their immediate surroundings and circumstances, providing 2-3 clear potential paths or choices that naturally fit the setting.
Be concise yet descriptive, and ensure the choices feel authentic to the environment.

IMPORTANT: Include at least one item that the player would logically have or could immediately find in this setting 
(e.g., appropriate clothing, tools, or objects that fit the context). This will be added to their starting inventory.

Everything should be written in the second person. Please return only a player-facing message and nothing else.
""".format(setting=setting)
        return self.llm.invoke(prompt).content

    def generate_narrative_element(self, state: GameState) -> Dict[str, str]:
        """Generate a context-aware narrative element to advance the story."""
        # Analyze the last player action to determine the most appropriate element type
        action_lower = state.last_player_message.lower()
        
        # Determine element type based on player's last action
        if any(word in action_lower for word in ['talk', 'ask', 'speak', 'say', 'tell', 'respond']):
            element_type = "DIALOGUE"
        elif any(word in action_lower for word in ['attack', 'fight', 'punch', 'shoot', 'defend', 'dodge', 'run']):
            element_type = "ACTION"
        elif any(word in action_lower for word in ['open', 'enter', 'go', 'walk', 'move', 'explore', 'look', 'search']):
            element_type = "EXPLORATION"
        elif any(word in action_lower for word in ['use', 'take', 'grab', 'pick', 'drop', 'give', 'hold', 'wear']):
            element_type = "ITEM"
        else:
            # If no specific action type is detected, choose based on context and recent events
            element_type = random.choice(["DIALOGUE", "EXPLORATION", "ITEM", "ACTION"])
        
        prompt = """
You are crafting the next story beat in an immersive text adventure. Based on the current context and the player's last action, 
create a natural progression that maintains narrative consistency and advances the story.

Current context:
Setting: {setting}
Last story beat: {last_message}
Player's action: {last_action}
Available items: {inventory}
Story so far: {turn_summary}
Current turn: {turn}

Action type: {element_type}

{specific_instructions}

Your response should feel like a natural consequence of the player's action and previous events. 
Return only the story beat, nothing else. Be specific and create clear paths forward.
""".format(
            element_type=element_type,
            last_message=state.last_gamemaster_message,
            last_action=state.last_player_message,
            inventory=state.inventory,
            setting=state.chosen_setting,
            turn=state.turn,
            turn_summary=state.turn_summary,
            specific_instructions={
                "DIALOGUE": "Create a character's response that feels natural to the setting and advances the story. Format: '[Character description] responds: \"[contextually appropriate dialogue that moves the story forward]\"'",
                "ACTION": "Describe the immediate outcome of the action and its consequences. Format: '[Detailed outcome] Your next options: [2-3 logical choices based on the outcome]'",
                "EXPLORATION": "Describe what the player discovers, maintaining consistency with the setting. Format: '[Discovery description] You notice: [1-2 interesting elements that fit the environment]'",
                "ITEM": "Create a realistic scenario involving items that fits the setting. Format: '[Item interaction and its immediate effects]'"
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
        if turn < 2:  # Give players more time to establish themselves
            return False
        
        # Turbulence chance increases with turns but caps at 30%
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
You are determining the outcome of a sudden event in an immersive text adventure. Based on the following context, 
decide if this event should result in a critical outcome.

Current story state:
- Setting: {setting}
- Recent events: {turn_summary}
- Player's karma: {karma} (-100 to 100)
- Current turn: {turn}
- Player's health: {health}
- Available items: {inventory}
- Last action: {last_action}

Mathematical chance of critical outcome based on karma: {lethal_chance:.1%}

Consider:
1. The current setting and situation
2. Recent story developments
3. Available resources or items that could help
4. Dramatic timing and narrative impact
5. Player's previous choices and their consequences

Should this event be critical? Respond with only 'YES' or 'NO'.
""".format(
            setting=state.chosen_setting,
            turn_summary=state.turn_summary,
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
You are creating a sudden event in an immersive text adventure. Generate an unexpected but contextually appropriate 
development that creates tension or challenge based on the current situation.

Current context:
Setting: {setting}
Recent events: {turn_summary}
Last story beat: {last_message}
Player's last action: {last_action}
Available items: {inventory}
Current health: {health}
Karma: {karma}

{lethality_instruction}

Create a single sentence describing a sudden event that:
1. Feels natural within the current setting
2. Connects to recent story developments
3. Creates immediate tension or urgency
4. Could reasonably lead to the required outcome
5. Doesn't reveal its critical/non-critical nature

Return only the event description, nothing else.
""".format(
            setting=state.chosen_setting,
            turn_summary=state.turn_summary,
            last_message=state.last_gamemaster_message,
            last_action=state.last_player_message,
            inventory=state.inventory,
            health=state.health,
            karma=state.karma,
            lethality_instruction="IMPORTANT: This event must lead to a critical outcome this turn." if is_lethal else "This event should create significant challenge but allow for potential survival."
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
        # Check if OpenAI API key is available
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("Warning: OPENAI_API_KEY environment variable not set.")
            print("Image generation will be disabled.")
            print("Set it using: export OPENAI_API_KEY='your-api-key'")
        
        self.llm = ChatOpenAI()
        self.story_generator = StoryGenerator(self.llm)
        self.turbulence_system = TurbulenceSystem(self.llm)
        self.karma_manager = KarmaManager(self.llm)
        self.health_manager = HealthManager(self.llm)  # Add health manager
        self.state: Optional[GameState] = None
        self.ui = GameUI()
        
        # Initialize image generator if API key is available
        self.image_generator = ImageGenerator(api_key) if api_key else None
        self.image_generation_enabled = bool(api_key)
        
        # For async image generation
        self.image_thread = None
        self.is_generating_image = False
    
    def start_new_game(self):
        """Start a new game session."""
        self.ui.add_system_message("Welcome to the AI Text Adventure!")
        if self.image_generation_enabled:
            self.ui.add_system_message("Image generation is enabled. You'll see scenes visualized as you play.")
        else:
            self.ui.add_system_message("Image generation is disabled. Set OPENAI_API_KEY to enable it.")
            
        self.ui.add_system_message("Enter your character name: ")
        self.ui.update_display({'health': 100, 'karma': 0, 'inventory': []})
        
        # Main game loop
        running = True
        name_entered = False
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                
                command = self.ui.handle_event(event)
                if command is not None:
                    if not name_entered:
                        self.state = GameState(command)
                        name_entered = True
                        self.ui.add_system_message(f"Welcome, {command}!")
                        self._start_new_situation()
                    else:
                        self.state.last_player_message = command
                        self.ui.add_player_message(command)
                        self._process_turn()
                
            # Update display every frame
            self.ui.update_display(self.state.to_dict() if self.state else {})
            
        self.ui.cleanup()
    
    def _load_karma_based_setting(self) -> str:
        """
        Load a setting based on the player's karma level.
        Returns the selected setting.
        """
        karma = self.state.karma
        
        # Define karma ranges
        if karma > 75:
            category = "VERY_POSITIVE"
        elif karma > 35:
            category = "POSITIVE"
        elif karma > 0:
            category = "SLIGHTLY_POSITIVE"
        elif karma == 0:
            category = "NEUTRAL"
        elif karma >= -35:
            category = "SLIGHTLY_NEGATIVE"
        elif karma >= -75:
            category = "NEGATIVE"
        else:
            category = "VERY_NEGATIVE"
        
        try:
            # Read the karma situations file
            with open('karma_situations.txt', 'r') as f:
                content = f.read()
            
            # Split into sections and find our category
            sections = content.split('[')
            category_section = next(s for s in sections if s.startswith(category))
            
            # Extract situations from the category
            situations = [
                line.strip() for line in category_section.split('\n')[1:]  # Skip category name
                if line.strip() and not line.strip().startswith('#')  # Skip comments and empty lines
            ]
            
            # Select a random situation from the appropriate category
            if situations:
                chosen_setting = random.choice(situations)
                karma_level = category.replace('_', ' ').title()
                self.ui.add_system_message(f"\nYour karma level ({karma}) has led you to a {karma_level} realm...")
                return chosen_setting
                
        except Exception as e:
            print(f"Error loading karma-based setting: {e}")
            # Fallback to neutral if there's an error
            return "Crossroads Inn"
    
    def _load_random_setting(self):
        """Load a setting based on karma."""
        self.state.chosen_setting = self._load_karma_based_setting()
        
    def _start_new_situation(self):
        """Initialize a new situation/life for the player."""
        # Store karma before reset
        current_karma = self.state.karma if self.state else 0
        
        # Reset life-specific values
        if self.state:
            self.state.reset_life_values()
            self.state.karma = current_karma  # Restore karma as it persists between lives
            
            # Inform player about karma carrying over
            if current_karma != 0:
                karma_message = "positive" if current_karma > 0 else "negative"
                self.ui.add_system_message(f"\nYour karma of {current_karma} carries over to your next life.")
                if abs(current_karma) > 75:
                    intensity = "profound"
                elif abs(current_karma) > 35:
                    intensity = "significant"
                else:
                    intensity = "subtle"
                self.ui.add_system_message(f"Your {karma_message} karma will have a {intensity} influence on your next incarnation...")
        
        self._load_random_setting()
        situation = self.story_generator.generate_initial_situation(self.state.chosen_setting)
        self.ui.add_system_message("\nNew Situation:")
        self.ui.add_gamemaster_message(situation)
        self.state.last_gamemaster_message = situation
        
        # Extract possible starting items from the initial situation
        self._extract_initial_items(situation)
        
        # Generate initial image (async)
        if self.image_generation_enabled:
            self._generate_scene_image(f"A scene depicting: {self.state.chosen_setting}. {situation}")
    
    def _extract_initial_items(self, situation: str):
        """Try to extract items mentioned in the initial situation to add to inventory."""
        # This is a simple implementation - the more sophisticated version would use the LLM
        item_prompt = f"""
You are an inventory manager for a text-based RPG. Given the following initial situation description, 
identify 1-2 items that the player should logically start with or could immediately find.
The items should be appropriate for the setting and could be useful for the adventure.

Situation: {situation}

Return only a comma-separated list of items, nothing else.
"""
        try:
            items_response = self.llm.invoke(item_prompt).content.strip()
            items = [item.strip() for item in items_response.split(',') if item.strip()]
            if items:
                self.state.inventory = items[:2]  # Limit to 2 items max
                items_str = ", ".join(self.state.inventory)
                self.ui.add_system_message(f"Starting items: {items_str}")
        except Exception as e:
            print(f"Error extracting initial items: {e}")
    
    def _generate_scene_image(self, prompt: str):
        """Generate an image for the current scene and update the UI."""
        if not self.image_generation_enabled or not self.image_generator:
            return
            
        self.ui.add_system_message("Generating scene image...")
        self.ui.is_loading_image = True
        
        # Start image generation in a separate thread
        self.is_generating_image = True
        self.image_thread = threading.Thread(
            target=self._generate_image_thread, 
            args=(prompt,)
        )
        self.image_thread.daemon = True  # Thread will exit when main program exits
        self.image_thread.start()
    
    def _generate_image_thread(self, prompt: str):
        """Thread function to generate image in the background."""
        try:
            # Generate image
            image = self.image_generator.generate_image(prompt)
            
            if image:
                # Scale image to fit display area
                scaled_image = self._scale_image_to_fit(image)
                
                # Update UI with new image (this will happen in the background)
                self.state.current_image = scaled_image
                self.ui.current_image = scaled_image
                self.ui.is_loading_image = False
                self.ui.add_system_message("Scene image updated.")
            else:
                self.ui.is_loading_image = False
                self.ui.add_system_message("Failed to generate scene image.")
        except Exception as e:
            print(f"Error generating scene image: {e}")
            self.ui.is_loading_image = False
            self.ui.add_system_message("Error generating scene image.")
        finally:
            self.is_generating_image = False
    
    def _scale_image_to_fit(self, image: pygame.Surface) -> pygame.Surface:
        """Scale image to fit in the UI's image area while maintaining aspect ratio."""
        # Get the dimensions of the target area
        target_width = self.ui.image_area.width
        target_height = self.ui.image_area.height
        
        # Get original image dimensions
        orig_width, orig_height = image.get_size()
        
        # Calculate scale factor
        width_ratio = target_width / orig_width
        height_ratio = target_height / orig_height
        scale_factor = min(width_ratio, height_ratio)
        
        # Calculate new dimensions
        new_width = int(orig_width * scale_factor)
        new_height = int(orig_height * scale_factor)
        
        # Scale the image
        return pygame.transform.scale(image, (new_width, new_height))
    
    def _process_turn(self):
        """Process a single game turn."""
        # Evaluate health for the player's action
        health_context = {
            'last_message': self.state.last_gamemaster_message,
            'situation': self.state.chosen_setting,
            'inventory': self.state.inventory
        }
        health_change, health_explanation, is_fatal = self.health_manager.evaluate_health_change(
            self.state.last_player_message,
            health_context
        )
        
        # Update health before generating response
        old_health = self.state.health
        self.state.health = self.health_manager.calculate_final_health(old_health, health_change)
        
        # If there was a significant health change or healing attempt, notify the player
        if abs(health_change) >= 10 or self.health_manager.is_healing_attempt(self.state.last_player_message):
            if health_change > 0:
                self.ui.add_system_message(f"Health +{health_change}: {health_explanation}")
            elif health_change < 0:
                self.ui.add_system_message(f"Health {health_change}: {health_explanation}")
        
        # Evaluate karma for the player's action
        karma_context = {
            'last_message': self.state.last_gamemaster_message,
            'situation': self.state.chosen_setting
        }
        karma_change, karma_explanation = self.karma_manager.evaluate_karma_change(
            self.state.last_player_message,
            karma_context
        )
        
        # Update karma before generating response
        old_karma = self.state.karma
        self.state.karma = self.karma_manager.calculate_final_karma(old_karma, karma_change)
        
        # If there was a significant karma change, notify the player
        if abs(karma_change) >= 5:
            self.ui.add_system_message(f"Karma {karma_change:+d}: {karma_explanation}")
        
        # Generate narrative element
        narrative_element = self.story_generator.generate_narrative_element(self.state)
        
        # Check for turbulence
        turbulence_result = self._handle_turbulence()
        
        # Generate and process response
        response = self._generate_turn_response(narrative_element, turbulence_result)
        parsed_response = ResponseParser.parse_response(response, self.state)
        
        # Update game state but preserve our karma and health calculations
        saved_karma = self.state.karma
        saved_health = self.state.health
        self._update_game_state(parsed_response)
        self.state.karma = saved_karma  # Keep our karma calculation instead of the LLM's
        self.state.health = saved_health  # Keep our health calculation instead of the LLM's
        
        # Check for death
        if self.state.health <= 0 or is_fatal:
            if is_fatal:
                self.state.health = 0  # Ensure health is 0 for fatal actions
                self.ui.add_system_message(f"\nFatal: {health_explanation}")
            self.ui.add_system_message("\nYou have died! Reincarnating into a new life...\n")
            self._start_new_situation()
    
    def _handle_turbulence(self) -> Optional[Dict[str, Any]]:
        """Handle turbulence events if they occur."""
        if self.turbulence_system.should_add_turbulence(self.state.turn):
            result = self.turbulence_system.generate_turbulence_event(self.state)
            self.ui.add_system_message("\n⚠️ UNEXPECTED EVENT! ⚠️")
            self.ui.add_system_message(result['event'])
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
        # Add specific instructions based on the narrative element type
        element_type_instructions = {
            "DIALOGUE": """
DIALOGUE FOCUS: Your response must:
1. Include the character's direct response to the player
2. Maintain the character's personality and knowledge
3. Advance the plot through the conversation
4. Provide clear conversational options or next steps
""",
            "ACTION": """
ACTION FOCUS: Your response must:
1. Describe the immediate outcome of the action
2. Account for weapons/items used (or lack thereof)
3. Update health appropriately based on success/failure
4. Present clear follow-up tactical options
""",
            "EXPLORATION": """
EXPLORATION FOCUS: Your response must:
1. Vividly describe what the player discovers
2. Include at least one interactive element
3. Maintain spatial consistency with previous descriptions
4. Create opportunities for meaningful choices
""",
            "ITEM": """
ITEM FOCUS: Your response must:
1. Clearly describe how items are used or acquired
2. Update inventory appropriately
3. Show meaningful consequences of item use
4. Create future opportunities for item use
"""
        }.get(narrative_element['type'], "")

        return """
You are a skilled dungeon master for a text-based RPG. Your job is to create an engaging and dynamic story that responds to player choices while maintaining appropriate challenge and consequences.

CURRENT SCENE CONTEXT:
Location: {setting}
Recent events: {turn_summary}
Last gamemaster message: {last_gamemaster_message}
Player's action: {last_player_message}

NARRATIVE ELEMENT TO INCORPORATE: {narrative_element}
ELEMENT TYPE: {element_type}

CRITICAL REQUIREMENTS:
1. MAINTAIN CONTEXT: Your response must directly follow from the player's action and maintain consistency with the current scene and previous events
2. CLEAR OUTCOMES: Describe specific consequences of the player's action
3. FORWARD MOMENTUM: Always end with clear options, discoveries, or next steps
4. SCENE CONSISTENCY: Keep track of and reference the physical space and characters previously mentioned
5. MEANINGFUL CHOICES: Present interesting decisions that affect the story

{element_type_instructions}

TECHNICAL RULES:
1. Keep responses concise but descriptive
2. Use simple comma-separated text for inventory
3. Health and karma changes should reflect action outcomes
4. Image prompts should capture the current scene{inventory_instruction}

The player {name} has:
- Health: {health}/100
- Karma: {karma} (-100 to 100)
- Inventory: {inventory}
- Current turn: {turn}{turbulence}

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
            setting=self.state.chosen_setting,
            turbulence=turbulence,
            turbulence_instruction=turbulence_instruction,
            narrative_element=narrative_element['content'],
            element_type=narrative_element['type'],
            element_type_instructions=element_type_instructions,
            inventory_instruction="" if narrative_element['type'] == "ITEM" else "\n5. Regularly create opportunities for inventory interaction"
        )
    
    def _update_game_state(self, parsed_response: Dict[str, Any]):
        """Update the game state with the parsed response."""
        # Check for inventory changes
        old_inventory = set(self.state.inventory)
        new_inventory = set(parsed_response['inventory'])
        
        # Detect added or removed items
        added_items = new_inventory - old_inventory
        removed_items = old_inventory - new_inventory
        
        # Update game state with parsed response
        self.state.health = parsed_response['health']
        self.state.inventory = parsed_response['inventory']
        self.state.karma = parsed_response['karma']
        self.state.last_gamemaster_message = parsed_response['gamemaster_message']
        self.state.turn_summary = parsed_response['turn_summary']
        self.state.image_prompt = parsed_response.get('image_prompt', "A mysterious scene")
        self.state.turn += 1
        
        # Display updates through UI
        self.ui.add_gamemaster_message(self.state.last_gamemaster_message)
        
        # Notify about inventory changes
        if added_items:
            items_str = ", ".join(added_items)
            self.ui.add_system_message(f"Added to inventory: {items_str}")
        
        if removed_items:
            items_str = ", ".join(removed_items)
            self.ui.add_system_message(f"Removed from inventory: {items_str}")
        
        # Generate new scene image asynchronously if image prompt is available
        if self.image_generation_enabled and self.state.image_prompt:
            # Make sure we're not already generating an image
            if not self.is_generating_image:
                self._generate_scene_image(self.state.image_prompt)


if __name__ == "__main__":
    game = Game()
    game.start_new_game()