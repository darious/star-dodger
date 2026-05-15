#!/usr/bin/env python3
"""STAR DODGER Plus.

Classic STAR DODGER v2 gameplay with practical modern conveniences:
resizable/fullscreen scaling, restart/title keys, and persistent high scores.

Original Amstrad CPC BASIC game: STAR DODGER v2 by G. French (14-2-92).
The faithful port remains in star_dodger.py; this file intentionally reuses
that gameplay instead of changing it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pygame

from star_dodger import (
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


class StarDodgerPlus(StarDodger):
    def __init__(self, scale: int | None = None, fullscreen: bool = False) -> None:
        self.fullscreen = fullscreen
        super().__init__(scale=scale)
        self.windowed_size = (WIDTH * self.scale, HEIGHT * self.scale)
        self.configure_window()
        self.state.hall_of_fame = self.load_scores()
        pygame.display.set_caption(f"STAR DODGER Plus - original by {ORIGINAL_AUTHOR}")

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
        self.put_text(self.screen, 3, 22, "Plus: F fullscreen  R restart  ESC title  Q quit", CYAN)
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

    def capture_name(self, event: pygame.event.Event) -> None:
        before = list(self.state.hall_of_fame)
        super().capture_name(event)
        if self.mode == "hall" and self.state.hall_of_fame != before:
            self.save_scores()

    def show_hall_of_fame(self) -> None:
        super().show_hall_of_fame()
        self.put_text(self.screen, 3, 22, "SPACE title   R restart   F fullscreen", CYAN)

    def present(self) -> None:
        window_w, window_h = self.window.get_size()
        scale = min(window_w / WIDTH, window_h / HEIGHT)
        scaled_w = max(1, round(WIDTH * scale))
        scaled_h = max(1, round(HEIGHT * scale))
        self.window.fill(BLACK)
        if scaled_w == WIDTH and scaled_h == HEIGHT:
            frame = self.screen
        else:
            frame = pygame.transform.scale(self.screen, (scaled_w, scaled_h))
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
