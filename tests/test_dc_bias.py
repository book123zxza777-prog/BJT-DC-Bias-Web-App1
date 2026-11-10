import math
import unittest

from dc_bias import BiasInputs, ValidationError, to_ohms, validate_inputs


def make(**overrides):
    base = dict(vcc=12.0, r1=1e5, r2=2.2e4, rc=2.2e3, re=1e3, beta=100.0, vbe=0.7)
    base.update(overrides)
    return BiasInputs(**base)


class TestUnits(unittest.TestCase):
    def test_to_ohms_scales(self):
        self.assertEqual(to_ohms(100, "kohm"), 100000.0)
        self.assertEqual(to_ohms(2.2, "mohm"), 2.2e6)
        self.assertEqual(to_ohms(470, "ohm"), 470.0)

    def test_to_ohms_rejects_unknown_unit(self):
        with self.assertRaises(ValueError):
            to_ohms(1.0, "megohm")


class TestValidation(unittest.TestCase):
    def test_validate_accepts_reference_circuit(self):
        validate_inputs(make())

    def test_validate_rejects_nonpositive_values(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_inputs(make(r1=0.0))
        self.assertIn("r1", ctx.exception.errors)

        with self.assertRaises(ValidationError) as ctx:
            validate_inputs(make(beta=0.0))
        self.assertIn("beta", ctx.exception.errors)

        with self.assertRaises(ValidationError) as ctx:
            validate_inputs(make(vcc=0.0))
        self.assertIn("vcc", ctx.exception.errors)

    def test_validate_rejects_vbe_out_of_range(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_inputs(make(vbe=12.0))
        self.assertIn("vbe", ctx.exception.errors)

        with self.assertRaises(ValidationError) as ctx:
            validate_inputs(make(vbe=0.0))
        self.assertIn("vbe", ctx.exception.errors)

    def test_validate_rejects_non_finite(self):
        for bad in (math.nan, math.inf, -math.inf):
            with self.assertRaises(ValidationError) as ctx:
                validate_inputs(make(vcc=bad))
            self.assertIn("vcc", ctx.exception.errors)


if __name__ == "__main__":
    unittest.main()
