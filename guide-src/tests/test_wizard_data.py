from __future__ import annotations

import json
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class TestWizardData(unittest.TestCase):
    def setUp(self):
        self.data = load(SRC / "wizard" / "steps.json")
        self.config = load(SRC / "config.json")

    def test_every_when_key_is_a_declared_question(self):
        question_ids = {q["id"] for q in self.data["questions"]}
        for step in self.data["steps"]:
            for key in step.get("when", {}):
                self.assertIn(key, question_ids, "unknown question in {0}".format(step["id"]))

    def test_every_when_value_is_a_declared_option(self):
        options = {q["id"]: set(q["options"]) for q in self.data["questions"]}
        for step in self.data["steps"]:
            for key, values in step.get("when", {}).items():
                for value in values:
                    self.assertIn(
                        value, options[key], "unknown option in {0}".format(step["id"])
                    )

    def test_step_ids_are_unique(self):
        ids = [s["id"] for s in self.data["steps"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_final_step_is_add_server(self):
        self.assertEqual(self.data["steps"][-1]["id"], "add-server")

    def test_every_step_has_strings_in_every_declared_language(self):
        for lang in self.config["languages"]:
            code = lang["code"]
            path = SRC / "wizard" / "strings" / "{0}.json".format(code)
            if not path.exists():
                continue
            strings = load(path)["steps"]
            for step in self.data["steps"]:
                self.assertIn(step["id"], strings, "{0} missing in {1}".format(step["id"], code))
                for field in ("title", "why", "verifyHint", "failHint"):
                    self.assertIn(
                        field,
                        strings[step["id"]],
                        "{0}.{1} missing in {2}".format(step["id"], field, code),
                    )

    def test_every_troubleshoot_anchor_exists_in_the_source_fragment(self):
        # Reads the source fragment, not the built page: anchors are authored
        # in the fragment and build.py embeds it verbatim, so this is the same
        # guarantee without making the suite depend on build output.
        fragment = SRC / "content" / "troubleshooting" / "zh-TW.html"
        self.assertTrue(fragment.exists(), "write the troubleshooting fragment first")
        html = fragment.read_text(encoding="utf-8")
        for step in self.data["steps"]:
            anchor = step.get("troubleshoot")
            if anchor:
                self.assertIn(
                    'id="{0}"'.format(anchor),
                    html,
                    "anchor {0} referenced by {1} does not exist".format(anchor, step["id"]),
                )

    def _combos(self):
        questions = self.data["questions"]

        def walk(index, acc):
            if index == len(questions):
                yield dict(acc)
                return
            q = questions[index]
            for opt in q["options"]:
                acc[q["id"]] = opt
                for c in walk(index + 1, acc):
                    yield c

        return walk(0, {})

    def _matching(self, answers):
        return [
            s
            for s in self.data["steps"]
            if all(answers.get(k) in v for k, v in s.get("when", {}).items())
        ]

    def test_the_unconditional_steps_are_exactly_the_expected_two(self):
        # The test below depends on knowing which steps match unconditionally.
        # Pin that here so adding a third one cannot silently weaken it.
        unconditional = [s["id"] for s in self.data["steps"] if not s.get("when")]
        self.assertEqual(unconditional, ["tmux-handled", "add-server"])

    def test_every_answer_combination_gets_a_conditional_step(self):
        # Count ONLY steps whose `when` actually matched. `tmux-handled` and
        # `add-server` match everything, so asserting "more than one step" can
        # never fail — deleting every conditional step still leaves those two,
        # and the suite would stay green while the wizard told a Mac user
        # nothing about turning on SSH.
        for answers in self._combos():
            conditional = [s for s in self._matching(answers) if s.get("when")]
            self.assertGreater(
                len(conditional), 0, "no conditional step for {0}".format(answers)
            )

    def test_every_machine_option_has_its_own_setup_step(self):
        # Whichever machine the reader picks, the plan must contain a step
        # gated on that specific answer — otherwise they are never told how to
        # get SSH running on it.
        machine = [q for q in self.data["questions"] if q["id"] == "machine"][0]
        for option in machine["options"]:
            gated = [
                s
                for s in self.data["steps"]
                if option in s.get("when", {}).get("machine", [])
            ]
            self.assertTrue(gated, "no machine step for {0}".format(option))


if __name__ == "__main__":
    unittest.main()
