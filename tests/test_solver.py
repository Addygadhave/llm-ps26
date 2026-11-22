import unittest
from types import SimpleNamespace

from solver import parse_response, verify, safe_eval, solve

GOOD = """Step 1: Cost of notebooks = 3 x 45 = 135.
Step 2: Cost of pens = 2 x 12 = 24.
Step 3: Total = 135 + 24 = 159.
Step 4: Change = 200 - 159 = 41.
CHECK: 200 - (3*45 + 2*12)
FINAL ANSWER: Rs. 41"""

WRONG = GOOD.replace("Rs. 41", "Rs. 51")


class FakeClient:
    def __init__(self, text):
        msg = SimpleNamespace(content=text)
        resp = SimpleNamespace(choices=[SimpleNamespace(message=msg)])
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: resp))


class SolverTests(unittest.TestCase):
    def test_parse(self):
        r = parse_response(GOOD)
        self.assertEqual(len(r.steps), 4)
        self.assertEqual(r.final_answer, "Rs. 41")
        self.assertEqual(r.check_expression, "200 - (3*45 + 2*12)")

    def test_verify_match(self):
        r = verify(parse_response(GOOD))
        self.assertTrue(r.verified)
        self.assertEqual(r.computed_value, "41")

    def test_verify_mismatch(self):
        self.assertFalse(verify(parse_response(WRONG)).verified)

    def test_percentage_and_decimals(self):
        self.assertAlmostEqual(float(safe_eval("800*(1-15/100)*(1+5/100)")), 714.0)

    def test_unsafe_expression_rejected(self):
        with self.assertRaises(ValueError):
            safe_eval("__import__('os').system('ls')")

    def test_missing_check(self):
        r = verify(parse_response("Step 1: x\nFINAL ANSWER: 5"))
        self.assertIsNone(r.verified)

    def test_solve_with_fake_client(self):
        r = solve("any problem", client=FakeClient(GOOD))
        self.assertTrue(r.verified)

    def test_empty_problem(self):
        with self.assertRaises(ValueError):
            solve("   ", client=FakeClient(GOOD))

    def test_bold_markdown_reply(self):
        r = verify(parse_response("**Step 1:** a = 2+3\n**CHECK:** 2+3\n**FINAL ANSWER:** 5"))
        self.assertTrue(r.verified)


if __name__ == "__main__":
    unittest.main()
