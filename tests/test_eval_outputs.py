"""Deterministic graders of scripts/eval_outputs.py: they must accept right answers and reject wrong ones (no model, no network)."""
import pathlib, sys, unittest
R = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "scripts"))
import eval_outputs as eo

VLSM = {"type": "vlsm", "parent": "10.20.0.0/24", "need": [100, 50, 10]}
GOOD = "users 10.20.0.0/25 (126), servers 10.20.0.128/26 (62), mgmt 10.20.0.192/28 (14)"


class Graders(unittest.TestCase):
    def test_vlsm_accepts_valid_plan(self): self.assertTrue(eo.check_vlsm(GOOD, VLSM)[0])
    def test_vlsm_rejects_overlap(self): self.assertFalse(eo.check_vlsm("10.20.0.0/25 and 10.20.0.64/26 and 10.20.0.192/28", VLSM)[0])
    def test_vlsm_ignores_extra_unused_cidrs(self): self.assertTrue(eo.check_vlsm(GOOD + "; unused 10.20.0.208/28, 10.20.0.224/27, or 10.20.0.0/26", VLSM)[0])
    def test_vlsm_rejects_too_small(self): self.assertFalse(eo.check_vlsm("10.20.0.0/26 10.20.0.64/26 10.20.0.128/28", VLSM)[0])
    def test_vlsm_rejects_outside_parent(self): self.assertFalse(eo.check_vlsm("192.168.0.0/25 192.168.1.0/26 192.168.2.0/28", VLSM)[0])
    def test_vlsm_ignores_ipv6_and_parent_itself(self): self.assertFalse(eo.check_vlsm("10.20.0.0/24 2001:db8::/32", VLSM)[0])
    def test_number_normalisation(self):
        self.assertTrue(eo.grade("usable hosts: 4,194,302", [{"type": "regex", "pattern": r"\b4194302\b"}])[0][0])
    def test_not_regex(self):
        c = [{"type": "not_regex", "pattern": r"\bnot (in|inside) the same"}]
        self.assertFalse(eo.grade("they are not inside the same block", c)[0][0]); self.assertTrue(eo.grade("both inside", c)[0][0])
    def test_unknown_check_type_is_an_error(self):
        with self.assertRaises(ValueError): eo.grade("x", [{"type": "magic"}])


if __name__ == "__main__": unittest.main()
