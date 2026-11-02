import unittest
from unittest.mock import MagicMock

from src.colors import Colors
from src.party_sort import sort_players_by_level_and_party


def player(subject, level):
    return {"Subject": subject, "PlayerIdentity": {"AccountLevel": level}}


class PartySortTests(unittest.TestCase):
    def test_party_adjacent_and_ordered_by_top_level(self):
        players = [player("a", 100), player("b", 90), player("c", 10), player("d", 50)]
        sort_players_by_level_and_party(players, {"p1": ["a", "c"]})
        self.assertEqual([p["Subject"] for p in players], ["a", "c", "b", "d"])

    def test_solos_by_level_and_missing_level(self):
        players = [player("a", None), player("b", 5), player("c", 7)]
        sort_players_by_level_and_party(players, {})
        self.assertEqual([p["Subject"] for p in players], ["c", "b", "a"])

    def test_low_party_top_level_sorts_below_solo(self):
        players = [player("a", 20), player("b", 30), player("c", 25)]
        sort_players_by_level_and_party(players, {"p1": ["a", "b"]})
        self.assertEqual([p["Subject"] for p in players], ["b", "a", "c"])


class HiddenNameTests(unittest.TestCase):
    def make(self, hide_names=False):
        return Colors(MagicMock(), hide_names, {"agentid": "Jett"}, [], {})

    def test_empty_names_get_hidden_fallback(self):
        c = self.make()
        for name in ("#", ""):
            out = c.get_color_from_team("Red", name, "x", "y", "AgentID", [])
            self.assertIn("(hidden)", out)
            self.assertIn("Jett", out)

    def test_real_name_untouched(self):
        out = self.make().get_color_from_team("Red", "Bob#123", "x", "y", "AgentID", [])
        self.assertIn("Bob#123", out)
        self.assertNotIn("(hidden)", out)


if __name__ == "__main__":
    unittest.main()
