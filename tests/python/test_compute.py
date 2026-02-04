import unittest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from python_mse.compute import compute_signals


class TestSignalComputation(unittest.TestCase):
    def test_basic_signals(self):
        """Test that signals are computed for a simple dataset."""
        data = {
            "XLE": [
                100,
                101,
                102,
                103,
                104,
                105,
                106,
                107,
                108,
                109,
                110,
                111,
                112,
                113,
                114,
                115,
                116,
                117,
                118,
                119,
                120,
            ],
            "TLT": [
                110,
                109,
                108,
                107,
                106,
                105,
                104,
                103,
                102,
                101,
                100,
                99,
                98,
                97,
                96,
                95,
                94,
                93,
                92,
                91,
                90,
            ],
            "XLK": [
                150,
                151,
                152,
                153,
                154,
                155,
                156,
                157,
                158,
                159,
                160,
                161,
                162,
                163,
                164,
                165,
                166,
                167,
                168,
                169,
                170,
            ],
            "XLU": [
                65,
                65.1,
                65.2,
                65.3,
                65.4,
                65.5,
                65.6,
                65.7,
                65.8,
                65.9,
                66,
                66.1,
                66.2,
                66.3,
                66.4,
                66.5,
                66.6,
                66.7,
                66.8,
                66.9,
                67,
            ],
            "SPY": [
                400,
                401,
                402,
                403,
                404,
                405,
                406,
                407,
                408,
                409,
                410,
                411,
                412,
                413,
                414,
                415,
                416,
                417,
                418,
                419,
                420,
            ],
        }
        df = pd.DataFrame(data, index=pd.date_range("2025-01-01", periods=21))
        records = compute_signals(df, window=20)

        # Check we got records
        self.assertEqual(len(records), 21)

        # First 19 should have 'NA' (window not full)
        for i in range(19):
            self.assertEqual(records[i]["signals"]["energy"], "NA")
            self.assertEqual(records[i]["signals"]["rates"], "NA")
            self.assertEqual(records[i]["signals"]["tech"], "NA")
            self.assertEqual(records[i]["signals"]["utilities"], "NA")

        # Record 20 (index 20) should have real signals
        self.assertIn(records[20]["signals"]["energy"], ["UP", "DOWN"])
        self.assertIn(records[20]["signals"]["rates"], ["UP", "DOWN"])
        self.assertIn(records[20]["signals"]["tech"], ["UP", "DOWN"])
        self.assertIn(records[20]["signals"]["utilities"], ["UP", "DOWN"])

    def test_rates_semantics(self):
        """Test that Rates = UP means TLT < MA (yields up)."""
        # Construct data where TLT falls below its 20D MA
        data = {
            "XLE": [100] * 21,
            "TLT": [110] * 10 + [105] * 11,  # drops below 107.5 MA
            "XLK": [150] * 21,
            "XLU": [65] * 21,
            "SPY": [400] * 21,
        }
        df = pd.DataFrame(data, index=pd.date_range("2025-01-01", periods=21))
        records = compute_signals(df, window=20)

        # At index 20, MA should be ~107.5, TLT is 105, so rates = UP
        self.assertEqual(records[20]["signals"]["rates"], "UP")

    def test_energy_relative_strength(self):
        """Test Energy signal based on RS ratio."""
        data = {
            "XLE": [100] * 10 + [105] * 11,  # rising
            "TLT": [110] * 21,
            "XLK": [150] * 21,
            "XLU": [65] * 21,
            "SPY": [400] * 21,
        }
        df = pd.DataFrame(data, index=pd.date_range("2025-01-01", periods=21))
        records = compute_signals(df, window=20)

        # At index 20: RS_energy = 105/400 = 0.2625, MA_energy ≈ 0.25, so RS > MA → UP
        self.assertEqual(records[20]["signals"]["energy"], "UP")

    def test_schema_completeness(self):
        """Ensure output records have all required schema fields."""
        data = {
            "XLE": [100] * 21,
            "TLT": [110] * 21,
            "XLK": [150] * 21,
            "XLU": [65] * 21,
            "SPY": [400] * 21,
        }
        df = pd.DataFrame(data, index=pd.date_range("2025-01-01", periods=21))
        records = compute_signals(df, window=20)

        record = records[20]
        self.assertIn("date", record)
        self.assertIn("signals", record)
        self.assertIn("inputs", record)
        self.assertIn("version", record)
        self.assertEqual(record["version"], "0.1")
        self.assertEqual(record["inputs"]["window"], 20)
        self.assertListEqual(
            record["inputs"]["tickers"], ["XLE", "TLT", "XLK", "XLU", "SPY"]
        )


if __name__ == "__main__":
    unittest.main()
