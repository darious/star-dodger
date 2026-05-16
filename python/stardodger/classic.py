#!/usr/bin/env python3
"""STAR DODGER v2 remake.

Original Amstrad CPC BASIC game: STAR DODGER v2 by G. French (14-2-92).
This Python/pygame version is a faithful modern port of the BASIC listing in
star-dodger.bas, keeping the original author attribution, screen flow, scoring,
gap behavior, and SPACE-to-climb control.
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass, field
from typing import Callable

import pygame


ORIGINAL_AUTHOR = "G. French"
ORIGINAL_DATE = "14-2-92"
WIDTH = 640
HEIGHT = 400
TEXT_COLS = 40
CELL_W = 16
CELL_H = 16
TITLE = "StarDodger"
UPDATES_PER_SECOND = 60
UPDATE_STEP_SECONDS = 1 / UPDATES_PER_SECOND
MAX_FRAME_SECONDS = 0.25

BLACK = (0, 0, 0)
WHITE = (235, 235, 235)
CYAN = (0, 232, 255)
YELLOW = (255, 240, 0)
GREEN = (0, 255, 80)
RED = (255, 40, 40)
MAGENTA = (255, 60, 255)
BLUE = (80, 120, 255)
ORANGE = (255, 150, 20)
PURPLE = (170, 90, 255)


@dataclass
class ScoreEntry:
    name: str
    screens: int


@dataclass
class GameState:
    hall_of_fame: list[ScoreEntry] = field(
        default_factory=lambda: [
            ScoreEntry("GRAHAM", 12),
            ScoreEntry("EGGY", 10),
            ScoreEntry("NOB", 8),
            ScoreEntry("MARK", 6),
            ScoreEntry("SARAH", 4),
            ScoreEntry("HILARY", 2),
        ]
    )
    slow_speed: bool = False
    q: int = 5
    screens_completed: int = 0
    rng: random.Random = field(default_factory=random.Random)


class StarDodger:
    def __init__(self, scale: int | None = None) -> None:
        pygame.init()
        self.scale = self.resolve_scale(scale)
        pygame.display.set_caption(f"STAR DODGER v2 - original by {ORIGINAL_AUTHOR}")
        self.window = pygame.display.set_mode((WIDTH * self.scale, HEIGHT * self.scale))
        self.screen = pygame.Surface((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("couriernew,courier,monospace", 16, bold=True)
        self.big_font = pygame.font.SysFont("couriernew,courier,monospace", 18, bold=True)
        self.state = GameState()

        self.mode = "instructions"
        self.wait_callback: Callable[[], None] | None = None
        self.game_surface = pygame.Surface((WIDTH, HEIGHT))
        self.obstacles: list[tuple[float, float]] = []
        self.player_x = 0.0
        self.player_y = 200.0
        self.gap_top = 228
        self.gap_bottom = 172
        self.step = 4
        self.tick = 0
        self.update_accumulator = 0.0
        self.flash_until = 0
        self.flash_count = 0
        self.name_buffer = ""

    def resolve_scale(self, requested_scale: int | None) -> int:
        if requested_scale is not None:
            return max(1, requested_scale)
        info = pygame.display.Info()
        desktop_w = max(info.current_w, WIDTH)
        desktop_h = max(info.current_h, HEIGHT)
        scale = min(int((desktop_w * 0.9) // WIDTH), int((desktop_h * 0.9) // HEIGHT))
        return max(1, scale)

    def run(self) -> None:
        self.show_instructions()
        self.clock.tick()
        while True:
            elapsed = min(self.clock.tick(UPDATES_PER_SECOND) / 1000.0, MAX_FRAME_SECONDS)
            self.handle_events()
            self.advance_game(elapsed)
            self.present()

    def advance_game(self, elapsed_seconds: float) -> None:
        if self.mode != "game":
            self.update_accumulator = 0.0
            return
        self.update_accumulator += elapsed_seconds
        while self.update_accumulator + 1e-9 >= UPDATE_STEP_SECONDS and self.mode == "game":
            self.game_tick()
            self.update_accumulator -= UPDATE_STEP_SECONDS

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_q:
                self.quit()
            if self.mode == "instructions":
                self.choose_speed(event)
            elif self.mode == "wait" and self.wait_callback is not None:
                callback = self.wait_callback
                self.wait_callback = None
                callback()
            elif self.mode == "hall":
                if event.key == pygame.K_SPACE:
                    self.show_instructions()
            elif self.mode == "name":
                self.capture_name(event)

    def quit(self) -> None:
        pygame.quit()
        raise SystemExit

    def cpc_y(self, y: float) -> int:
        return int(HEIGHT - y)

    def text_xy(self, column: int, row: int) -> tuple[int, int]:
        return (column - 1) * CELL_W, (row - 1) * CELL_H

    def put_text(
        self,
        target: pygame.Surface,
        column: int,
        row: int,
        value: str,
        colour: tuple[int, int, int] = CYAN,
        font: pygame.font.Font | None = None,
    ) -> None:
        font = font or self.font
        x, y = self.text_xy(column, row)
        target.blit(font.render(value, True, colour), (x, y))

    def centered_text(
        self,
        target: pygame.Surface,
        row: int,
        value: str,
        colour: tuple[int, int, int] = CYAN,
    ) -> None:
        column = max(1, ((TEXT_COLS - len(value)) // 2) + 1)
        self.put_text(target, column, row, value, colour)

    def show_instructions(self) -> None:
        self.mode = "instructions"
        self.screen.fill(BLACK)
        self.put_text(self.screen, 17, 1, TITLE, CYAN, self.big_font)
        self.put_text(self.screen, 8, 3, f"Original by {ORIGINAL_AUTHOR} ({ORIGINAL_DATE})", CYAN)
        self.put_text(self.screen, 2, 5, "Avoid the killer Asterisks, and seek the", CYAN)
        self.put_text(self.screen, 10, 6, "wondrous Nextscreen Gap.", CYAN)
        self.put_text(self.screen, 13, 13, "Use SPACE to climb", CYAN)
        self.put_text(self.screen, 8, 16, "Do you want the slow speed Y/N", CYAN)

    def choose_speed(self, event: pygame.event.Event) -> None:
        if event.key not in (pygame.K_y, pygame.K_n):
            return
        self.state.slow_speed = event.key == pygame.K_y
        self.press_any_key(self.start_game)

    def press_any_key(self, callback: Callable[[], None]) -> None:
        self.put_text(self.screen, 9, 25, "Press any key to continue.", CYAN)
        self.mode = "wait"
        self.wait_callback = callback

    def start_game(self) -> None:
        self.state.q = 5
        self.start_screen()

    def start_screen(self) -> None:
        self.mode = "game"
        self.step = 3 if self.state.slow_speed else 4
        self.player_x = 0.0
        self.player_y = 200.0
        self.gap_top = 228
        self.gap_bottom = 172
        self.tick = 0
        self.obstacles = self.make_obstacles(self.state.q)
        self.game_surface.fill(BLACK)
        self.draw_borders()
        self.draw_obstacles()
        self.screen.blit(self.game_surface, (0, 0))

    def make_obstacles(self, count: int) -> list[tuple[float, float]]:
        obstacles: list[tuple[float, float]] = []
        while len(obstacles) < count:
            x = 50 + self.state.rng.random() * 561
            y = 20 + self.state.rng.random() * 361
            if x < 95 and abs(y - 200) < 40:
                continue
            obstacles.append((x, y))
        return obstacles

    def draw_borders(self) -> None:
        self.line(0, 0, 629, 0, WHITE)
        self.line(629, 0, 629, self.gap_bottom, WHITE)
        self.line(629, self.gap_top, 629, 399, WHITE)
        self.line(627, 0, 627, self.gap_bottom, WHITE)
        self.line(627, self.gap_top, 627, 399, WHITE)
        self.line(0, 399, 629, 399, WHITE)
        self.line(0, 0, 0, 399, WHITE)
        self.line(636, 0, 636, 399, MAGENTA)
        self.line(638, 0, 638, 399, WHITE)
        self.plot(629, self.gap_bottom, GREEN, 3)
        self.plot(629, self.gap_top, GREEN, 3)
        self.plot(627, self.gap_bottom, GREEN, 3)
        self.plot(627, self.gap_top, GREEN, 3)

    def draw_obstacles(self) -> None:
        for x, y in self.obstacles:
            image = self.big_font.render("*", True, WHITE)
            rect = image.get_rect(center=(round(x), self.cpc_y(y)))
            self.game_surface.blit(image, rect)

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        colour: tuple[int, int, int],
        width: int = 2,
    ) -> None:
        pygame.draw.line(
            self.game_surface,
            colour,
            (round(x1), self.cpc_y(y1)),
            (round(x2), self.cpc_y(y2)),
            width,
        )

    def plot(self, x: float, y: float, colour: tuple[int, int, int], radius: int = 2) -> None:
        pygame.draw.circle(self.game_surface, colour, (round(x), self.cpc_y(y)), radius)

    def game_tick(self) -> None:
        keys = pygame.key.get_pressed()
        climb = keys[pygame.K_SPACE]
        old_x = self.player_x
        old_y = self.player_y
        self.player_x += self.step
        self.player_y += self.step if climb else -self.step
        self.line(old_x, old_y, self.player_x, self.player_y, CYAN, 2)
        self.screen.blit(self.game_surface, (0, 0))

        result = self.collision_result()
        if result == "complete":
            self.completed_screen()
            return
        if result == "dead":
            self.zapped()
            return

        self.tick += 1
        if self.state.q > 55 and self.tick % 25 == 0:
            self.close_gap()

    def collision_result(self) -> str | None:
        x = self.player_x
        y = self.player_y
        if x >= 627:
            if self.gap_bottom <= y <= self.gap_top:
                return "complete"
            return "dead"
        if x <= 0 or y <= 0 or y >= 399:
            return "dead"
        for obstacle_x, obstacle_y in self.obstacles:
            if abs(x - obstacle_x) <= 8 and abs(y - obstacle_y) <= 10:
                return "dead"
        return None

    def close_gap(self) -> None:
        if self.gap_top - self.gap_bottom <= 8:
            return
        self.gap_top -= 2
        self.gap_bottom += 2
        self.plot(629, self.gap_bottom, GREEN, 3)
        self.plot(629, self.gap_top, GREEN, 3)
        self.plot(627, self.gap_bottom, GREEN, 3)
        self.plot(627, self.gap_top, GREEN, 3)

    def completed_screen(self) -> None:
        self.mode = "wait"
        self.screen.fill(BLACK)
        self.put_text(self.screen, 2, 1, "YOU MADE IT THROUGH THE KILLER ASTERISKS", CYAN)
        self.put_text(self.screen, 11, 13, f"Stand by for Screen {(self.state.q // 5) + 1:2d}", CYAN)
        self.state.q += 5
        self.press_any_key(self.start_screen)

    def zapped(self) -> None:
        self.state.screens_completed = (self.state.q // 5) - 1
        self.mode = "flash"
        self.flash_count = 0
        self.flash_until = pygame.time.get_ticks()
        self.draw_flash()

    def draw_flash(self) -> None:
        colours = [RED, BLACK, RED, BLACK]
        if self.flash_count < len(colours):
            self.screen.fill(colours[self.flash_count])
            self.flash_count += 1
            self.present()
            pygame.time.delay(90)
            self.draw_flash()
            return
        self.screen.fill(BLACK)
        self.put_text(self.screen, 4, 1, "YOU WERE ZAPPED BY A KILLER ASTERISK", CYAN)
        self.put_text(
            self.screen,
            6,
            13,
            f"Number of screens completed = {self.state.screens_completed:2d}",
            CYAN,
        )
        self.press_any_key(self.after_death)

    def after_death(self) -> None:
        if self.state.screens_completed > self.state.hall_of_fame[-1].screens:
            self.enter_hall_of_fame()
        else:
            self.show_hall_of_fame()

    def enter_hall_of_fame(self) -> None:
        self.mode = "name"
        self.name_buffer = ""
        self.screen.fill(BLACK)
        self.put_text(self.screen, 4, 1, "** WELL DONE **", YELLOW)
        self.put_text(self.screen, 2, 4, " YOU ARE ONE OF THE ", WHITE)
        self.put_text(self.screen, 2, 5, "  BEST STARDODGERS  ", WHITE)
        self.put_text(self.screen, 2, 6, "  IN THE UNIVERSE.", WHITE)
        self.rainbow_text(3, 10, "ENTER YOUR NAME")
        self.draw_name_entry()

    def rainbow_text(self, column: int, row: int, value: str) -> None:
        colours = [CYAN, WHITE, YELLOW, GREEN, MAGENTA, BLUE, ORANGE, PURPLE]
        for index, char in enumerate(value):
            self.put_text(self.screen, column + index, row, char, colours[index % len(colours)])

    def draw_name_entry(self) -> None:
        pygame.draw.rect(self.screen, BLACK, pygame.Rect(0, 14 * CELL_H, WIDTH, CELL_H * 2))
        self.put_text(self.screen, 7, 15, f">{self.name_buffer:<6}<", CYAN)

    def capture_name(self, event: pygame.event.Event) -> None:
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            name = self.name_buffer or "PLAYER"
            self.state.hall_of_fame.append(ScoreEntry(name, self.state.screens_completed))
            self.state.hall_of_fame.sort(key=lambda entry: entry.screens, reverse=True)
            self.state.hall_of_fame = self.state.hall_of_fame[:6]
            self.show_hall_of_fame()
            return
        if event.key == pygame.K_BACKSPACE:
            self.name_buffer = self.name_buffer[:-1]
        elif event.unicode and " " <= event.unicode <= "~" and len(self.name_buffer) < 6:
            self.name_buffer += event.unicode.upper()
        self.draw_name_entry()

    def show_hall_of_fame(self) -> None:
        self.mode = "hall"
        self.screen.fill(BLACK)
        self.put_text(self.screen, 1, 1, "  ** THE TOP SIX **", CYAN)
        colours = [CYAN, WHITE, YELLOW, GREEN, MAGENTA, BLUE]
        for index, entry in enumerate(self.state.hall_of_fame):
            self.put_text(
                self.screen,
                3,
                4 + index * 2,
                f"{entry.name:<9}  {entry.screens:3d}",
                colours[index % len(colours)],
            )
        self.put_text(self.screen, 4, 25, "   PRESS SPACE BAR", WHITE)

    def present(self) -> None:
        if self.scale == 1:
            self.window.blit(self.screen, (0, 0))
        else:
            pygame.transform.scale(self.screen, self.window.get_size(), self.window)
        pygame.display.flip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run STAR DODGER v2, original by G. French.")
    parser.add_argument(
        "--scale",
        type=int,
        default=None,
        help="Integer window scale. By default the game chooses a large scale that fits your display.",
    )
    args = parser.parse_args()
    try:
        StarDodger(scale=args.scale).run()
    except pygame.error as exc:
        print(f"pygame could not start: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
