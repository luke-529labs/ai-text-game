# AI Text Adventure Game

An interactive text-based RPG that uses AI to generate dynamic content and images.

## Features

- **Dynamic Storylines**: Each gameplay session creates a unique adventure
- **Real-time Image Generation**: Scenes are visualized using AI-generated images
- **Inventory System**: Find, use and lose items throughout your adventure
- **Karma & Health Tracking**: Your choices affect your character's fate
- **Random Events**: Unexpected challenges can appear at any time
- **Multiple Lives**: When you die, you reincarnate into a new adventure

## Requirements

- Python 3.8 or higher
- OpenAI API key for LLM and image generation

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/luke-529labs/ai_text_game.git
   cd ai_text_game
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up your OpenAI API key:
   ```
   export OPENAI_API_KEY='your-api-key-here'
   ```
   
   On Windows:
   ```
   set OPENAI_API_KEY=your-api-key-here
   ```

4. Create a `situations.txt` file with one situation/setting per line, for example:
   ```
   a cyberpunk city with neon lights and dark alleys
   a medieval fantasy kingdom with dragons and magic
   a post-apocalyptic wasteland with scarce resources
   ```

## Running the Game

Start the game by running:
```
python main.py
```

## How to Play

1. Enter your character name when prompted
2. Read the description of your situation
3. Type your actions in the input box
4. Make choices that affect your karma and health
5. Manage your inventory by finding and using items
6. Try to survive as long as possible!

## Game Controls

- **Type** your actions in the input box
- Press **Enter** to submit
- Click anywhere else to unfocus from the input box
- Close the window to exit the game

## Image Generation

The game automatically generates images for each scene using OpenAI's DALL-E API. If you don't have an API key or don't want to use this feature, the game will still run but without images.

## Troubleshooting

- **No images appear**: Make sure your OpenAI API key is set correctly and has permission for image generation
- **Game crashes**: Check that all dependencies are installed correctly
- **Text too small/large**: Adjust your display settings or modify the font sizes in `game_ui.py`

## License

This project is open source and available under the MIT License.

## Credits

- Uses OpenAI's language models and DALL-E for content generation
- Built with Pygame for the graphical interface 