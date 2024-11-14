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
    high_score: int = 0  # Add high score tracking
    matches_found: int = 0
    selected_tile: Optional[Tuple[int, int]] = None
    game_time: float = 0
    best_time: float = float('inf')  # Add best time tracking
    message: str = "Matching Adventure Quest!"
    matched_pairs: Set[Tuple[int, int]] = field(default_factory=set)
    game_complete: bool = False
    game_active: bool = False

class Tile:
    def __init__(self, image: pygame.Surface, rect: pygame.Rect):
        self.image = image
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
        
        self.font = pygame.font.Font(None, 80)
        self.title_font = pygame.font.Font(None, 150)
        self.countdown_font = pygame.font.Font(None, 600)
        
        self.state = GameState()
        self.tiles: Dict[Tuple[int, int], Tile] = {}
        self.particles = self._create_particles()
        
        self.waiting_for_reset = False
        self.reset_start_time = 0
        self.transition_active = False
        self.transition_start_time = 0
        self.background_color = (20, 30, 40)

        # Level 1: 4x4 grid (8 pairs needed)
        self.tile_images = [
            pygame.image.load("images/1.png").convert_alpha(),
            pygame.image.load("images/2.png").convert_alpha(),
            pygame.image.load("images/3.png").convert_alpha(),
            pygame.image.load("images/4.png").convert_alpha(),
            pygame.image.load("images/5.png").convert_alpha(),
            pygame.image.load("images/6.png").convert_alpha(),
            pygame.image.load("images/7.png").convert_alpha(),
            pygame.image.load("images/8.png").convert_alpha(),
        ]
        
        screen_center_x = self.screen.get_width() // 2
        self.start_button = Button("Let's Play!", 
                                 pygame.Rect(screen_center_x - 125, 500, 300, 100),
                                 (38, 188, 81), (98, 208, 121))  # Happy green
        self.quit_button = Button("Exit Game", 
                                pygame.Rect(screen_center_x - 125, 650, 300, 100),
                                (255, 89, 94), (255, 129, 134))  # Friendly red
        self.exit_button = Button("X", 
                                pygame.Rect(self.screen.get_width() - 50, 10, 40, 40),
                                (255, 89, 94), (255, 129, 134))
        
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
        
        # Get images for tile
        needed_pairs = (self.grid_size * self.grid_size) // 2
        tile_images = [self.tile_images[i] for i in range(needed_pairs) for _ in range(2)]
        random.shuffle(tile_images)
        
        # Create tiles with new positioning
        self.tiles.clear()
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                rect = pygame.Rect(
                    self.margin_x + col * self.tile_size,
                    self.margin_y + row * self.tile_size,
                    self.tile_size - 10,
                    self.tile_size - 10
                )
                self.tiles[(row, col)] = Tile(tile_images.pop(), rect)

    # Also replace the handle_click method
    def handle_click(self, pos: Tuple[int, int], current_time: float) -> None:
        if self.waiting_for_reset or self.transition_active:
            return

        x, y = pos
        row = (y - self.margin_y) // self.tile_size
        col = (x - self.margin_x) // self.tile_size

        # Check if (row, col) is within bounds and exists in self.tiles
        if not (0 <= row < self.grid_size and 0 <= col < self.grid_size):
            return
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
            prev_tile = self.tiles.get((prev_row, prev_col))

            if prev_tile and tile.image == prev_tile.image:
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
        self.screen.fill((15, 23, 42))
        
        header_height = 120
        pygame.draw.rect(self.screen, (0, 0, 0), (0, 0, self.screen.get_width(), header_height))
        pygame.draw.line(self.screen, (94, 180, 251), (0, header_height), 
                        (self.screen.get_width(), header_height), 3)
        
        # Draw particles
        for particle in self.particles:
            pygame.draw.circle(self.screen, (int(particle[4]),) * 3, 
                            (int(particle[0]), int(particle[1])), int(particle[5]))

        # More colorful stats
        stats_font = pygame.font.Font(None, 56)
        stats = [
            ("LEVEL " + str(self.state.level), (255, 129, 134)),  # Friendly red
            ("TIME: " + f"{self.state.game_time:.1f}s", (38, 188, 81)),  # Green
            ("SCORE: " + str(self.state.score), (94, 180, 251))  # Blue
        ]
        
        total_width = 0
        stat_surfaces = []
        for text, color in stats:
            surface = stats_font.render(text, True, color)
            stat_surfaces.append(surface)
            total_width += surface.get_width()
        
        spacing = 100
        total_width += spacing * (len(stats) - 1)
        start_x = (self.screen.get_width() - total_width) // 2
        current_x = start_x
        
        # Draw stats with shadows for fun effect
        for i, surface in enumerate(stat_surfaces):
            # Draw shadow
            shadow_surface = stats_font.render(stats[i][0], True, (180, 180, 180))
            self.screen.blit(shadow_surface, (current_x + 2, header_height // 2 - surface.get_height() // 2 + 2))
            # Draw text
            self.screen.blit(surface, (current_x, header_height // 2 - surface.get_height() // 2))
            current_x += surface.get_width() + spacing

        # Update exit button position and size
        self.exit_button.rect = pygame.Rect(self.screen.get_width() - 80, 20, 60, 60)
        self.exit_button.font = pygame.font.Font(None, 48)
        self.exit_button.draw(self.screen)

        # Draw message at bottom with larger font
            # Draw message at bottom with larger font and shadow
        message_font = pygame.font.Font(None, 48)
    # Shadow
        shadow_surface = message_font.render(self.state.message, True, (20, 30, 40))
        shadow_rect = shadow_surface.get_rect(
        center=(self.screen.get_width() // 2 + 2, self.screen.get_height() - 58)
    )
        self.screen.blit(shadow_surface, shadow_rect)
    # Main text
        msg_surface = message_font.render(self.state.message, True, (94, 180, 251))
        msg_rect = msg_surface.get_rect(
        center=(self.screen.get_width() // 2, self.screen.get_height() - 60)
    )
        self.screen.blit(msg_surface, msg_rect)

    def draw_tile(self, tile: Tile) -> None:
        if tile.is_flipping:
            scale = abs(math.cos(tile.flip_progress * math.pi))
            scaled_width = tile.rect.width * scale
            x_offset = (tile.rect.width - scaled_width) / 2
            scaled_rect = pygame.Rect(tile.rect.x + x_offset, tile.rect.y, scaled_width, tile.rect.height)
            if tile.flip_progress >= 0.5 and tile.image:
                self.screen.blit(tile.image, scaled_rect)
            else:
                pygame.draw.rect(self.screen, (194, 224, 60), scaled_rect, border_radius=20)
        else:
            if tile.revealed and tile.image:
                self.screen.blit(tile.image, tile.rect)
            elif not tile.revealed:
                pygame.draw.rect(self.screen, (194, 224, 60), tile.rect, border_radius=20)

    
    def reset_game(self) -> None:
        # Update high score before resetting
        if self.state.score > self.state.high_score:
            self.state.high_score = self.state.score
        # Update best time if game was completed
        if self.state.game_complete and self.state.game_time < self.state.best_time:
            self.state.best_time = self.state.game_time
        
        # Reset game state
        self.state = GameState(high_score=self.state.high_score, best_time=self.state.best_time)
        self.tiles.clear()
        self.setup_level()
        self.game_started = False
        self.countdown_start = 0
        self.transition_active = False
        self.transition_start_time = 0
        self.waiting_for_reset = False

    def show_transition_screen(self, text1: str) -> None:
        overlay = pygame.Surface(self.screen.get_size())
        overlay.set_alpha(200)
        overlay.fill((20, 30, 40))
    
        msg1 = self.title_font.render(text1, True, (100, 200, 255))
    
        screen_center_x = self.screen.get_width() // 2
    
        # Create larger font for score display
        score_font = pygame.font.Font(None, 100)  # Larger font for final score
        stats_font = pygame.font.Font(None, 80)  # Regular font for other stats

        # Ensure score, time, and high score texts are created to avoid unbound variable issues
        score_text = score_font.render(f"Final Score: {self.state.score}", True, (255, 255, 255))
        time_text = stats_font.render(f"Time: {self.state.game_time:.1f}s", True, (255, 255, 255))
        high_score_text = stats_font.render(f"High Score: {self.state.high_score}", True, (255, 255, 255))
    
        # Position play again button with more spacing
        self.play_again_button = Button("Play Again", 
                                pygame.Rect(screen_center_x - 150, 700, 300, 70),
                                (0, 200, 0), (0, 255, 0))

        # Display overlay and messages
        self.screen.blit(overlay, (0, 0))
        self.screen.blit(msg1, (screen_center_x - msg1.get_width() // 2, 300))  # Adjusted positioning
    
        # Display final score and other stats on the transition screen
        self.screen.blit(score_text, (screen_center_x - score_text.get_width() // 2, 450))
        self.screen.blit(time_text, (screen_center_x - time_text.get_width() // 2, 550))
        self.screen.blit(high_score_text, (screen_center_x - high_score_text.get_width() // 2, 600))

        # Draw the play again button
        self.play_again_button.draw(self.screen)
    
        pygame.display.flip()
    
    def draw_start_screen(self) -> None:
            self.screen.fill(self.background_color)
            
            for particle in self.particles:
                pygame.draw.circle(self.screen, (int(particle[4]),) * 3, 
                                (int(particle[0]), int(particle[1])), int(particle[5]))
                
            self.exit_button.draw(self.screen)

            title_text = self.title_font.render("Matching Adventure!", True, (255, 255, 255))
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
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.exit_button.rect.collidepoint(event.pos):
                        pygame.quit()
                        return
                    
                    # Only check for play again button in level 2
                    if self.transition_active and self.state.game_complete and hasattr(self, 'play_again_button'):
                        if self.play_again_button.is_clicked(event.pos):
                            self.reset_game()
                            continue
                            
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
                    countdown_text = self.countdown_font.render(
                        str(3 - int(countdown_elapsed)), 
                        True, 
                        (255, 255, 255)
                    )
                    countdown_rect = countdown_text.get_rect(
                        center=(self.screen.get_width() // 2, self.screen.get_height() // 2)
                    )
                    self.screen.blit(countdown_text, countdown_rect)
                else:
                    if not self.state.game_active:
                        self.state.game_active = True
                        self.state.game_time = 0
                    
                    if self.state.game_active and not self.transition_active:
                        self.state.game_time = current_time - (self.countdown_start + 3)
                    
                    self.update_tiles(current_time)
                    self.update_particles()
                    
                    # Calculate required matches before checking completion
                    required_matches = (self.grid_size * self.grid_size) // 2

                    # Handle level completion and transitions
                    if self.state.matches_found == required_matches:
                        if not self.transition_active:
                            self.transition_active = True
                            self.transition_start_time = current_time
                            self.show_transition_screen("CONGRATULATIONS!!")

                        if current_time - self.transition_start_time >= 2:
                            self.state.game_complete = True

                    # Continue drawing the game
                    if not self.transition_active:
                        self.draw_laboratory_ui()
                        for tile in self.tiles.values():
                            self.draw_tile(tile)

            pygame.display.flip()
            clock.tick(60)

if __name__ == "__main__":
    ScienceGame().run()