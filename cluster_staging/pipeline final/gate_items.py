"""
Fixed teacher-forced texts for the merge gate.

These are held-out GSM8K-style items. Because the gate is teacher-forced, the
continuations do NOT need to be correct or model-generated — both sides are fed
the identical token sequence and only their logits are compared. What matters is
that the texts are (a) fixed, (b) in the trained format, (c) long enough to give
a few hundred compared positions.

Prompt construction goes through utils.build_prompt so it stays the single
source of truth. If utils is not importable, a local fallback is used.
"""

try:
    from utils import build_prompt
except Exception:  # standalone / different cwd
    def build_prompt(q):
        return f"Question: {q}\nAnswer:"


_ITEMS = [
    (
        "Janet's ducks lay 16 eggs per day. She eats three for breakfast every "
        "morning and bakes muffins for her friends every day with four. She sells "
        "the remainder at the farmers' market daily for $2 per fresh duck egg. How "
        "much in dollars does she make every day at the farmers' market?",
        " Janet uses 3 + 4 = 7 eggs per day.\nShe sells 16 - 7 = 9 eggs per day.\n"
        "She makes 9 * $2 = $18 per day.\n#### 18",
    ),
    (
        "A robe takes 2 bolts of blue fiber and half that much white fiber. How "
        "many bolts in total does it take?",
        " The robe takes 2 / 2 = 1 bolt of white fiber.\nIn total it takes "
        "2 + 1 = 3 bolts.\n#### 3",
    ),
    (
        "Josh decides to try flipping a house. He buys a house for $80,000 and then "
        "puts in $50,000 in repairs. This increased the value of the house by 150%. "
        "How much profit did he make?",
        " The value increased by 80000 * 1.5 = $120,000.\nThe new value is "
        "80000 + 120000 = $200,000.\nHe spent 80000 + 50000 = $130,000.\n"
        "His profit is 200000 - 130000 = $70,000.\n#### 70000",
    ),
    (
        "James decides to run 3 sprints 3 times a week. He runs 60 meters each "
        "sprint. How many total meters does he run a week?",
        " He runs 3 * 3 = 9 sprints a week.\nHe runs 9 * 60 = 540 meters.\n#### 540",
    ),
    (
        "Every day, Wendi feeds each of her chickens three cups of mixed chicken "
        "feed. She gives 15 cups in the morning and 25 cups in the afternoon. If "
        "she has 20 chickens, how many cups does she need in the final meal?",
        " Her chickens need 20 * 3 = 60 cups per day.\nShe has given 15 + 25 = 40 "
        "cups.\nShe needs 60 - 40 = 20 cups in the final meal.\n#### 20",
    ),
]

GATE_TEXTS = [build_prompt(q) + a for q, a in _ITEMS]
