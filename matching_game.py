import pygame
import random
import time
import math
from dataclasses import dataclass, field
from typing import Tuple, Optional, Set, List, Dict

@dataclass
class GameState:
    level: int = 1
    score: int = 0
    matches_found: int = 0
    selected_tile: Optional[Tuple[int, int]] = None
    game_time: float = 0
    message: str = "Little Scientists: Matching Adventure Quest!"
    matched_pairs: Set[Tuple[int, int]] = field(default_factory=set)
    game_complete: bool = False
    game_active: bool = False

class Tile:
    def __init__(self, color: Tuple[int, int, int], rect: pygame.Rect):
        self.color = color
        self.rect = rect
        self.flip_progress = 0
        self.is_flipping = False
        self.revealed = False
        self.flip_start_time = 0
        self.matched = False
        self.flip_duration = 0.3

    def update_flip(self, current_time: float) -> bool:
        if self.is_flipping:
            progress = min((current_time - self.flip_start_time) / self.flip_duration, 1)
            self.flip_progress = progress
            if progress >= 1:
                self.is_flipping = False
                self.revealed = not self.revealed
                return True
        return False

    def start_flip(self, current_time: float) -> None:
        self.is_flipping = True
        self.flip_start_time = current_time


# new button feature
class Button:
    def __init__(self, text: str, rect: pygame.Rect, color: Tuple[int, int, int], hover_color: Tuple[int, int, int]):
        self.text = text
        self.rect = rect
        self.color = color
        self.hover_color = hover_color
        self.font = pygame.font.Font(None, 48)  # Increased default font size
        self.is_hovered = False

    def draw(self, screen: pygame.Surface) -> None:
        self.is_hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        text_surface = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def is_clicked(self, pos: Tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)

class ScienceGame:
    # Level 1: 4x4 grid (8 pairs needed)
    # Level 2: 5x5 grid (12 pairs needed)
    COLORS = {
        1: [  # Level 1 colors (8 pairs)
            (230, 25, 75),    # Red
            (60, 180, 75),    # Green
            (255, 225, 25),   # Yellow
            (0, 130, 200),    # Blue
            (245, 130, 48),   # Orange
            (145, 30, 180),   # Purple
            (70, 240, 240),   # Cyan
            (240, 50, 230),   # Magenta
        ],
        2: [  # Level 2 colors (12 pairs)
            (230, 25, 75),    # Red
            (60, 180, 75),    # Green
            (255, 225, 25),   # Yellow
            (0, 130, 200),    # Blue
            (245, 130, 48),   # Orange
            (145, 30, 180),   # Purple
            (70, 240, 240),   # Cyan
            (240, 50, 230),   # Magenta
            (210, 245, 60),   # Lime
            (250, 190, 212),  # Pink
            (0, 128, 128),    # Teal
            (220, 190, 255),  # Lavender
        ]
    }

    SCIENCE_MESSAGES = [
        "Excellent observation!",
        "Data match found!",
        "Scientific success!",
        "Discovery made!",
    ]

    def __init__(self):
        pygame.init()
        self.fullscreen = True
        self.screen = self.set_screen_mode()
        pygame.display.set_caption("Science Matching Game")
        
        self.font = pygame.font.Font(None, 36)
        self.title_font = pygame.font.Font(None, 48)
        
        self.state = GameState()
        self.tiles: Dict[Tuple[int, int], Tile] = {}
        self.particles = self._create_particles()
        
        self.waiting_for_reset = False
        self.reset_start_time = 0
        self.transition_active = False
        self.transition_start_time = 0
        self.background_color = (20, 30, 40)
        
        screen_center_x = self.screen.get_width() // 2
        self.start_button = Button("Start", pygame.Rect(screen_center_x - 100, 400, 200, 50), 
                                 (0, 200, 0), (0, 255, 0))
        self.quit_button = Button("Quit", pygame.Rect(screen_center_x - 100, 470, 200, 50), 
                                 (200, 0, 0), (255, 0, 0))
        self.exit_button = Button("X", 
                                pygame.Rect(self.screen.get_width() - 50, 10, 40, 40),
                                (200, 0, 0),
                                (255, 0, 0))
        
        self.game_started = False
        self.countdown_start = 0
        self.setup_level()

    def set_screen_mode(self) -> pygame.Surface:
        if self.fullscreen:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            return pygame.display.set_mode((800, 600))

    def _create_particles(self) -> List[List[float]]:
        width, height = self.screen.get_width(), self.screen.get_height()
        return [[random.randint(0, width), 
                 random.randint(0, height),
                 random.uniform(-0.5, 0.5),
                 random.uniform(-0.5, 0.5),
                 random.randint(150, 255),
                 random.randint(2, 5)]
                for _ in range(50)]

 # new level set up

    def setup_level(self) -> None:
        self.grid_size = 4 if self.state.level == 1 else 5
        
        # Calculate tile size based on screen dimensions
        screen_width = self.screen.get_width()
        screen_height = self.screen.get_height()
        
        # Use the smaller screen dimension to ensure squares fit
        usable_height = screen_height - 200  # Account for UI elements (top and bottom margins)
        max_tile_width = screen_width // (self.grid_size + 1)  # Add padding
        max_tile_height = usable_height // (self.grid_size + 1)
        
        # Use the smaller of the two to maintain square tiles
        self.tile_size = min(max_tile_width, max_tile_height)
        
        # Calculate margins to center the grid
        self.margin_x = (screen_width - (self.grid_size * self.tile_size)) // 2
        self.margin_y = ((screen_height - (self.grid_size * self.tile_size)) // 2) + 80  # Increased offset for larger header
        
        # Get colors for current level
        colors = self.COLORS[self.state.level]
        
        if self.state.level == 1:
            needed_pairs = (self.grid_size * self.grid_size) // 2
            color_pairs = []
            for i in range(needed_pairs):
                color_pairs.extend([colors[i], colors[i]])
        else:
            color_pairs = []
            for i in range(12):
                color_pairs.extend([colors[i], colors[i]])
        
        random.shuffle(color_pairs)
        
        # Create tiles with new positioning
        self.tiles.clear()
        color_index = 0
        
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                # Skip the center tile in level 2 to create donut shape
                if self.state.level == 2 and row == 2 and col == 2:
                    continue
                    
                rect = pygame.Rect(
                    self.margin_x + col * self.tile_size,
                    self.margin_y + row * self.tile_size,
                    self.tile_size - 10,
                    self.tile_size - 10
                )
                self.tiles[(row, col)] = Tile(color_pairs[color_index], rect)
                color_index += 1
    def start_next_level(self) -> None:
        self.state.level += 1
        self.state.matches_found = 0
        self.state.matched_pairs.clear()
        self.state.selected_tile = None
        self.state.message = f"Starting Level {self.state.level}! More complex level ahead!"
        self.setup_level()
        self.transition_active = False
        self.transition_start_time = 0

    def show_transition_screen(self, text1: str, text2: str) -> None:
        overlay = pygame.Surface(self.screen.get_size())
        overlay.set_alpha(200)
        overlay.fill((20, 30, 40))
        
        msg1 = self.title_font.render(text1, True, (100, 200, 255))
        msg2 = self.font.render(text2, True, (255, 255, 255))
        
        self.screen.blit(overlay, (0, 0))
        screen_center_x = self.screen.get_width() // 2
        self.screen.blit(msg1, (screen_center_x - msg1.get_width() // 2, 250))
        self.screen.blit(msg2, (screen_center_x - msg2.get_width() // 2, 320))
        pygame.display.flip()  # Make sure the transition screen is displayed

    # Also replace the handle_click method
    def handle_click(self, pos: Tuple[int, int], current_time: float) -> None:
        if self.waiting_for_reset or self.transition_active:
            return

        x, y = pos
        row = (y - self.margin_y) // self.tile_size
        col = (x - self.margin_x) // self.tile_size
        
        # Skip if clicked position is not valid or is the center hole in level 2
        if not (0 <= row < self.grid_size and 0 <= col < self.grid_size) or \
           (self.state.level == 2 and row == 2 and col == 2):
            return
            
        # Skip if the tile doesn't exist (center hole)
        if (row, col) not in self.tiles:
            return
            
        tile = self.tiles[(row, col)]
        if tile.revealed or tile.is_flipping or tile.matched:
            return

        tile.start_flip(current_time)
        
        if not self.state.selected_tile:
            self.state.selected_tile = (row, col)
        else:
            prev_row, prev_col = self.state.selected_tile
            prev_tile = self.tiles[(prev_row, prev_col)]
            
            if tile.color == prev_tile.color:
                tile.matched = prev_tile.matched = True
                self.state.matched_pairs.update([(prev_row, prev_col), (row, col)])
                self.state.matches_found += 1
                self.state.score += 10 * self.state.level
                self.state.message = random.choice(self.SCIENCE_MESSAGES)
            else:
                self.waiting_for_reset = True
                self.reset_start_time = current_time
            
            self.state.selected_tile = None

    def update_tiles(self, current_time: float) -> None:
        if self.waiting_for_reset and current_time - self.reset_start_time > 1:
            for tile in self.tiles.values():
                if tile.revealed and not tile.matched:
                    tile.start_flip(current_time)
            self.waiting_for_reset = False

        for tile in self.tiles.values():
            tile.update_flip(current_time)

    def update_particles(self) -> None:
        width, height = self.screen.get_width(), self.screen.get_height()
        for particle in self.particles:
            particle[0] = (particle[0] + particle[2]) % width
            particle[1] = (particle[1] + particle[3]) % height
            particle[4] -= 0.5
            if particle[4] <= 0:
                particle[0] = random.randint(0, width)
                particle[1] = random.randint(0, height)
                particle[4] = random.randint(150, 255)

    def draw_laboratory_ui(self) -> None:
        self.screen.fill(self.background_color)
        
        # Draw particles
        for particle in self.particles:
            pygame.draw.circle(self.screen, (int(particle[4]),) * 3, 
                            (int(particle[0]), int(particle[1])), int(particle[5]))

        # Create larger header area
        header_height = 120
        pygame.draw.rect(self.screen, (30, 40, 50), (0, 0, self.screen.get_width(), header_height))
        pygame.draw.line(self.screen, (50, 150, 200), (0, header_height), 
                        (self.screen.get_width(), header_height), 3)
        
        # Create fonts for stats - reduced from 72 to 56
        stats_font = pygame.font.Font(None, 56)
        
        # Define stats with spacing
        stats = [
            f"LEVEL: {self.state.level}",
            f"TIME: {self.state.game_time:.1f}s",
            f"SCORE: {self.state.score}"
        ]
        
        # Calculate total width of all stats
        total_width = 0
        stat_surfaces = []
        for text in stats:
            surface = stats_font.render(text, True, (100, 200, 255))
            stat_surfaces.append(surface)
            total_width += surface.get_width()
        
        # Increased spacing between stats from 50 to 100
        spacing = 100
        total_width += spacing * (len(stats) - 1)
        
        # Calculate starting x position to center all stats
        start_x = (self.screen.get_width() - total_width) // 2
        current_x = start_x
        
        # Draw centered stats
        for surface in stat_surfaces:
            self.screen.blit(surface, (current_x, header_height // 2 - surface.get_height() // 2))
            current_x += surface.get_width() + spacing

        # Update exit button position and size
        self.exit_button.rect = pygame.Rect(self.screen.get_width() - 80, 20, 60, 60)
        self.exit_button.font = pygame.font.Font(None, 48)  # Larger font for exit button
        self.exit_button.draw(self.screen)

        # Draw message at bottom with larger font
        message_font = pygame.font.Font(None, 48)  # Increased font size for message
        msg_surface = message_font.render(self.state.message, True, (255, 255, 255))
        self.screen.blit(msg_surface, 
                        ((self.screen.get_width() - msg_surface.get_width()) // 2, 
                        self.screen.get_height() - 60))

    def draw_tile(self, tile: Tile) -> None:
                if tile.is_flipping:
                    scale = abs(math.cos(tile.flip_progress * math.pi))
                    scaled_width = tile.rect.width * scale
                    x_offset = (tile.rect.width - scaled_width) / 2
                    scaled_rect = pygame.Rect(
                        tile.rect.x + x_offset,
                        tile.rect.y,
                        scaled_width,
                        tile.rect.height
                    )
                    color = tile.color if tile.flip_progress >= 0.5 else (60, 80, 100)
                    pygame.draw.rect(self.screen, color, scaled_rect, border_radius=20)
                    
                    if scale > 0.1:
                        center = scaled_rect.center
                        if tile.flip_progress >= 0.5:
                            for radius in (15, 30):
                                pygame.draw.circle(self.screen, (255, 255, 255, 128), 
                                                center, int(radius * scale), 1)
                        else:
                            for offset in range(0, 31, 15):
                                pygame.draw.circle(self.screen, (100, 150, 200),
                                                center, int(offset * scale), 1)
                else:
                    if tile.revealed:
                        pygame.draw.rect(self.screen, tile.color, tile.rect, border_radius=20)
                        for radius in (15, 30):
                            pygame.draw.circle(self.screen, (255, 255, 255, 128), 
                                            tile.rect.center, radius, 1)
                    else:
                        pygame.draw.rect(self.screen, (60, 80, 100), tile.rect, border_radius=20)
                        pygame.draw.rect(self.screen, (80, 100, 120), tile.rect, 2, border_radius=20)
                        for offset in range(0, 31, 15):
                            pygame.draw.circle(self.screen, (100, 150, 200),
                                            tile.rect.center, offset, 1)

    def draw_start_screen(self) -> None:
            self.screen.fill(self.background_color)
            
            for particle in self.particles:
                pygame.draw.circle(self.screen, (int(particle[4]),) * 3, 
                                (int(particle[0]), int(particle[1])), int(particle[5]))
                
            self.exit_button.draw(self.screen)

            title_text = self.title_font.render("Epic Memory Match!", True, (255, 255, 255))
            title_rect = title_text.get_rect(center=(self.screen.get_width() // 2, 200))
            self.screen.blit(title_text, title_rect)

            self.start_button.draw(self.screen)
            self.quit_button.draw(self.screen)
        
    def run(self) -> None:
        clock = pygame.time.Clock()
        while True:
            current_time = time.time()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        return
                    elif event.key == pygame.K_f:
                        self.fullscreen = not self.fullscreen
                        self.screen = self.set_screen_mode()
                        self.setup_level()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.exit_button.rect.collidepoint(event.pos):
                        pygame.quit()
                        return
                        
                    if not self.game_started:
                        if self.start_button.is_clicked(event.pos):
                            self.game_started = True
                            self.countdown_start = current_time
                            self.state.game_time = 0
                        elif self.quit_button.is_clicked(event.pos):
                            pygame.quit()
                            return
                    elif self.state.game_active and not self.transition_active:
                        self.handle_click(event.pos, current_time)

            if not self.game_started:
                self.update_particles()
                self.draw_start_screen()
            else:
                countdown_elapsed = current_time - self.countdown_start
                
                if countdown_elapsed < 3:
                    self.screen.fill(self.background_color)
                    countdown_text = self.title_font.render(
                        str(3 - int(countdown_elapsed)), 
                        True, 
                        (255, 255, 255)
                    )
                    countdown_rect = countdown_text.get_rect(
                        center=(self.screen.get_width() // 2, self.screen.get_height() // 2)
                    )
                    self.screen.blit(countdown_text, countdown_rect)
                else:
                    if not self.state.game_active:  # First frame after countdown
                        self.state.game_active = True
                        self.state.game_time = 0
                    
                    if self.state.game_active and not self.transition_active:
                        self.state.game_time = current_time - (self.countdown_start + 3)
                    
                    self.update_tiles(current_time)
                    self.update_particles()

                    # Handle level completion and transitions
                    required_matches = (self.grid_size * self.grid_size) // 2
                    if self.state.matches_found == required_matches:
                        if not self.transition_active:
                            self.transition_active = True
                            self.transition_start_time = current_time
                            if self.state.level == 1:
                                self.show_transition_screen(
                                    "EXPERIMENT 1 COMPLETE!",
                                    "Preparing Level 2... More complex level ahead!"
                                )
                            else:
                                self.show_transition_screen(
                                    "CONGRATULATIONS! ALL EXPERIMENTS COMPLETE!",
                                    f"Final Score: {self.state.score} - Time: {self.state.game_time:.1f}s"
                                )
                                time.sleep(2)  # Show final screen for 2 seconds
                                pygame.quit()
                                return

                        if current_time - self.transition_start_time >= 2:  # Wait 2 seconds before proceeding
                            if self.state.level == 1:
                                self.start_next_level()
                            else:
                                self.state.game_complete = True
                                pygame.quit()
                                return

                    # Only draw game if not in transition
                    if not self.transition_active:
                        self.draw_laboratory_ui()
                        for tile in self.tiles.values():
                            self.draw_tile(tile)

            pygame.display.flip()
            clock.tick(60)

if __name__ == "__main__":
    ScienceGame().run()