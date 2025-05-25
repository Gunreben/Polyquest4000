import pygame
import mido
import sys
import time
import threading
from collections import defaultdict
from datetime import datetime

class MIDIVisualizer:
    def __init__(self):
        pygame.init()
        
        # Screen setup
        self.width = 1200
        self.height = 800
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Kaossilator Pro MIDI Visualizer")
        
        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GREEN = (0, 255, 0)
        self.RED = (255, 0, 0)
        self.BLUE = (0, 0, 255)
        self.YELLOW = (255, 255, 0)
        self.PURPLE = (255, 0, 255)
        self.CYAN = (0, 255, 255)
        self.ORANGE = (255, 165, 0)
        
        # Channel colors (16 MIDI channels)
        self.channel_colors = [
            self.RED, self.GREEN, self.BLUE, self.YELLOW,
            self.PURPLE, self.CYAN, self.ORANGE, (255, 100, 100),
            (100, 255, 100), (100, 100, 255), (255, 255, 100),
            (255, 100, 255), (100, 255, 255), (200, 200, 200),
            (150, 75, 0), (75, 150, 0)
        ]
        
        # Font
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 36)
        
        # MIDI data
        self.channel_activity = defaultdict(list)  # Store recent activity per channel
        self.note_velocities = defaultdict(int)    # Current note velocities
        self.cc_values = defaultdict(dict)         # Control change values per channel
        self.message_count = 0
        self.last_message_time = None
        
        # MIDI input
        self.midi_input = None
        self.running = True
        
    def list_midi_devices(self):
        """List available MIDI input devices"""
        print("Available MIDI input devices:")
        input_names = mido.get_input_names()
        
        if not input_names:
            print("No MIDI input devices found!")
            return None
            
        for i, name in enumerate(input_names):
            print(f"{i}: {name}")
        
        return input_names
    
    def connect_midi(self, device_name=None):
        """Connect to MIDI device"""
        try:
            if device_name:
                self.midi_input = mido.open_input(device_name)
                print(f"Connected to: {device_name}")
            else:
                # Try to find Kaossilator or use first available device
                input_names = mido.get_input_names()
                kaossilator_device = None
                
                for name in input_names:
                    if 'kaossilator' in name.lower() or 'korg' in name.lower():
                        kaossilator_device = name
                        break
                
                if kaossilator_device:
                    self.midi_input = mido.open_input(kaossilator_device)
                    print(f"Auto-detected and connected to: {kaossilator_device}")
                elif input_names:
                    self.midi_input = mido.open_input(input_names[0])
                    print(f"Connected to first available device: {input_names[0]}")
                else:
                    print("No MIDI devices available!")
                    return False
                    
            return True
        except Exception as e:
            print(f"Error connecting to MIDI device: {e}")
            return False
    
    def midi_callback(self):
        """Handle incoming MIDI messages"""
        if not self.midi_input:
            return
            
        try:
            for message in self.midi_input.iter_pending():
                self.process_midi_message(message)
        except:
            pass
    
    def process_midi_message(self, message):
        """Process individual MIDI message"""
        current_time = time.time()
        self.last_message_time = current_time
        self.message_count += 1
        
        channel = getattr(message, 'channel', 0)
        
        # Store activity for visualization
        self.channel_activity[channel].append({
            'time': current_time,
            'message': message,
            'type': message.type
        })
        
        # Keep only recent activity (last 5 seconds)
        cutoff_time = current_time - 5
        self.channel_activity[channel] = [
            activity for activity in self.channel_activity[channel]
            if activity['time'] > cutoff_time
        ]
        
        # Handle specific message types
        if message.type == 'note_on':
            if message.velocity > 0:
                self.note_velocities[f"{channel}_{message.note}"] = message.velocity
            else:
                # Note off (velocity 0)
                key = f"{channel}_{message.note}"
                if key in self.note_velocities:
                    del self.note_velocities[key]
                    
        elif message.type == 'note_off':
            key = f"{channel}_{message.note}"
            if key in self.note_velocities:
                del self.note_velocities[key]
                
        elif message.type == 'control_change':
            self.cc_values[channel][message.control] = message.value
            
        print(f"CH{channel+1:2d}: {message}")
    
    def draw_channel_bars(self):
        """Draw activity bars for each MIDI channel"""
        bar_height = 40
        bar_spacing = 45
        start_y = 80
        bar_width = 800
        
        current_time = time.time()
        
        for channel in range(16):
            y_pos = start_y + channel * bar_spacing
            color = self.channel_colors[channel]
            
            # Base bar (inactive)
            pygame.draw.rect(self.screen, (50, 50, 50), 
                           (50, y_pos, bar_width, bar_height))
            
            # Calculate activity level
            activity_level = 0
            if channel in self.channel_activity:
                recent_messages = [
                    msg for msg in self.channel_activity[channel]
                    if current_time - msg['time'] < 1.0  # Last 1 second
                ]
                activity_level = min(len(recent_messages) * 20, 100)  # Scale to percentage
            
            # Active bar
            if activity_level > 0:
                active_width = int(bar_width * activity_level / 100)
                pygame.draw.rect(self.screen, color, 
                               (50, y_pos, active_width, bar_height))
            
            # Channel label
            label = self.font.render(f"CH {channel+1:2d}", True, self.WHITE)
            self.screen.blit(label, (10, y_pos + 10))
            
            # Activity percentage
            if activity_level > 0:
                activity_text = self.font.render(f"{activity_level}%", True, self.WHITE)
                self.screen.blit(activity_text, (bar_width + 60, y_pos + 10))
    
    def draw_info_panel(self):
        """Draw information panel"""
        info_x = 900
        info_y = 80
        
        # Connection status
        status_color = self.GREEN if self.midi_input else self.RED
        status_text = "CONNECTED" if self.midi_input else "DISCONNECTED"
        status_surface = self.font.render(f"Status: {status_text}", True, status_color)
        self.screen.blit(status_surface, (info_x, info_y))
        
        # Message count
        count_surface = self.font.render(f"Messages: {self.message_count}", True, self.WHITE)
        self.screen.blit(count_surface, (info_x, info_y + 30))
        
        # Last message time
        if self.last_message_time:
            time_diff = time.time() - self.last_message_time
            if time_diff < 60:
                time_text = f"Last: {time_diff:.1f}s ago"
            else:
                time_text = "Last: >1min ago"
        else:
            time_text = "Last: Never"
        
        time_surface = self.font.render(time_text, True, self.WHITE)
        self.screen.blit(time_surface, (info_x, info_y + 60))
        
        # Active notes
        active_notes = len(self.note_velocities)
        notes_surface = self.font.render(f"Active notes: {active_notes}", True, self.WHITE)
        self.screen.blit(notes_surface, (info_x, info_y + 90))
        
        # Instructions
        instructions = [
            "Instructions:",
            "- Play your Kaossilator",
            "- Watch for activity bars",
            "- Press ESC to quit"
        ]
        
        for i, instruction in enumerate(instructions):
            color = self.YELLOW if i == 0 else self.WHITE
            text_surface = self.font.render(instruction, True, color)
            self.screen.blit(text_surface, (info_x, info_y + 130 + i * 25))
    
    def run(self):
        """Main visualization loop"""
        clock = pygame.time.Clock()
        
        # Connect to MIDI
        if not self.connect_midi():
            print("Failed to connect to MIDI device. Continuing in demo mode...")
        
        print("\nMIDI Visualizer running...")
        print("Play your Kaossilator Pro to see activity!")
        print("Press ESC to quit\n")
        
        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
            
            # Process MIDI messages
            self.midi_callback()
            
            # Clear screen
            self.screen.fill(self.BLACK)
            
            # Draw title
            title = self.title_font.render("Kaossilator Pro MIDI Visualizer", True, self.WHITE)
            title_rect = title.get_rect(center=(self.width // 2, 30))
            self.screen.blit(title, title_rect)
            
            # Draw channel bars
            self.draw_channel_bars()
            
            # Draw info panel
            self.draw_info_panel()
            
            # Update display
            pygame.display.flip()
            clock.tick(60)  # 60 FPS
        
        # Cleanup
        if self.midi_input:
            self.midi_input.close()
        pygame.quit()

def main():
    # List available MIDI devices
    print("=" * 50)
    print("KAOSSILATOR PRO MIDI VISUALIZER")
    print("=" * 50)
    
    visualizer = MIDIVisualizer()
    device_names = visualizer.list_midi_devices()
    
    if device_names:
        print(f"\nStarting visualizer...")
        visualizer.run()
    else:
        print("No MIDI devices found. Please check your Kaossilator Pro connection.")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main() 