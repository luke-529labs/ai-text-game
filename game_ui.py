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
    TRANSLUCENT_BLACK = (0, 0, 0, 180)  # For overlays
    TRANSLUCENT_DARK = (20, 20, 20, 200)  # For overlays

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
        self.small_font = pygame.freetype.SysFont('Arial', 14)
        
        # UI element dimensions
        self.padding = 10
        self.input_height = 40
        self.title_height = 40  # Height reserved for scene title
        
        # New layout with larger image and text areas
        # Image area now takes up right half of screen, with space for title
        self.image_area = pygame.Rect(
            self.width // 2 + self.padding,
            self.padding + self.title_height,  # Move down by title height
            (self.width // 2) - (self.padding * 2),
            self.height - self.input_height - (self.padding * 3) - self.title_height  # Adjust height
        )
        
        # Title area above image
        self.title_area = pygame.Rect(
            self.width // 2 + self.padding,
            self.padding,
            (self.width // 2) - (self.padding * 2),
            self.title_height
        )
        
        # Small inventory in top-left corner
        inventory_height = 150
        self.inventory_area = pygame.Rect(
            self.padding,
            self.padding,
            (self.width // 2) - (self.padding * 2),
            inventory_height
        )
        
        # Text area takes remaining left side space
        self.text_area = pygame.Rect(
            self.padding,
            self.inventory_area.bottom + self.padding,
            (self.width // 2) - (self.padding * 2),
            self.height - self.inventory_area.height - self.input_height - (self.padding * 4)
        )
        
        # Scroll buttons for text area
        button_size = 30
        self.scroll_up_button = pygame.Rect(
            self.text_area.right - button_size - 5,
            self.text_area.top + 5,
            button_size,
            button_size
        )
        
        self.scroll_down_button = pygame.Rect(
            self.text_area.right - button_size - 5,
            self.text_area.bottom - button_size - 5,
            button_size,
            button_size
        )
        
        # Scrollbar track between buttons
        scrollbar_width = 6  # Thinner scrollbar
        self.scrollbar_track = pygame.Rect(
            self.text_area.right - scrollbar_width - 10,  # Move it a bit more to the right
            self.scroll_up_button.bottom + 5,
            scrollbar_width,
            self.scroll_down_button.top - self.scroll_up_button.bottom - 10
        )
        
        # Input box at bottom spans full width
        self.input_box = pygame.Rect(
            self.padding,
            self.height - self.input_height - self.padding,
            self.width - (self.padding * 2),
            self.input_height
        )
        
        # Scrolling variables for text area
        self.scroll_position = 0
        self.max_scroll_position = 0
        self.always_show_latest = True  # Flag to control auto-scrolling
        
        self.input_text = ""
        self.input_active = False
        
        # Message history with type info
        self.messages: List[Message] = []
        self.max_messages = 200  # Increased from 50 to allow for more history
        
        # Image loading state
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
            
            # Check if scroll buttons were clicked
            if self.scroll_up_button.collidepoint(event.pos):
                # Scroll up button should increase scroll_position (show older messages)
                self.scroll_position = min(self.max_scroll_position, self.scroll_position + 5)
                self.always_show_latest = False  # User manually scrolled
            elif self.scroll_down_button.collidepoint(event.pos):
                # Scroll down button should decrease scroll_position (show newer messages)
                self.scroll_position = max(0, self.scroll_position - 5)
                # If scrolled to bottom, re-enable auto-scrolling
                if self.scroll_position <= 0:
                    self.always_show_latest = True
            
            # Handle mouse wheel scrolling for text area
            elif self.text_area.collidepoint(event.pos):
                if event.button == 4:  # Scroll up
                    self.scroll_position = max(0, self.scroll_position - 3)
                    self.always_show_latest = False  # User manually scrolled
                elif event.button == 5:  # Scroll down
                    self.scroll_position = min(self.max_scroll_position, self.scroll_position + 3)
                    # If scrolled to bottom, re-enable auto-scrolling
                    if self.scroll_position >= self.max_scroll_position:
                        self.always_show_latest = True
                
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
            
            # Keyboard scrolling for text area
            if event.key == pygame.K_PAGEUP:
                self.scroll_position = max(0, self.scroll_position - 10)
                self.always_show_latest = False
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll_position = min(self.max_scroll_position, self.scroll_position + 10)
                if self.scroll_position >= self.max_scroll_position:
                    self.always_show_latest = True
            elif event.key == pygame.K_HOME:
                self.scroll_position = 0
                self.always_show_latest = False
            elif event.key == pygame.K_END:
                self.scroll_position = self.max_scroll_position
                self.always_show_latest = True
        
        return None
    
    def add_system_message(self, message: str):
        """Add a system message to the display history."""
        # Handle loading messages specially - but don't set flags directly
        # (let the main game loop handle the state)
        if message == "Generating scene image...":
            # The flag is now set by the main game before calling this method
            pass
        elif message == "Scene image updated." or message == "Failed to generate scene image.":
            # The flag is now cleared by the image generation thread
            pass
            
        # Wrap text to fit the screen
        wrapped_text = textwrap.fill(message, width=60)  # Adjusted for new width
        for line in wrapped_text.split('\n'):
            self.messages.append(Message(line, MessageType.SYSTEM))
        
        # Keep only the last max_messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
        
        # Update scroll position if auto-scrolling is enabled
        self._calculate_max_scroll_position()
        # Always default to showing newest content (bottom of text)
        self.scroll_position = 0
    
    def add_player_message(self, message: str):
        """Add a player message to the display history."""
        # Format with player name
        formatted = f"You: {message}"
        
        # Wrap text to fit the screen
        wrapped_text = textwrap.fill(formatted, width=60)  # Adjusted for new width
        for line in wrapped_text.split('\n'):
            self.messages.append(Message(line, MessageType.PLAYER))
        
        # Keep only the last max_messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
        
        # Update scroll position if auto-scrolling is enabled
        self._calculate_max_scroll_position()
        # Always default to showing newest content (bottom of text)
        self.scroll_position = 0
    
    def add_gamemaster_message(self, message: str):
        """Add a gamemaster message to the display history."""
        # Format as gamemaster
        formatted = f"Gamemaster: {message}"
        
        # Wrap text to fit the screen
        wrapped_text = textwrap.fill(formatted, width=60)  # Adjusted for new width
        for line in wrapped_text.split('\n'):
            self.messages.append(Message(line, MessageType.GAMEMASTER))
        
        # Keep only the last max_messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
        
        # Update scroll position if auto-scrolling is enabled
        self._calculate_max_scroll_position()
        # Always default to showing newest content (bottom of text)
        self.scroll_position = 0
    
    def add_message(self, message: str):
        """Legacy method - adds a system message for backward compatibility."""
        self.add_system_message(message)
    
    def _calculate_max_scroll_position(self):
        """Calculate the maximum scroll position based on message count."""
        line_height = 25
        total_message_height = len(self.messages) * line_height
        visible_height = self.text_area.height - 20
        
        if total_message_height > visible_height:
            self.max_scroll_position = (total_message_height - visible_height) // line_height
        else:
            self.max_scroll_position = 0
    
    def draw_status_bars(self, health: int, karma: int):
        """Draw health and karma bars overlaid on image area."""
        # Create a translucent background for the status bars
        status_surface = pygame.Surface((200, 75), pygame.SRCALPHA)  # Increased height
        status_surface.fill((0, 0, 0, 180))  # Translucent black
        
        # Position in top-right corner of image area
        status_x = self.image_area.right - 210
        status_y = self.image_area.top + 10
        
        # Draw health bar
        bar_width = 180
        bar_height = 15
        bar_x = 10
        bar_y = 5
        
        pygame.draw.rect(status_surface, Colors.DARK_GRAY, (bar_x, bar_y, bar_width, bar_height))
        health_width = (bar_width * health) // 100
        pygame.draw.rect(status_surface, Colors.HEALTH_BAR, (bar_x, bar_y, health_width, bar_height))
        
        health_text = f"Health: {health}"
        self.small_font.render_to(status_surface, (bar_x, bar_y + bar_height + 2), health_text, Colors.TEXT_COLOR)
        
        # Karma bar - moved down for more space
        bar_y += bar_height + 25  # Increased spacing
        pygame.draw.rect(status_surface, Colors.DARK_GRAY, (bar_x, bar_y, bar_width, bar_height))
        
        # Calculate karma position and color
        mid_point = bar_x + (bar_width // 2)
        if karma >= 0:
            karma_width = (bar_width // 2) * karma // 100
            karma_color = Colors.KARMA_BAR_POSITIVE
            karma_x = mid_point
        else:
            karma_width = (bar_width // 2) * abs(karma) // 100
            karma_color = Colors.KARMA_BAR_NEGATIVE
            karma_x = mid_point - karma_width
        
        # Draw the karma bar
        pygame.draw.rect(status_surface, karma_color, (karma_x, bar_y, karma_width, bar_height))
        
        # Draw center line and markers
        pygame.draw.line(status_surface, Colors.WHITE, (mid_point, bar_y), (mid_point, bar_y + bar_height), 1)
        
        # Draw karma value
        karma_text = f"Karma: {karma}"
        self.small_font.render_to(status_surface, (bar_x, bar_y + bar_height + 2), karma_text, Colors.TEXT_COLOR)
        
        # Blit the status surface onto the main screen
        self.screen.blit(status_surface, (status_x, status_y))
    
    def draw_inventory(self, inventory: List[str]):
        """Draw a smaller inventory panel."""
        pygame.draw.rect(self.screen, Colors.DARKER_GRAY, self.inventory_area)
        
        # Draw header with background
        header_rect = pygame.Rect(
            self.inventory_area.x,
            self.inventory_area.y,
            self.inventory_area.width,
            30
        )
        pygame.draw.rect(self.screen, Colors.DARK_GRAY, header_rect)
        
        self.header_font.render_to(
            self.screen,
            (self.inventory_area.x + 10, self.inventory_area.y + 5),
            "INVENTORY",
            Colors.TEXT_COLOR
        )
        
        # Draw items in a more compact format
        y = self.inventory_area.y + 40
        if not inventory:
            self.main_font.render_to(
                self.screen,
                (self.inventory_area.x + 20, y),
                "Empty",
                Colors.GRAY
            )
        else:
            # Draw items in a grid-like layout if there are many
            item_width = 180
            items_per_row = max(1, self.inventory_area.width // item_width)
            
            for i, item in enumerate(inventory):
                col = i % items_per_row
                row = i // items_per_row
                
                x = self.inventory_area.x + 10 + (col * item_width)
                item_y = y + (row * 25)
                
                if item_y < self.inventory_area.bottom - 15:  # Ensure it's visible
                    self.main_font.render_to(
                        self.screen,
                        (x, item_y),
                        f"• {item}",
                        Colors.TEXT_COLOR
                    )
    
    def draw_text_area(self):
        """Draw the scrollable text area with message history."""
        pygame.draw.rect(self.screen, Colors.DARKER_GRAY, self.text_area)
        
        # Draw messages with scrolling
        line_height = 25
        visible_lines = (self.text_area.height - 20) // line_height
        
        # Calculate which messages to display based on scroll position
        start_idx = max(0, len(self.messages) - visible_lines - self.scroll_position)
        end_idx = min(len(self.messages), start_idx + visible_lines)
        
        visible_messages = self.messages[start_idx:end_idx]
        
        # Draw scroll indicators if needed
        if self.scroll_position > 0:
            # Draw "more above" indicator
            pygame.draw.polygon(
                self.screen, 
                Colors.LIGHT_GRAY,
                [
                    (self.text_area.right - 20, self.text_area.top + 10),
                    (self.text_area.right - 10, self.text_area.top + 20),
                    (self.text_area.right - 30, self.text_area.top + 20)
                ]
            )
        
        if self.scroll_position < self.max_scroll_position:
            # Draw "more below" indicator
            pygame.draw.polygon(
                self.screen, 
                Colors.LIGHT_GRAY,
                [
                    (self.text_area.right - 20, self.text_area.bottom - 10),
                    (self.text_area.right - 10, self.text_area.bottom - 20),
                    (self.text_area.right - 30, self.text_area.bottom - 20)
                ]
            )
        
        # Draw scrollbar track
        pygame.draw.rect(self.screen, Colors.DARK_GRAY, self.scrollbar_track)
        
        # Draw scrollbar position indicator (thumb)
        if self.max_scroll_position > 0:
            # Calculate thumb position and size
            scrollbar_height = self.scrollbar_track.height
            # Make the thumb a bit smaller but still visible
            thumb_height = max(30, min(100, scrollbar_height * visible_lines / len(self.messages)))
            
            # Position is based on current scroll position - FIXED direction
            # When scroll_position is 0, thumb should be at the bottom (newest messages)
            # When scroll_position is max, thumb should be at the top (oldest messages)
            # So we invert the ratio: (1 - scroll_ratio)
            scroll_ratio = self.scroll_position / self.max_scroll_position if self.max_scroll_position > 0 else 0
            inverted_ratio = 1.0 - scroll_ratio
            thumb_pos = self.scrollbar_track.top + (scrollbar_height - thumb_height) * inverted_ratio
            
            thumb_rect = pygame.Rect(
                self.scrollbar_track.x,
                thumb_pos,
                self.scrollbar_track.width,
                thumb_height
            )
            
            # Draw a more elegant scrollbar
            # First draw a slightly larger rect with the same color as background for rounded effect
            pygame.draw.rect(self.screen, Colors.DARKER_GRAY, 
                            (thumb_rect.x - 1, thumb_rect.y - 1, 
                             thumb_rect.width + 2, thumb_rect.height + 2), 
                            border_radius=3)
            
            # Then draw the actual scrollbar with a softer color
            scrollbar_color = Colors.LIGHT_GRAY if self.always_show_latest else (180, 180, 220)  # Light blue-gray when manually scrolling
            pygame.draw.rect(self.screen, scrollbar_color, thumb_rect, border_radius=3)
        
        # Draw scroll buttons
        # Up button
        pygame.draw.rect(self.screen, Colors.DARK_GRAY, self.scroll_up_button)
        pygame.draw.polygon(
            self.screen,
            Colors.WHITE,
            [
                (self.scroll_up_button.centerx, self.scroll_up_button.top + 5),
                (self.scroll_up_button.left + 5, self.scroll_up_button.bottom - 5),
                (self.scroll_up_button.right - 5, self.scroll_up_button.bottom - 5)
            ]
        )
        
        # Down button
        pygame.draw.rect(self.screen, Colors.DARK_GRAY, self.scroll_down_button)
        pygame.draw.polygon(
            self.screen,
            Colors.WHITE,
            [
                (self.scroll_down_button.centerx, self.scroll_down_button.bottom - 5),
                (self.scroll_down_button.left + 5, self.scroll_down_button.top + 5),
                (self.scroll_down_button.right - 5, self.scroll_down_button.top + 5)
            ]
        )
        
        # Draw messages
        y = self.text_area.y + 10
        for message in visible_messages:
            self.main_font.render_to(
                self.screen,
                (self.text_area.x + 10, y),
                message.text,
                message.color
            )
            y += line_height
    
    def draw_input_box(self):
        """Draw the input box."""
        # Draw label
        self.main_font.render_to(
            self.screen, 
            (self.padding, self.height - self.input_height - self.padding - 20),
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
        """Draw the larger image area and current image if available."""
        # Draw the background and border for both title and image areas
        border_rect = pygame.Rect(
            self.image_area.x - 2,
            self.title_area.y - 2,  # Start from title area
            self.image_area.width + 4,
            self.image_area.height + self.title_height + 4  # Include title height
        )
        pygame.draw.rect(self.screen, Colors.LIGHT_GRAY, border_rect)
        
        # Draw title area background
        pygame.draw.rect(self.screen, Colors.DARK_GRAY, self.title_area)
        
        # Draw image area background
        pygame.draw.rect(self.screen, Colors.DARKER_GRAY, self.image_area)
        
        # Draw scene title in title area
        self.header_font.render_to(
            self.screen,
            (self.title_area.x + 10, self.title_area.y + (self.title_height - 24) // 2),  # Center vertically
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
                (self.image_area.x + (self.image_area.width - 150) // 2, 
                 self.image_area.y + self.image_area.height // 2),
                loading_text,
                Colors.TEXT_COLOR
            )
        else:
            # Show placeholder text
            self.main_font.render_to(
                self.screen,
                (self.image_area.x + (self.image_area.width - 250) // 2, 
                 self.image_area.y + self.image_area.height // 2),
                "Scene image will appear here",
                Colors.GRAY
            )
    
    def update_display(self, game_state: Dict[str, Any]):
        """Update the entire display with current game state."""
        self.screen.fill(Colors.BLACK)
        
        # Draw all UI components in the new layout
        self.draw_image_area()
        self.draw_inventory(game_state.get('inventory', []))
        self.draw_text_area()
        self.draw_input_box()
        
        # Draw status bars on top of image
        self.draw_status_bars(
            game_state.get('health', 100),
            game_state.get('karma', 0)
        )
        
        pygame.display.flip()
        self.clock.tick(self.fps)
    
    def cleanup(self):
        """Clean up PyGame resources."""
        pygame.quit() 