import pygame
import mido
import sys
import time
import json
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime

class TarmacGame:
    def __init__(self):
        pygame.init()
        
        # Screen setup - CRT terminal feel
        self.width = 1024
        self.height = 768
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Tarmac Festival - Polytron 4000")
        
        # Colors - Green on black CRT aesthetic
        self.BLACK = (0, 0, 0)
        self.GREEN = (0, 255, 0)
        self.BRIGHT_GREEN = (100, 255, 100)
        self.DIM_GREEN = (0, 150, 0)
        self.GREY = (128, 128, 128)
        self.RED = (255, 0, 0)
        
        # Font
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 36)
        
        # Game state
        self.running = True
        self.clock = pygame.time.Clock()
        
        # Player
        self.player_x = 100.0
        self.player_y = 100.0
        self.player_size = 8
        self.player_speed = 2.0
        
        # MIDI controls - smooth movement
        self.midi_x = 64  # Center position (0-127)
        self.midi_y = 64  # Center position (0-127)
        self.last_midi_time = time.time()
        
        # Dialogue system
        self.dialogue_active = False
        self.current_dialogue = None
        self.selected_choice = 0
        self.dialogue_confirmed = False
        self.last_tap_time = 0
        self.tap_cooldown = 0.3  # Prevent accidental double taps
        
        # Game data
        self.inventory = set()
        self.quest_flags = set()
        self.pois = []
        self.walkable_areas = []
        
        # POI type mapping - updated for new map
        self.poi_types = {
            0: "Polytron4000",    # Main goal
            1: "Brausecus",       # Drinks
            2: "Resonant",        # Music/Sound
            3: "Vacanza",         # Relaxation
            4: "Looserlounge",    # Social
            5: "L300",            # Tech/Equipment
            6: "Orgia",           # Party
            7: "Lila Drache",     # Mystery
            8: "Nest",            # Cozy space
            9: "Workshopspace",   # Learning
            10: "2. Reihe"        # Seating/Viewing
        }
        
        # Load game data
        self.load_map()
        self.load_dialogue()
        
        # MIDI setup
        self.setup_midi()
        
    def setup_midi(self):
        """Setup MIDI input"""
        try:
            available_ports = mido.get_input_names()
            print(f"Available MIDI ports: {available_ports}")
            
            # Try to find Kaossilator Pro or any available port
            self.midi_port = None
            for port_name in available_ports:
                if 'kaoss' in port_name.lower() or 'pro' in port_name.lower():
                    self.midi_port = mido.open_input(port_name)
                    print(f"Connected to: {port_name}")
                    break
            
            if not self.midi_port and available_ports:
                self.midi_port = mido.open_input(available_ports[0])
                print(f"Connected to: {available_ports[0]}")
                
        except Exception as e:
            print(f"MIDI setup failed: {e}")
            self.midi_port = None
    
    def load_map(self):
        """Load TMX map file"""
        try:
            tree = ET.parse('assets/map.tmx')
            root = tree.getroot()
            
            # Find object layer
            for layer in root.findall('objectgroup'):
                for obj in layer.findall('object'):
                    obj_type = int(obj.get('type', 0))
                    name = obj.get('name', '')
                    x = float(obj.get('x', 0))
                    y = float(obj.get('y', 0))
                    width = float(obj.get('width', 0))
                    height = float(obj.get('height', 0))
                    
                    if obj_type == 99:  # Walkable areas
                        self.walkable_areas.append({
                            'x': x, 'y': y, 'width': width, 'height': height
                        })
                    else:  # POIs
                        poi_name = self.poi_types.get(obj_type, name)
                        self.pois.append({
                            'name': poi_name,
                            'type': obj_type,
                            'x': x, 'y': y, 'width': width, 'height': height
                        })
            
            print(f"Loaded {len(self.pois)} POIs and {len(self.walkable_areas)} walkable areas")
            
        except Exception as e:
            print(f"Failed to load map: {e}")
            # Create fallback POIs
            self.pois = [
                {'name': 'Polytron4000', 'type': 0, 'x': 45, 'y': 91, 'width': 85, 'height': 70}
            ]
    
    def load_dialogue(self):
        """Load dialogue data"""
        try:
            with open('assets/dialogue.json', 'r') as f:
                self.dialogue_data = json.load(f)
        except Exception as e:
            print(f"Failed to load dialogue: {e}")
            # Fallback dialogue
            self.dialogue_data = {
                "Polytron4000": {
                    "initial": {
                        "text": "The mighty Polytron 4000 awaits activation!",
                        "choices": [
                            {"text": "Activate", "action": "win_game"},
                            {"text": "Not ready", "action": "close"}
                        ]
                    }
                }
            }
    
    def handle_midi(self):
        """Handle MIDI input for smooth movement and dialogue"""
        if not self.midi_port:
            return
            
        try:
            # Process all pending MIDI messages
            for msg in self.midi_port.iter_pending():
                if msg.type == 'control_change':
                    current_time = time.time()
                    
                    if msg.control == 12:  # X-axis control
                        self.midi_x = msg.value
                        self.last_midi_time = current_time
                        
                        # Handle dialogue navigation
                        if self.dialogue_active and current_time - self.last_tap_time > self.tap_cooldown:
                            if msg.value > 100:  # Upper half tap
                                if self.selected_choice == 1:  # Switch to upper choice
                                    self.selected_choice = 0
                                elif self.selected_choice == 0:  # Confirm upper choice
                                    self.dialogue_confirmed = True
                                self.last_tap_time = current_time
                            elif msg.value < 27:  # Lower half tap
                                if self.selected_choice == 0:  # Switch to lower choice
                                    self.selected_choice = 1
                                elif self.selected_choice == 1:  # Confirm lower choice
                                    self.dialogue_confirmed = True
                                self.last_tap_time = current_time
                    
                    elif msg.control == 13:  # Y-axis control
                        self.midi_y = msg.value
                        self.last_midi_time = current_time
                        
        except Exception as e:
            print(f"MIDI error: {e}")
    
    def update_player_movement(self):
        """Update player position based on MIDI input with smooth movement"""
        if time.time() - self.last_midi_time < 0.1:  # Recent MIDI input
            # Convert MIDI values to movement
            # MIDI: 0-127, where 127/127 should be upper-left
            # Invert Y so 127 = up, 0 = down
            # Keep X normal so 127 = right, 0 = left
            
            # Calculate movement direction from center (64)
            center = 64
            deadzone = 10
            
            # X movement: 0=left, 127=right
            if abs(self.midi_x - center) > deadzone:
                x_factor = (self.midi_x - center) / center
                self.player_x += x_factor * self.player_speed
            
            # Y movement: 127=up, 0=down (inverted from MIDI)
            if abs(self.midi_y - center) > deadzone:
                y_factor = -(self.midi_y - center) / center  # Negative to invert
                self.player_y += y_factor * self.player_speed
            
            # Keep player on screen
            self.player_x = max(self.player_size, min(self.width - self.player_size, self.player_x))
            self.player_y = max(self.player_size, min(self.height - self.player_size, self.player_y))
    
    def check_collisions(self):
        """Check if player is on walkable area and near POIs"""
        player_rect = pygame.Rect(self.player_x - self.player_size//2, 
                                 self.player_y - self.player_size//2,
                                 self.player_size, self.player_size)
        
        # Check POI interactions
        for poi in self.pois:
            poi_rect = pygame.Rect(poi['x'], poi['y'], poi['width'], poi['height'])
            if player_rect.colliderect(poi_rect) and not self.dialogue_active:
                self.start_dialogue(poi['name'])
                break
    
    def start_dialogue(self, poi_name):
        """Start dialogue with a POI"""
        if poi_name in self.dialogue_data:
            self.dialogue_active = True
            self.current_dialogue = self.dialogue_data[poi_name]['initial']
            self.selected_choice = 0
            self.dialogue_confirmed = False
            print(f"Started dialogue with {poi_name}")
    
    def handle_dialogue_action(self, action):
        """Handle dialogue choice actions"""
        if action == "close":
            self.dialogue_active = False
            self.current_dialogue = None
        elif action == "win_game":
            print("🎉 GAME WON! Polytron 4000 activated!")
            self.dialogue_active = False
        elif action.startswith("give_"):
            item = action.replace("give_", "")
            self.inventory.add(item)
            print(f"Received: {item}")
            self.dialogue_active = False
        elif action.startswith("flag_"):
            flag = action.replace("flag_", "")
            self.quest_flags.add(flag)
            print(f"Quest flag set: {flag}")
            self.dialogue_active = False
    
    def update(self):
        """Main game update loop"""
        self.handle_midi()
        
        if self.dialogue_active:
            # Handle dialogue confirmation
            if self.dialogue_confirmed:
                if self.current_dialogue and 'choices' in self.current_dialogue:
                    choices = self.current_dialogue['choices']
                    if self.selected_choice < len(choices):
                        choice = choices[self.selected_choice]
                        
                        # Check conditions
                        if 'condition' in choice:
                            condition = choice['condition']
                            if condition.startswith('has') and condition.replace('has', '').lower() not in self.inventory:
                                print(f"You need: {condition.replace('has', '')}")
                                self.dialogue_active = False
                                return
                        
                        # Execute action
                        if 'action' in choice:
                            self.handle_dialogue_action(choice['action'])
                
                self.dialogue_confirmed = False
        else:
            # Normal movement
            self.update_player_movement()
            self.check_collisions()
    
    def draw_dialogue(self):
        """Draw dialogue interface"""
        if not self.dialogue_active or not self.current_dialogue:
            return
        
        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(128)
        overlay.fill(self.BLACK)
        self.screen.blit(overlay, (0, 0))
        
        # Dialogue box
        box_width = 600
        box_height = 200
        box_x = (self.width - box_width) // 2
        box_y = (self.height - box_height) // 2
        
        pygame.draw.rect(self.screen, self.BLACK, (box_x, box_y, box_width, box_height))
        pygame.draw.rect(self.screen, self.GREEN, (box_x, box_y, box_width, box_height), 2)
        
        # Dialogue text
        text = self.current_dialogue.get('text', '')
        y_offset = box_y + 20
        
        # Word wrap
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if self.font.size(test_line)[0] < box_width - 40:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        for line in lines:
            text_surface = self.font.render(line, True, self.GREEN)
            self.screen.blit(text_surface, (box_x + 20, y_offset))
            y_offset += 25
        
        # Choices
        if 'choices' in self.current_dialogue:
            choices = self.current_dialogue['choices']
            choice_y = box_y + box_height - 80
            
            for i, choice in enumerate(choices):
                color = self.BRIGHT_GREEN if i == self.selected_choice else self.DIM_GREEN
                choice_text = f"{'>' if i == self.selected_choice else ' '} {choice['text']}"
                
                # Show tap instruction
                if i == 0:
                    choice_text += " (tap upper half)"
                else:
                    choice_text += " (tap lower half)"
                
                text_surface = self.font.render(choice_text, True, color)
                self.screen.blit(text_surface, (box_x + 20, choice_y + i * 25))
    
    def draw(self):
        """Main draw function"""
        self.screen.fill(self.BLACK)
        
        # Draw walkable areas (debug)
        for area in self.walkable_areas:
            pygame.draw.rect(self.screen, self.DIM_GREEN, 
                           (area['x'], area['y'], area['width'], area['height']), 1)
        
        # Draw POIs
        for poi in self.pois:
            color = self.BRIGHT_GREEN if poi['name'] == 'Polytron4000' else self.GREEN
            pygame.draw.rect(self.screen, color, 
                           (poi['x'], poi['y'], poi['width'], poi['height']), 2)
            
            # POI label
            text_surface = self.font.render(poi['name'], True, color)
            self.screen.blit(text_surface, (poi['x'], poi['y'] - 20))
        
        # Draw player
        pygame.draw.circle(self.screen, self.BRIGHT_GREEN, 
                         (int(self.player_x), int(self.player_y)), self.player_size)
        
        # Draw MIDI debug info
        debug_text = f"MIDI X: {self.midi_x} Y: {self.midi_y} | Pos: ({int(self.player_x)}, {int(self.player_y)})"
        text_surface = self.font.render(debug_text, True, self.GREEN)
        self.screen.blit(text_surface, (10, 10))
        
        # Draw inventory
        if self.inventory:
            inv_text = f"Inventory: {', '.join(self.inventory)}"
            text_surface = self.font.render(inv_text, True, self.GREEN)
            self.screen.blit(text_surface, (10, 35))
        
        # Draw dialogue
        self.draw_dialogue()
        
        # Draw title
        title_surface = self.title_font.render("TARMAC FESTIVAL - POLYTRON 4000", True, self.BRIGHT_GREEN)
        title_rect = title_surface.get_rect(center=(self.width//2, 30))
        self.screen.blit(title_surface, title_rect)
        
        pygame.display.flip()
    
    def run(self):
        """Main game loop"""
        print("🎮 Tarmac Festival Game Started!")
        print("📱 Use your Kaossilator Pro touchpad to move")
        print("🎯 Find and activate the Polytron 4000!")
        
        while self.running:
            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
            
            self.update()
            self.draw()
            self.clock.tick(60)  # 60 FPS
        
        # Cleanup
        if self.midi_port:
            self.midi_port.close()
        pygame.quit()

if __name__ == "__main__":
    game = TarmacGame()
    game.run()