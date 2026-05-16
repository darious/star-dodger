#!/usr/bin/env python3
"""STAR DODGER Plus.

Classic STAR DODGER v2 gameplay with practical modern conveniences:
resizable/fullscreen scaling, restart/title keys, and persistent high scores.

Original Amstrad CPC BASIC game: STAR DODGER v2 by G. French (14-2-92).
The faithful port remains in stardodger.classic; this file intentionally
reuses that gameplay instead of changing it.
"""

from __future__ import annotations

import argparse
from importlib import resources
import json
import sys
from pathlib import Path

import pygame

from .classic import (
    BLACK,
    CYAN,
    HEIGHT,
    ORIGINAL_AUTHOR,
    ORIGINAL_DATE,
    ScoreEntry,
    StarDodger,
    WIDTH,
)


SCORES_PATH = Path("star_dodger_plus_scores.json")
CPC_MODE_WIDTH = 320
CPC_MODE_HEIGHT = 200
CPC_MODE_SCALE = 2


class StarDodgerPlus(StarDodger):
    def __init__(self, scale: int | None = None, fullscreen: bool = False) -> None:
        self.fullscreen = fullscreen
        self.cpc_visual = False
        super().__init__(scale=scale)
        self.windowed_size = (WIDTH * self.scale, HEIGHT * self.scale)
        self.scanlines = self.make_scanlines()
        self.cpc_glyphs = self.load_cpc_glyphs()
        self.cpc_glyphs_mode1 = {
            char: pygame.transform.scale(glyph, (8, 8))
            for char, glyph in self.cpc_glyphs.items()
        }
        self.cpc_game_surface = pygame.Surface((CPC_MODE_WIDTH, CPC_MODE_HEIGHT))
        self.configure_window()
        self.state.hall_of_fame = self.load_scores()
        pygame.display.set_caption(f"STAR DODGER Plus - original by {ORIGINAL_AUTHOR}")

    def make_scanlines(self) -> pygame.Surface:
        scanlines = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for y in range(0, HEIGHT, 4):
            pygame.draw.rect(scanlines, (0, 0, 0, 38), pygame.Rect(0, y, WIDTH, 1))
        return scanlines

    def load_cpc_glyphs(self) -> dict[str, pygame.Surface]:
        glyphs: dict[str, pygame.Surface] = {}
        font_path = resources.files("stardodger.assets").joinpath("amstrad-character-set.png")
        sheet = pygame.image.load(str(font_path)).convert()
        for code in range(256):
            glyph = pygame.Surface((16, 16), pygame.SRCALPHA)
            source_x = 1 + (code % 32) * 9
            source_y = 1 + (code // 32) * 9
            for y in range(8):
                for x in range(8):
                    r, g, b, _a = sheet.get_at((source_x + x, source_y + y))
                    if r < 80 and g < 80 and b < 80:
                        pygame.draw.rect(glyph, (255, 255, 255), pygame.Rect(x * 2, y * 2, 2, 2))
            glyphs[chr(code)] = glyph
        return glyphs

    def put_text(
        self,
        target: pygame.Surface,
        column: int,
        row: int,
        value: str,
        colour: tuple[int, int, int] = CYAN,
        font: pygame.font.Font | None = None,
    ) -> None:
        if not self.cpc_visual:
            super().put_text(target, column, row, value, colour, font)
            return
        x, y = self.text_xy(column, row)
        for index, char in enumerate(value):
            glyph = self.cpc_glyphs.get(char, self.cpc_glyphs.get("?"))
            if glyph is None:
                continue
            coloured = self.tint_glyph(glyph, colour)
            target.blit(coloured, (x + index * 16, y))

    def tint_glyph(
        self,
        glyph: pygame.Surface,
        colour: tuple[int, int, int],
    ) -> pygame.Surface:
        coloured = glyph.copy()
        coloured.fill((*colour, 255), special_flags=pygame.BLEND_RGBA_MULT)
        return coloured

    def cpc_mode_y(self, y: float) -> int:
        return max(0, min(CPC_MODE_HEIGHT - 1, CPC_MODE_HEIGHT - round(y / CPC_MODE_SCALE)))

    def cpc_mode_point(self, x: float, y: float) -> tuple[int, int]:
        px = max(0, min(CPC_MODE_WIDTH - 1, round(x / CPC_MODE_SCALE)))
        return px, self.cpc_mode_y(y)

    def configure_window(self) -> None:
        if self.fullscreen:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)

    def load_scores(self) -> list[ScoreEntry]:
        defaults = self.state.hall_of_fame
        if not SCORES_PATH.exists():
            return defaults
        try:
            data = json.loads(SCORES_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return defaults
        if not isinstance(data, list):
            return defaults

        scores: list[ScoreEntry] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", ""))[:6].upper() or "PLAYER"
            try:
                screens = int(item.get("screens", 0))
            except (TypeError, ValueError):
                continue
            scores.append(ScoreEntry(name, screens))

        if not scores:
            return defaults
        scores.sort(key=lambda entry: entry.screens, reverse=True)
        return scores[:6]

    def save_scores(self) -> None:
        data = [
            {"name": entry.name, "screens": int(entry.screens)}
            for entry in self.state.hall_of_fame[:6]
        ]
        SCORES_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type == pygame.VIDEORESIZE and not self.fullscreen:
                self.windowed_size = (
                    max(WIDTH, event.w),
                    max(HEIGHT, event.h),
                )
                self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
                continue
            if event.type != pygame.KEYDOWN:
                continue

            if self.mode == "name":
                self.capture_name(event)
                continue

            if event.key == pygame.K_q:
                self.quit()
            if event.key == pygame.K_f:
                self.toggle_fullscreen()
                continue
            if event.key == pygame.K_c:
                self.cpc_visual = not self.cpc_visual
                if self.mode == "instructions":
                    self.show_instructions()
                elif self.mode == "hall":
                    self.show_hall_of_fame()
                continue
            if self.mode == "instructions":
                self.choose_speed(event)
                continue
            if event.key == pygame.K_r and self.mode in {"game", "wait", "hall"}:
                self.start_game()
                continue
            if event.key == pygame.K_ESCAPE:
                self.show_instructions()
                continue
            if self.mode == "wait" and self.wait_callback is not None:
                callback = self.wait_callback
                self.wait_callback = None
                callback()
            elif self.mode == "hall":
                if event.key == pygame.K_SPACE:
                    self.show_instructions()

    def toggle_fullscreen(self) -> None:
        if not self.fullscreen:
            self.windowed_size = self.window.get_size()
        self.fullscreen = not self.fullscreen
        self.configure_window()

    def show_instructions(self) -> None:
        super().show_instructions()
        self.put_text(self.screen, 2, 22, "C CPC  F full  R reset  ESC title", CYAN)
        self.put_text(
            self.screen,
            4,
            24,
            f"Original STAR DODGER v2 by {ORIGINAL_AUTHOR} ({ORIGINAL_DATE})",
            CYAN,
        )

    def start_game(self) -> None:
        self.state.q = 5
        self.state.screens_completed = 0
        self.wait_callback = None
        self.start_screen()

    def start_screen(self) -> None:
        self.cpc_game_surface.fill(BLACK)
        super().start_screen()

    def capture_name(self, event: pygame.event.Event) -> None:
        before = list(self.state.hall_of_fame)
        super().capture_name(event)
        if self.mode == "hall" and self.state.hall_of_fame != before:
            self.save_scores()

    def show_hall_of_fame(self) -> None:
        super().show_hall_of_fame()
        self.put_text(self.screen, 2, 22, "SPACE title  C CPC  R reset  F full", CYAN)

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        colour: tuple[int, int, int],
        width: int = 2,
    ) -> None:
        super().line(x1, y1, x2, y2, colour, width)
        pygame.draw.line(
            self.cpc_game_surface,
            colour,
            self.cpc_mode_point(x1, y1),
            self.cpc_mode_point(x2, y2),
            max(1, round(width / CPC_MODE_SCALE)),
        )

    def plot(self, x: float, y: float, colour: tuple[int, int, int], radius: int = 2) -> None:
        super().plot(x, y, colour, radius)
        px, py = self.cpc_mode_point(x, y)
        pygame.draw.rect(self.cpc_game_surface, colour, pygame.Rect(px - 1, py - 1, 2, 2))

    def draw_obstacles(self) -> None:
        super().draw_obstacles()
        star = self.tint_glyph(self.cpc_glyphs_mode1["*"], (235, 235, 235))
        for x, y in self.obstacles:
            self.cpc_game_surface.blit(star, (round(x / CPC_MODE_SCALE) - 4, self.cpc_mode_y(y) - 4))

    def cpc_game_frame(self) -> pygame.Surface:
        return pygame.transform.scale(
            self.cpc_game_surface,
            (CPC_MODE_WIDTH * CPC_MODE_SCALE, CPC_MODE_HEIGHT * CPC_MODE_SCALE),
        )

    def cpc_frame(self) -> pygame.Surface:
        frame = self.cpc_game_frame() if self.mode == "game" else self.screen.copy()
        frame.blit(self.scanlines, (0, 0))
        pygame.draw.rect(frame, (0, 0, 128), frame.get_rect(), 5)
        pygame.draw.rect(frame, (0, 0, 0), frame.get_rect(), 1)
        return frame

    def present(self) -> None:
        window_w, window_h = self.window.get_size()
        scale = min(window_w / WIDTH, window_h / HEIGHT)
        scaled_w = max(1, round(WIDTH * scale))
        scaled_h = max(1, round(HEIGHT * scale))
        self.window.fill(BLACK)
        source = self.cpc_frame() if self.cpc_visual else self.screen
        if scaled_w == WIDTH and scaled_h == HEIGHT:
            frame = source
        else:
            frame = pygame.transform.scale(source, (scaled_w, scaled_h))
        self.window.blit(frame, ((window_w - scaled_w) // 2, (window_h - scaled_h) // 2))
        pygame.display.flip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run STAR DODGER Plus, original game by G. French."
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=None,
        help="Initial integer window scale. The window remains resizable.",
    )
    parser.add_argument("--fullscreen", action="store_true", help="Start fullscreen.")
    args = parser.parse_args()
    try:
        StarDodgerPlus(scale=args.scale, fullscreen=args.fullscreen).run()
    except pygame.error as exc:
        print(f"pygame could not start: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
