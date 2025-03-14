import os
import requests
import pygame
import io
import time
import hashlib
from typing import Optional

class ImageGenerator:
    """Handles generation of images from scene descriptions using OpenAI's API."""
    
    def __init__(self, api_key: str, cache_dir: str = "image_cache"):
        """
        Initialize the image generator.
        
        Args:
            api_key: OpenAI API key
            cache_dir: Directory to cache generated images
        """
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.image_url = None
        self.current_prompt_hash = None
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def _hash_prompt(self, prompt: str) -> str:
        """Create a hash of the prompt to use as a cache key."""
        return hashlib.md5(prompt.encode()).hexdigest()
    
    def _get_cache_path(self, prompt_hash: str) -> str:
        """Get the path to a cached image."""
        return os.path.join(self.cache_dir, f"{prompt_hash}.png")
    
    def generate_image(self, prompt: str) -> Optional[pygame.Surface]:
        """
        Generate an image from a prompt, or retrieve from cache if available.
        
        Args:
            prompt: Text description to generate image from
            
        Returns:
            A pygame Surface containing the image, or None if generation failed
        """
        # Clean and enhance the prompt for better image generation
        enhanced_prompt = self._enhance_prompt(prompt)
        
        # Create a hash of the prompt for caching
        prompt_hash = self._hash_prompt(enhanced_prompt)
        self.current_prompt_hash = prompt_hash
        
        # Check if image is already cached
        cache_path = self._get_cache_path(prompt_hash)
        if os.path.exists(cache_path):
            try:
                return pygame.image.load(cache_path)
            except pygame.error:
                # If loading fails, continue to generate a new image
                pass
                
        # If not cached, generate new image
        try:
            # Call OpenAI API
            url = "https://api.openai.com/v1/images/generations"
            payload = {
                "model": "dall-e-3",
                "prompt": enhanced_prompt,
                "n": 1,
                "size": "1024x1024"
            }
            
            response = requests.post(url, headers=self.headers, json=payload)
            
            if response.status_code != 200:
                print(f"Error generating image: {response.text}")
                return None
                
            # Extract image URL
            data = response.json()
            image_url = data["data"][0]["url"]
            self.image_url = image_url
            
            # Download the image
            image_response = requests.get(image_url)
            if image_response.status_code != 200:
                print(f"Error downloading image: {image_response.status_code}")
                return None
                
            # Save to cache
            with open(cache_path, "wb") as f:
                f.write(image_response.content)
                
            # Convert to pygame surface
            image_data = io.BytesIO(image_response.content)
            image = pygame.image.load(image_data)
            
            return image
            
        except Exception as e:
            print(f"Error in image generation: {e}")
            return None
    
    def _enhance_prompt(self, prompt: str) -> str:
        """Enhance the prompt for better image generation."""
        # Add style guidance for consistent look
        style_guidance = "Create a vivid, detailed illustration in a fantasy game art style. Focus on dramatic lighting and rich colors."
        
        # Clean up any long or messy prompt
        if len(prompt) > 800:
            prompt = prompt[:800] + "..."
            
        # Combine the original prompt with style guidance
        enhanced = f"{prompt.strip()}. {style_guidance}"
        
        return enhanced 