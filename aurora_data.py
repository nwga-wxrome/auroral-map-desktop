import numpy as np
import requests
from PIL import Image
from OpenGL.GL import *
import math

class AuroraData:
    def __init__(self):
        self.texture = None
        self.last_update = None
        self.intensity_scale = 150  # Increased for better visibility
        self.color_key_texture = None

    def fetch_data(self):
        try:
            url = "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json"
            response = requests.get(url)
            data = response.json()
            
            # Higher resolution for better visualization
            width, height = 720, 360
            aurora_map = np.zeros((height, width, 4), dtype=np.uint8)
            
            if 'coordinates' in data:
                for point in data['coordinates']:
                    lat = int((point[1] + 90) * height/180)
                    lon = int((point[0] + 180) * width/360)
                    
                    if isinstance(point[2], (int, float)):
                        intensity = min(255, int(point[2] * self.intensity_scale))
                        
                        radius = 5  # Reduced for less blur
                        for dy in range(-radius, radius + 1):
                            for dx in range(-radius, radius + 1):
                                new_lat = lat + dy
                                new_lon = (lon + dx) % width
                                
                                if 0 <= new_lat < height:
                                    dist = math.sqrt(dx*dx + dy*dy)
                                    if dist <= radius:
                                        # Sharper falloff
                                        fade = math.pow((radius - dist) / radius, 2.0)
                                        current_intensity = int(intensity * fade)
                                        
                                        # Color gradient from light to strong green
                                        green_base = min(255, int(180 + (current_intensity * 0.3)))
                                        green_value = min(255, green_base)
                                        
                                        # Add some blue for more vibrant appearance
                                        blue_value = min(100, int(current_intensity * 0.2))
                                        
                                        # Combine into final color
                                        if current_intensity > aurora_map[new_lat, new_lon][3]:
                                            aurora_map[new_lat, new_lon] = [0, green_value, blue_value, current_intensity]

            return aurora_map
        except Exception as e:
            print(f"Error fetching aurora data: {e}")
            return None

    def create_texture(self, aurora_map):
        if (aurora_map is None):
            return None

        try:
            image = Image.fromarray(aurora_map)
            image = image.transpose(Image.FLIP_TOP_BOTTOM)
            img_data = np.array(image).tobytes()
            
            texture = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture)
            
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 
                        image.width, image.height, 0, 
                        GL_RGBA, GL_UNSIGNED_BYTE, 
                        img_data)
            
            return texture
        except Exception as e:
            print(f"Error creating aurora texture: {e}")
            return None

    def create_color_key(self):
        """Create a color key texture showing intensity scale"""
        width, height = 256, 32
        color_key = np.zeros((height, width, 4), dtype=np.uint8)
        
        for x in range(width):
            intensity = int((x / width) * 255)
            green_base = min(255, int(180 + (intensity * 0.3)))
            blue_value = min(100, int(intensity * 0.2))
            
            for y in range(height):
                color_key[y, x] = [0, green_base, blue_value, intensity]

        try:
            image = Image.fromarray(color_key)
            img_data = np.array(image).tobytes()
            
            texture = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture)
            
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 
                        width, height, 0, 
                        GL_RGBA, GL_UNSIGNED_BYTE, 
                        img_data)
            
            self.color_key_texture = texture
            return texture
        except Exception as e:
            print(f"Error creating color key texture: {e}")
            return None
