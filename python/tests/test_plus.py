from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from stardodger import plus
from stardodger.classic import UPDATE_STEP_SECONDS
from stardodger.plus import StarDodgerPlus


def make_key_event(char: str) -> pygame.event.Event:
    return pygame.event.Event(
        pygame.KEYDOWN,
        key=getattr(pygame, f"K_{char.lower()}"),
        unicode=char,
    )


class StarDodgerPlusTests(unittest.TestCase):
    def test_name_entry_accepts_chris_without_restart(self) -> None:
        plus.SCORES_PATH = Path(os.environ.get("TMPDIR", "/tmp")) / (
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

    def test_cpc_toggle_does_not_intercept_name_entry(self) -> None:
        app = StarDodgerPlus(scale=1)
        try:
            app.mode = "name"
            pygame.event.post(make_key_event("c"))
            app.handle_events()

            self.assertFalse(app.cpc_visual)
            self.assertEqual(app.name_buffer, "C")

            app.mode = "hall"
            pygame.event.post(make_key_event("c"))
            app.handle_events()

            self.assertTrue(app.cpc_visual)
        finally:
            pygame.quit()

    def test_fixed_update_pace_matches_go_steps(self) -> None:
        app = StarDodgerPlus(scale=1)
        try:
            app.state.slow_speed = False
            app.start_screen()
            app.obstacles = []
            app.player_y = 390
            for _ in range(60):
                app.advance_game(UPDATE_STEP_SECONDS)

            self.assertEqual(app.mode, "game")
            self.assertAlmostEqual(app.player_x, 240)

            app.state.slow_speed = True
            app.start_screen()
            app.obstacles = []
            app.player_y = 390
            for _ in range(60):
                app.advance_game(UPDATE_STEP_SECONDS)

            self.assertEqual(app.mode, "game")
            self.assertAlmostEqual(app.player_x, 180)
        finally:
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
