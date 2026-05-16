#!/usr/bin/env python3
"""Generate README screenshots for the Python versions."""

from __future__ import annotations

import os
import random
from pathlib import Path

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from stardodger.classic import HEIGHT, WIDTH, StarDodger
from stardodger.plus import StarDodgerPlus


ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "media"


def draw_sample_trail(app: StarDodger, frames: int = 92) -> None:
    app.state.slow_speed = False
    app.state.rng = random.Random(1992)
    app.start_screen()

    for frame in range(frames):
        climb = (frame // 13) % 2 == 0
        old_x, old_y = app.player_x, app.player_y
        app.player_x += app.step
        app.player_y += app.step if climb else -app.step
        app.line(old_x, old_y, app.player_x, app.player_y, (0, 232, 255), 2)

    app.screen.blit(app.game_surface, (0, 0))


def save_scaled(surface: pygame.Surface, path: Path, scale: int = 2) -> None:
    scaled = pygame.transform.scale(surface, (WIDTH * scale, HEIGHT * scale))
    pygame.image.save(scaled, path)


def main() -> None:
    MEDIA.mkdir(exist_ok=True)

    classic = StarDodger(scale=1)
    draw_sample_trail(classic)
    save_scaled(classic.screen, MEDIA / "classic.png")
    pygame.quit()

    plus = StarDodgerPlus(scale=1)
    draw_sample_trail(plus)
    plus.put_text(plus.screen, 2, 22, "C CPC  F full  R reset  ESC title", (0, 232, 255))
    save_scaled(plus.screen, MEDIA / "plus.png")
    plus.cpc_visual = True
    draw_sample_trail(plus)
    plus.put_text(plus.screen, 2, 22, "C CPC  F full  R reset  ESC title", (0, 232, 255))
    save_scaled(plus.cpc_frame(), MEDIA / "plus-cpc.png")
    pygame.quit()


if __name__ == "__main__":
    main()
