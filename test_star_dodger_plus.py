from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import star_dodger_plus
from star_dodger_plus import StarDodgerPlus


def make_key_event(char: str) -> pygame.event.Event:
    return pygame.event.Event(
        pygame.KEYDOWN,
        key=getattr(pygame, f"K_{char.lower()}"),
        unicode=char,
    )


class StarDodgerPlusTests(unittest.TestCase):
    def test_name_entry_accepts_chris_without_restart(self) -> None:
        star_dodger_plus.SCORES_PATH = Path(os.environ.get("TMPDIR", "/tmp")) / (
            "star_dodger_plus_test_scores.json"
        )
        app = StarDodgerPlus(scale=1)
        try:
            app.mode = "name"
            app.state.q = 25
            app.player_x = 123
            for char in "chris":
                pygame.event.post(make_key_event(char))
                app.handle_events()

            self.assertEqual(app.mode, "name")
            self.assertEqual(app.name_buffer, "CHRIS")
            self.assertEqual(app.state.q, 25)
            self.assertEqual(app.player_x, 123)
        finally:
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
