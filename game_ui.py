import pygame
import pygame.freetype
from typing import List, Dict, Any, Optional, Tuple
import textwrap

class Colors:
    """Color constants used in the UI."""
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    GRAY = (128, 128, 128)
    DARK_GRAY = (64, 64, 64)
    DARKER_GRAY = (40, 40, 40)
    LIGHT_GRAY = (180, 180, 180)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    HEALTH_BAR = (220, 50, 50)
    KARMA_BAR_POSITIVE = (50, 220, 50)
    KARMA_BAR_NEGATIVE = (220, 50, 50)
    TEXT_COLOR = (240, 240, 240)
    PLAYER_TEXT = (120, 200, 255)  # Light blue for player messages
    GM_TEXT = (240, 240, 200)  # Light yellow for gamemaster
    SYSTEM_TEXT = (200, 200, 200)  # Light gray for system messages
    INPUT_BOX_ACTIVE = (100, 100, 255)
    INPUT_BOX_INACTIVE = (70, 70, 70)

class MessageType:
    """Enum for message types"""
    SYSTEM = 0
    PLAYER = 1
    GAMEMASTER = 2

class Message:
    """Represents a single message in the chat history"""
    def __init__(self, text: str, msg_type: int):
        self.text = text
        self.type = msg_type
    
    @property
    def color(self) -> Tuple[int, int, int]:
        """Get color based on message type"""
        if self.type == MessageType.SYSTEM:
            return Colors.SYSTEM_TEXT
        elif self.type == MessageType.PLAYER:
            return Colors.PLAYER_TEXT
        else:
            return Colors.GM_TEXT

class GameUI:
    """Handles the game's graphical user interface using PyGame."""
    
    def __init__(self, width: int = 1280, height: int = 720):
        pygame.init()
        pygame.freetype.init()
        
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("AI Text Adventure")
        
        # Load fonts
        self.main_font = pygame.freetype.SysFont('Arial', 16)
        self.header_font = pygame.freetype.SysFont('Arial', 24)
        self.bold_font = pygame.freetype.SysFont('Arial', 16, bold=True)
        
        # UI element dimensions
        self.text_area_height = height * 0.6
        self.input_height = 40
        self.status_height = 80
        self.padding = 20
        
        # Input box
        self.input_box = pygame.Rect(
            self.padding,
            self.height - self.input_height - self.padding,
            self.width - (2 * self.padding),
            self.input_height
        )
        self.input_text = ""
        self.input_active = False
        
        # Message history with type info
        self.messages: List[Message] = []
        self.max_messages = 50
        
        # Image area - moved to right side
        self.image_area = pygame.Rect(
            self.width - 320,
            self.padding + 80,  # Below status bars
            300,
            300
        )
        self.current_image: Optional[pygame.Surface] = None
        self.loading_animation_state = 0
        self.last_animation_time = 0
        self.is_loading_image = False
        
        # Frame rate control
        self.clock = pygame.time.Clock()
        self.fps = 60
        
        # Add prompt for input
        self.add_system_message("Welcome to the AI Text Adventure!")
    
    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """Handle PyGame events and return player input if enter is pressed."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.input_box.collidepoint(event.pos):
                self.input_active = True
            else:
                self.input_active = False
                
        elif event.type == pygame.KEYDOWN:
            if self.input_active:
                if event.key == pygame.K_RETURN and self.input_text.strip():
                    command = self.input_text
                    self.input_text = ""
                    return command
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                else:
                    self.input_text += event.unicode
        
        return None
    
    def add_system_message(self, message: str):
        """Add a system message to the display history."""
        # Handle loading messages specially
        if message == "Generating scene image...":
            self.is_loading_image = True
        elif message == "Scene image updated." or message == "Failed to generate scene image.":
            self.is_loading_image = False
            
        # Wrap text to fit the screen
        wrapped_text = textwrap.fill(message, width=80)
        for line in wrapped_text.split('\n'):
            self.messages.append(Message(line, MessageType.SYSTEM))
        
        # Keep only the last max_messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def add_player_message(self, message: str):
        """Add a player message to the display history."""
        # Format with player name
        formatted = f"You: {message}"
        
        # Wrap text to fit the screen
        wrapped_text = textwrap.fill(formatted, width=80)
        for line in wrapped_text.split('\n'):
            self.messages.append(Message(line, MessageType.PLAYER))
        
        # Keep only the last max_messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def add_gamemaster_message(self, message: str):
        """Add a gamemaster message to the display history."""
        # Format as gamemaster
        formatted = f"Gamemaster: {message}"
        
        # Wrap text to fit the screen
        wrapped_text = textwrap.fill(formatted, width=80)
        for line in wrapped_text.split('\n'):
            self.messages.append(Message(line, MessageType.GAMEMASTER))
        
        # Keep only the last max_messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def add_message(self, message: str):
        """Legacy method - adds a system message for backward compatibility."""
        self.add_system_message(message)
    
    def draw_status_bars(self, health: int, karma: int):
        """Draw health and karma bars."""
        # Health bar
        bar_width = 200
        bar_height = 20
        x = self.width - bar_width - self.padding
        y = self.padding
        
        # Draw health bar with label
        pygame.draw.rect(self.screen, Colors.DARK_GRAY, (x, y, bar_width, bar_height))
        health_width = (bar_width * health) // 100
        pygame.draw.rect(self.screen, Colors.HEALTH_BAR, (x, y, health_width, bar_height))
        
        health_text = f"Health: {health}"
        self.bold_font.render_to(self.screen, (x - 100, y), health_text, Colors.TEXT_COLOR)
        
        # Karma bar
        y += bar_height + 10
        pygame.draw.rect(self.screen, Colors.DARK_GRAY, (x, y, bar_width, bar_height))
        
        # Calculate karma position and color
        mid_point = x + (bar_width // 2)
        if karma >= 0:
            karma_width = (bar_width // 2) * karma // 100
            karma_color = Colors.KARMA_BAR_POSITIVE
            karma_x = mid_point
        else:
            karma_width = (bar_width // 2) * abs(karma) // 100
            karma_color = Colors.KARMA_BAR_NEGATIVE
            karma_x = mid_point - karma_width
        
        # Draw the karma bar
        pygame.draw.rect(self.screen, karma_color, (karma_x, y, karma_width, bar_height))
        
        # Draw center line and markers
        pygame.draw.line(self.screen, Colors.WHITE, (mid_point, y), (mid_point, y + bar_height), 1)
        
        # Draw karma value
        karma_text = f"Karma: {karma}"
        self.bold_font.render_to(self.screen, (x - 100, y), karma_text, Colors.TEXT_COLOR)
    
    def draw_inventory(self, inventory: List[str]):
        """Draw the inventory panel."""
        inventory_rect = pygame.Rect(
            self.padding,
            self.padding,
            200,
            self.text_area_height - (2 * self.padding)
        )
        
        pygame.draw.rect(self.screen, Colors.DARKER_GRAY, inventory_rect)
        
        # Draw header with background
        header_rect = pygame.Rect(
            inventory_rect.x,
            inventory_rect.y,
            inventory_rect.width,
            40
        )
        pygame.draw.rect(self.screen, Colors.DARK_GRAY, header_rect)
        
        self.header_font.render_to(
            self.screen,
            (inventory_rect.x + 10, inventory_rect.y + 10),
            "INVENTORY",
            Colors.TEXT_COLOR
        )
        
        # Draw items
        y = inventory_rect.y + 50
        if not inventory:
            self.main_font.render_to(
                self.screen,
                (inventory_rect.x + 20, y),
                "Empty",
                Colors.GRAY
            )
        else:
            for item in inventory:
                self.main_font.render_to(
                    self.screen,
                    (inventory_rect.x + 20, y),
                    f"• {item}",
                    Colors.TEXT_COLOR
                )
                y += 30
    
    def draw_text_area(self):
        """Draw the main text area with message history."""
        # Adjust text area to account for image area
        text_rect = pygame.Rect(
            250,
            self.padding,
            self.width - 590,  # Leave room for image
            self.text_area_height - (2 * self.padding)
        )
        
        pygame.draw.rect(self.screen, Colors.DARKER_GRAY, text_rect)
        
        # Draw messages
        # Calculate how many messages we can display
        line_height = 25
        visible_line_count = (text_rect.height - 20) // line_height
        
        # Get messages to display
        visible_messages = self.messages[-visible_line_count:] if len(self.messages) > visible_line_count else self.messages
        
        y = text_rect.y + 10
        for message in visible_messages:
            # Render messages based on type
            self.main_font.render_to(
                self.screen,
                (text_rect.x + 10, y),
                message.text,
                message.color
            )
            y += line_height
    
    def draw_input_box(self):
        """Draw the input box."""
        # Draw label
        self.main_font.render_to(
            self.screen, 
            (self.padding, self.height - self.input_height - self.padding - 25),
            "What do you want to do?",
            Colors.TEXT_COLOR
        )
        
        # Draw input box with border
        border = pygame.Rect(
            self.input_box.x - 2,
            self.input_box.y - 2,
            self.input_box.width + 4,
            self.input_box.height + 4
        )
        pygame.draw.rect(self.screen, Colors.LIGHT_GRAY, border)
        
        color = Colors.INPUT_BOX_ACTIVE if self.input_active else Colors.INPUT_BOX_INACTIVE
        pygame.draw.rect(self.screen, color, self.input_box)
        
        # Draw cursor
        cursor_text = self.input_text
        if self.input_active and pygame.time.get_ticks() % 1000 < 500:
            cursor_text += "|"
            
        # Draw input text
        text_surface, _ = self.main_font.render(cursor_text, Colors.TEXT_COLOR)
        self.screen.blit(
            text_surface,
            (self.input_box.x + 5, self.input_box.y + (self.input_box.height - text_surface.get_height()) // 2)
        )
    
    def _update_loading_animation(self):
        """Update the loading animation state."""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_animation_time > 300:  # Update every 300ms
            self.loading_animation_state = (self.loading_animation_state + 1) % 4
            self.last_animation_time = current_time
    
    def draw_image_area(self):
        """Draw the image area and current image if available."""
        # Draw the background and border
        border_rect = pygame.Rect(
            self.image_area.x - 2,
            self.image_area.y - 2,
            self.image_area.width + 4,
            self.image_area.height + 4
        )
        pygame.draw.rect(self.screen, Colors.LIGHT_GRAY, border_rect)
        pygame.draw.rect(self.screen, Colors.DARKER_GRAY, self.image_area)
        
        # Draw scene title
        title_rect = pygame.Rect(
            self.image_area.x,
            self.image_area.y - 30,
            self.image_area.width,
            25
        )
        self.header_font.render_to(
            self.screen,
            (title_rect.x, title_rect.y),
            "CURRENT SCENE",
            Colors.TEXT_COLOR
        )
        
        if self.current_image:
            # Calculate centered position for the image
            img_w, img_h = self.current_image.get_size()
            x_pos = self.image_area.x + (self.image_area.width - img_w) // 2
            y_pos = self.image_area.y + (self.image_area.height - img_h) // 2
            
            # Display the image
            self.screen.blit(self.current_image, (x_pos, y_pos))
        elif self.is_loading_image:
            # Show loading indicator
            self._update_loading_animation()
            dots = "." * self.loading_animation_state
            loading_text = f"Generating image{dots}"
            self.main_font.render_to(
                self.screen,
                (self.image_area.x + 10, self.image_area.y + self.image_area.height // 2),
                loading_text,
                Colors.TEXT_COLOR
            )
        else:
            # Show placeholder text
            self.main_font.render_to(
                self.screen,
                (self.image_area.x + 10, self.image_area.y + self.image_area.height // 2),
                "Scene image will appear here",
                Colors.GRAY
            )
    
    def update_display(self, game_state: Dict[str, Any]):
        """Update the entire display with current game state."""
        self.screen.fill(Colors.BLACK)
        
        # Draw all UI components
        self.draw_inventory(game_state.get('inventory', []))
        self.draw_text_area()
        self.draw_status_bars(
            game_state.get('health', 100),
            game_state.get('karma', 0)
        )
        self.draw_image_area()
        self.draw_input_box()
        
        pygame.display.flip()
        self.clock.tick(self.fps)
    
    def cleanup(self):
        """Clean up PyGame resources."""
        pygame.quit() 