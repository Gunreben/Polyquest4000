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
        self.midi_pause_threshold = 0.2  # Time in seconds to consider as a pause
        self.last_midi_value = None  # Track last MIDI value for pause detection
        
        # Debug control mode
        self.debug_mode = False
        self.target_x = None
        self.target_y = None
        self.moving_to_target = False
        self.movement_speed = 3.0  # Speed for click-to-move
        self.mouse_pos = (0, 0)  # Track mouse position for visual feedback
        self.kaoss_click_threshold = 100  # MIDI value threshold for "click"
        self.last_kaoss_click_time = 0
        self.kaoss_click_cooldown = 0.5  # Prevent accidental double clicks
        
        # Dialogue system
        self.dialogue_active = False
        self.current_dialogue = None
        self.selected_choice = 0
        self.dialogue_confirmed = False
        self.last_tap_time = 0
        self.tap_cooldown = 0.3  # Prevent accidental double taps
        self.dialogue_state = "selecting"  # Can be "selecting" or "confirming"
        
        # Mouse support for dialogue
        self.dialogue_choice_rects = []  # Store clickable areas for dialogue choices
        self.hovered_choice = -1  # Track which choice is being hovered over
        
        # Game data
        self.inventory = set()
        self.quest_flags = set()
        self.pois = []
        self.walkable_areas = []
        self.zugang_areas = []  # New: Zugang areas (class 98)
        
        # POI interaction control
        self.last_poi_visited = None  # Track which POI was last visited
        self.has_been_on_weg = True   # Track if player has been on Weg since last POI
        self.is_first_interaction = True  # Track if this is the first Polytron4000 interaction
        
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
                    
                    if obj_type == 99:  # Weg (walkable roads)
                        self.walkable_areas.append({
                            'x': x, 'y': y, 'width': width, 'height': height
                        })
                    elif obj_type == 98:  # Zugang (POI access areas)
                        self.zugang_areas.append({
                            'x': x, 'y': y, 'width': width, 'height': height
                        })
                    else:  # POIs
                        poi_name = self.poi_types.get(obj_type, name)
                        self.pois.append({
                            'name': poi_name,
                            'type': obj_type,
                            'x': x, 'y': y, 'width': width, 'height': height
                        })
            
            print(f"Loaded {len(self.pois)} POIs, {len(self.walkable_areas)} Weg areas, and {len(self.zugang_areas)} Zugang areas")
            
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
            current_time = time.time()
            time_since_last_midi = current_time - self.last_midi_time
            
            # Process all pending MIDI messages
            for msg in self.midi_port.iter_pending():
                if msg.type == 'control_change':
                    if msg.control == 12:  # X-axis control
                        self.midi_x = msg.value
                        self.last_midi_time = current_time
                        self.last_midi_value = msg.value
                    
                    elif msg.control == 13:  # Y-axis control
                        self.midi_y = msg.value
                        self.last_midi_time = current_time
                        self.last_midi_value = msg.value
                        
                        # Handle dialogue navigation using Y-axis with adjusted thresholds
                        if self.dialogue_active and time_since_last_midi > self.tap_cooldown:
                            if msg.value > 75:  # Upper half (adjusted threshold)
                                if self.dialogue_state == "selecting":
                                    self.selected_choice = 0
                                    self.dialogue_state = "confirming"
                                elif self.dialogue_state == "confirming" and self.selected_choice == 0:
                                    self.dialogue_confirmed = True
                                    self.dialogue_state = "selecting"
                                self.last_tap_time = current_time
                            
                            elif msg.value < 53:  # Lower half (adjusted threshold)
                                if self.dialogue_state == "selecting":
                                    self.selected_choice = 1
                                    self.dialogue_state = "confirming"
                                elif self.dialogue_state == "confirming" and self.selected_choice == 1:
                                    self.dialogue_confirmed = True
                                    self.dialogue_state = "selecting"
                                self.last_tap_time = current_time
                    
                    # Handle kaossilator "click" for debug mode (using control 16 or another unused control)
                    elif msg.control == 16 and self.debug_mode:  # Assuming control 16 for "click"
                        if (msg.value > self.kaoss_click_threshold and 
                            current_time - self.last_kaoss_click_time > self.kaoss_click_cooldown):
                            # Convert current MIDI position to screen coordinates
                            click_x = (self.midi_x / 127.0) * self.width
                            click_y = (self.midi_y / 127.0) * self.height
                            self.set_target_position(click_x, click_y)
                            self.last_kaoss_click_time = current_time
                            print(f"Kaoss click at ({int(click_x)}, {int(click_y)})")
            
            # Check for MIDI pause to reset dialogue state
            if self.dialogue_active and time_since_last_midi > self.midi_pause_threshold:
                self.dialogue_state = "selecting"
            
        except Exception as e:
            print(f"MIDI error: {e}")
    
    def set_target_position(self, x, y):
        """Set target position for click-to-move"""
        self.target_x = x
        self.target_y = y
        self.moving_to_target = True
        print(f"Moving to target: ({int(x)}, {int(y)})")
    
    def update_click_to_move(self):
        """Update player position when moving to target"""
        if not self.moving_to_target or self.target_x is None or self.target_y is None:
            return
        
        # Calculate distance to target
        dx = self.target_x - self.player_x
        dy = self.target_y - self.player_y
        distance = (dx * dx + dy * dy) ** 0.5
        
        # If close enough, stop moving
        if distance < 3.0:
            self.player_x = self.target_x
            self.player_y = self.target_y
            self.moving_to_target = False
            self.target_x = None
            self.target_y = None
            return
        
        # Move towards target
        move_x = (dx / distance) * self.movement_speed
        move_y = (dy / distance) * self.movement_speed
        
        self.player_x += move_x
        self.player_y += move_y
        
        # Keep player on screen
        self.player_x = max(self.player_size, min(self.width - self.player_size, self.player_x))
        self.player_y = max(self.player_size, min(self.height - self.player_size, self.player_y))
    
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
        
        # Check if player is on a Weg (class 99)
        is_on_weg = False
        for area in self.walkable_areas:
            area_rect = pygame.Rect(area['x'], area['y'], area['width'], area['height'])
            if player_rect.colliderect(area_rect):
                is_on_weg = True
                break
        
        # Update Weg status
        if is_on_weg:
            self.has_been_on_weg = True
        
        # Check POI interactions (can interact directly with POIs)
        if not self.dialogue_active:
            for poi in self.pois:
                poi_rect = pygame.Rect(poi['x'], poi['y'], poi['width'], poi['height'])
                if player_rect.colliderect(poi_rect):
                    # Allow interaction if:
                    # 1. This is a new POI, OR
                    # 2. Player has been on Weg since last visiting this POI
                    if (self.last_poi_visited != poi['name'] or self.has_been_on_weg):
                        self.start_dialogue(poi['name'])
                        self.last_poi_visited = poi['name']
                        self.has_been_on_weg = False  # Reset until player goes to Weg again
                    break
    
    def start_dialogue(self, poi_name):
        """Start dialogue with a POI"""
        if poi_name in self.dialogue_data:
            self.dialogue_active = True
            self.current_dialogue = self.dialogue_data[poi_name]['initial']
            
            # Special handling for first Polytron4000 interaction
            if poi_name == "Polytron4000" and self.is_first_interaction:
                self.current_dialogue = {
                    "text": "Welcome to the Tarmac Festival! The mighty Polytron 4000 needs the Hyperraumantrieb to activate. Your mission is to find it!",
                    "choices": [
                        {"text": "I'll help find the Hyperraumantrieb!", "action": "close"},
                        {"text": "Not interested", "action": "close"}
                    ]
                }
                self.is_first_interaction = False
            
            self.selected_choice = 0
            self.dialogue_confirmed = False
            self.dialogue_state = "selecting"
            print(f"Started dialogue with {poi_name}")
    
    def handle_dialogue_action(self, action):
        """Handle dialogue choice actions"""
        if action == "close":
            self.dialogue_active = False
            self.current_dialogue = None
            # Don't reset last_poi_visited here to maintain cooldown
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
            # Handle movement based on mode
            if self.debug_mode and self.moving_to_target:
                self.update_click_to_move()
            elif not self.debug_mode:
                # Normal MIDI movement
                self.update_player_movement()
            
            # Always check collisions
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
        self.dialogue_choice_rects = []  # Reset clickable areas
        
        if 'choices' in self.current_dialogue:
            choices = self.current_dialogue['choices']
            choice_y = box_y + box_height - 80
            
            for i, choice in enumerate(choices):
                # Calculate choice rectangle for clicking
                choice_text = f"{'>' if i == self.selected_choice else ' '} {choice['text']}"
                text_surface = self.font.render(choice_text, True, self.GREEN)
                text_width, text_height = text_surface.get_size()
                
                # Create clickable rectangle (with some padding)
                choice_rect = pygame.Rect(box_x + 15, choice_y + i * 25 - 2, 
                                        box_width - 30, text_height + 4)
                self.dialogue_choice_rects.append(choice_rect)
                
                # Determine color based on selection, confirmation state, and hover
                if i == self.hovered_choice:
                    # Mouse hover - brightest
                    color = self.BRIGHT_GREEN
                    # Draw hover background
                    pygame.draw.rect(self.screen, (0, 100, 0), choice_rect)
                elif i == self.selected_choice:
                    if self.dialogue_state == "confirming":
                        color = self.BRIGHT_GREEN
                    else:
                        color = self.GREEN
                else:
                    color = self.DIM_GREEN
                
                # Draw choice text
                choice_display_text = f"{'>' if i == self.selected_choice else ' '} {choice['text']}"
                
                # Add mouse instruction for hover
                if i == self.hovered_choice:
                    choice_display_text += " (click to select)"
                # Add MIDI instructions for non-hovered choices (only if not hovering any choice)
                elif self.hovered_choice == -1:
                    if self.dialogue_state == "selecting":
                        if i == 0:
                            choice_display_text += " (tap upper half to select)"
                        else:
                            choice_display_text += " (tap lower half to select)"
                    else:  # confirming
                        if i == self.selected_choice:
                            choice_display_text += " (tap same half to confirm)"
                
                text_surface = self.font.render(choice_display_text, True, color)
                self.screen.blit(text_surface, (box_x + 20, choice_y + i * 25))
                
                # Draw clickable area outline when hovering (debug visual)
                if i == self.hovered_choice:
                    pygame.draw.rect(self.screen, self.GREEN, choice_rect, 1)
        
        # Draw MIDI debug info for dialogue (only if not hovering with mouse)
        if self.hovered_choice == -1:
            debug_text = f"MIDI Y: {self.midi_y} | State: {self.dialogue_state} | Selected: {self.selected_choice}"
            text_surface = self.font.render(debug_text, True, self.GREEN)
            self.screen.blit(text_surface, (10, 60))
        else:
            # Show mouse interaction info instead
            debug_text = f"Mouse hover on choice {self.hovered_choice} - Click to select"
            text_surface = self.font.render(debug_text, True, self.BRIGHT_GREEN)
            self.screen.blit(text_surface, (10, 60))
    
    def draw(self):
        """Main draw function"""
        self.screen.fill(self.BLACK)
        
        # Draw walkable areas (Weg - class 99) filled with slight green
        for area in self.walkable_areas:
            pygame.draw.rect(self.screen, (0, 50, 0),  # Very dark green fill
                           (area['x'], area['y'], area['width'], area['height']))
        
        # Draw Zugang areas (class 98) in grey outline
        for area in self.zugang_areas:
            pygame.draw.rect(self.screen, self.GREY, 
                           (area['x'], area['y'], area['width'], area['height']), 1)
        
        # Draw POIs
        for poi in self.pois:
            color = self.BRIGHT_GREEN if poi['name'] == 'Polytron4000' else self.GREEN
            pygame.draw.rect(self.screen, color, 
                           (poi['x'], poi['y'], poi['width'], poi['height']), 2)
            
            # POI label centered in the rectangle
            text_surface = self.font.render(poi['name'], True, color)
            text_rect = text_surface.get_rect()
            # Center the text in the POI rectangle
            text_x = poi['x'] + (poi['width'] - text_rect.width) // 2
            text_y = poi['y'] + (poi['height'] - text_rect.height) // 2
            self.screen.blit(text_surface, (text_x, text_y))
        
        # Draw player
        pygame.draw.circle(self.screen, self.BRIGHT_GREEN, 
                         (int(self.player_x), int(self.player_y)), self.player_size)
        
        # Draw MIDI debug info in upper right corner
        debug_text = f"MIDI X: {self.midi_x} Y: {self.midi_y} | Pos: ({int(self.player_x)}, {int(self.player_y)})"
        text_surface = self.font.render(debug_text, True, self.GREEN)
        text_rect = text_surface.get_rect()
        self.screen.blit(text_surface, (self.width - text_rect.width - 10, 10))
        
        # Draw debug mode info
        if self.debug_mode:
            debug_mode_text = f"DEBUG MODE ON | Mouse: ({self.mouse_pos[0]}, {self.mouse_pos[1]})"
            if self.moving_to_target and self.target_x is not None:
                debug_mode_text += f" | Target: ({int(self.target_x)}, {int(self.target_y)})"
            text_surface = self.font.render(debug_mode_text, True, self.BRIGHT_GREEN)
            text_rect = text_surface.get_rect()
            self.screen.blit(text_surface, (10, 85))
            
            # Draw mouse cursor as a small crosshair
            mouse_x, mouse_y = self.mouse_pos
            pygame.draw.line(self.screen, self.GREEN, (mouse_x - 5, mouse_y), (mouse_x + 5, mouse_y), 1)
            pygame.draw.line(self.screen, self.GREEN, (mouse_x, mouse_y - 5), (mouse_x, mouse_y + 5), 1)
            
            # Draw target position if moving
            if self.moving_to_target and self.target_x is not None:
                target_x, target_y = int(self.target_x), int(self.target_y)
                # Draw target crosshair
                pygame.draw.line(self.screen, self.BRIGHT_GREEN, (target_x - 10, target_y), (target_x + 10, target_y), 2)
                pygame.draw.line(self.screen, self.BRIGHT_GREEN, (target_x, target_y - 10), (target_x, target_y + 10), 2)
                # Draw target circle
                pygame.draw.circle(self.screen, self.BRIGHT_GREEN, (target_x, target_y), 15, 2)
        
        # Draw POI interaction status in upper right corner
        poi_status = f"Last POI: {self.last_poi_visited} | On Weg: {self.has_been_on_weg}"
        text_surface = self.font.render(poi_status, True, self.GREEN)
        text_rect = text_surface.get_rect()
        self.screen.blit(text_surface, (self.width - text_rect.width - 10, 35))
        
        # Draw inventory in upper right corner
        if self.inventory:
            inv_text = f"Inventory: {', '.join(self.inventory)}"
            text_surface = self.font.render(inv_text, True, self.GREEN)
            text_rect = text_surface.get_rect()
            self.screen.blit(text_surface, (self.width - text_rect.width - 10, 60))
        
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
        print("🐛 Press 'D' to toggle debug mode (click-to-move)")
        print("🖱️  Mouse: Click dialogue choices to select them")
        
        while self.running:
            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_d:
                        # Toggle debug mode
                        self.debug_mode = not self.debug_mode
                        self.moving_to_target = False  # Stop any current movement
                        self.target_x = None
                        self.target_y = None
                        print(f"Debug mode: {'ON' if self.debug_mode else 'OFF'}")
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Handle mouse click
                    if event.button == 1:  # Left click
                        click_x, click_y = event.pos
                        
                        # Check if clicking on dialogue choices (works in both debug and normal mode)
                        if self.dialogue_active and self.dialogue_choice_rects:
                            for i, rect in enumerate(self.dialogue_choice_rects):
                                if rect.collidepoint(click_x, click_y):
                                    # Click on dialogue choice
                                    self.selected_choice = i
                                    self.dialogue_confirmed = True
                                    self.dialogue_state = "selecting"
                                    print(f"Clicked dialogue choice {i}")
                                    break
                        
                        # Handle map clicking in debug mode (only if not clicking dialogue)
                        elif self.debug_mode and not self.dialogue_active:
                            self.set_target_position(click_x, click_y)
                
                elif event.type == pygame.MOUSEMOTION:
                    # Always track mouse position
                    self.mouse_pos = event.pos
                    
                    # Check dialogue choice hover (works in both debug and normal mode)
                    if self.dialogue_active and self.dialogue_choice_rects:
                        mouse_x, mouse_y = event.pos
                        self.hovered_choice = -1
                        for i, rect in enumerate(self.dialogue_choice_rects):
                            if rect.collidepoint(mouse_x, mouse_y):
                                self.hovered_choice = i
                                break
            
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