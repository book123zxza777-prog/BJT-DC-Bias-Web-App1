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


from dc_bias import (  # noqa: E402
    REGION_ACTIVE, REGION_CUTOFF, REGION_SATURATION, calculate,
)


class TestCalculateActive(unittest.TestCase):
    def test_reference_operating_point(self):
        r = calculate(make())
        self.assertEqual(r.region, REGION_ACTIVE)
        self.assertEqual(r.warnings, ())
        self.assertAlmostEqual(r.vth, 2.163934, places=5)
        self.assertAlmostEqual(r.rth, 18032.7869, places=3)
        self.assertAlmostEqual(r.ib * 1e6, 12.2986, places=3)   # µA
        self.assertAlmostEqual(r.ic * 1e3, 1.22986, places=5)   # mA
        self.assertAlmostEqual(r.ie * 1e3, 1.24216, places=5)   # mA
        self.assertAlmostEqual(r.ve, 1.24216, places=5)
        self.assertAlmostEqual(r.vb, 1.94216, places=5)
        self.assertAlmostEqual(r.vc, 9.29431, places=5)
        self.assertAlmostEqual(r.vce, 8.052155, places=5)

    def test_active_invariants(self):
        r = calculate(make())
        self.assertAlmostEqual(r.ie, (100 + 1) * r.ib, places=12)
        self.assertAlmostEqual(r.vb, r.ve + 0.7, places=12)
        self.assertAlmostEqual(r.vce, r.vc - r.ve, places=12)

    def test_low_beta_stays_consistent(self):
        r = calculate(make(beta=1.0))
        self.assertEqual(r.region, REGION_ACTIVE)
        self.assertAlmostEqual(r.ic, r.ib, places=12)
        self.assertAlmostEqual(r.ie, 2 * r.ib, places=12)


class TestCalculateRegions(unittest.TestCase):
    def test_cutoff(self):
        r = calculate(make(r1=1e5, r2=1e3))
        self.assertEqual(r.region, REGION_CUTOFF)
        self.assertTrue(r.warnings)
        self.assertEqual((r.ib, r.ic, r.ie), (0.0, 0.0, 0.0))
        self.assertEqual(r.ve, 0.0)
        self.assertAlmostEqual(r.vb, 12 * 1e3 / 101e3, places=9)
        self.assertEqual(r.vc, 12.0)
        self.assertEqual(r.vce, 12.0)

    def test_saturation(self):
        r = calculate(make(rc=2e4))
        self.assertEqual(r.region, REGION_SATURATION)
        self.assertTrue(r.warnings)
        self.assertLess(r.vce, 0.3)


class TestCalculateGuardrails(unittest.TestCase):
    def test_overflow_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            calculate(make(vcc=1e308, r1=1e308, r2=1e308))


if __name__ == "__main__":
    unittest.main()
