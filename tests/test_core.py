import os
import socket
import sys
import unittest

from environment_metadata_provider import EnvironmentMetadataProvider, EnvironmentMetadata


class TestEnvironmentMetadata(unittest.TestCase):
    def test_is_immutable_mapping(self):
        m = EnvironmentMetadata({"a": 1, "b": 2})
        with self.assertRaises(TypeError):
            m["a"] = 99

    def test_protocol_methods(self):
        m = EnvironmentMetadata({"a": 1, "b": 2})
        self.assertEqual(m["a"], 1)
        self.assertEqual(m.get("missing", 7), 7)
        self.assertEqual(set(m.keys()), {"a", "b"})
        self.assertEqual(dict(m.items()), {"a": 1, "b": 2})
        self.assertIn("a", m)
        self.assertNotIn("z", m)
        self.assertEqual(len(m), 2)
        self.assertEqual(sorted(m), ["a", "b"])

    def test_as_dict_is_mutable_copy(self):
        m = EnvironmentMetadata({"a": 1})
        d = m.as_dict()
        d["a"] = 5
        self.assertEqual(m["a"], 1)


class TestEnvironmentMetadataProvider(unittest.TestCase):
    def test_collects_all_fields_once(self):
        calls = {"clock": 0}

        def fake_clock():
            calls["clock"] += 1
            return 1700000000.0

        provider = EnvironmentMetadataProvider(
            clock=fake_clock,
            gethostname=lambda: "worker-42",
            getpid=lambda: 9999,
            python_version="3.12.1",
        )
        m = provider.metadata()
        self.assertEqual(m["hostname"], "worker-42")
        self.assertEqual(m["pid"], 9999)
        self.assertEqual(m["python_version"], "3.12.1")
        self.assertEqual(m["boot_time"], 1700000000.0)
        self.assertEqual(calls["clock"], 1)

    def test_default_clock_uses_time_time(self):
        provider = EnvironmentMetadataProvider(
            gethostname=lambda: "h",
            getpid=lambda: 1,
            python_version="v",
        )
        self.assertIsInstance(provider.metadata()["boot_time"], float)

    def test_default_hostname_and_pid_match_system(self):
        provider = EnvironmentMetadataProvider(python_version="v")
        m = provider.metadata()
        self.assertEqual(m["hostname"], socket.gethostname())
        self.assertEqual(m["pid"], os.getpid())

    def test_metadata_is_stable_reference(self):
        provider = EnvironmentMetadataProvider(
            clock=lambda: 1.0,
            gethostname=lambda: "h",
            getpid=lambda: 1,
            python_version="v",
        )
        a = provider.metadata()
        b = provider.metadata()
        self.assertIs(a, b)

    def test_enrich_adds_missing_fields(self):
        provider = EnvironmentMetadataProvider(
            clock=lambda: 100.0,
            gethostname=lambda: "host",
            getpid=lambda: 7,
            python_version="3",
        )
        out = provider.enrich({"message": "hi", "level": "ERROR"})
        self.assertEqual(out["message"], "hi")
        self.assertEqual(out["level"], "ERROR")
        self.assertEqual(out["hostname"], "host")
        self.assertEqual(out["pid"], 7)
        self.assertEqual(out["python_version"], "3")
        self.assertEqual(out["boot_time"], 100.0)

    def test_enrich_does_not_clobber_existing_keys(self):
        provider = EnvironmentMetadataProvider(
            clock=lambda: 100.0,
            gethostname=lambda: "host",
            getpid=lambda: 7,
            python_version="3",
        )
        out = provider.enrich({"hostname": "custom", "pid": 0})
        self.assertEqual(out["hostname"], "custom")
        self.assertEqual(out["pid"], 0)
        self.assertEqual(out["python_version"], "3")
        self.assertEqual(out["boot_time"], 100.0)

    def test_enrich_returns_dict_not_metadata(self):
        provider = EnvironmentMetadataProvider(
            clock=lambda: 1.0,
            gethostname=lambda: "h",
            getpid=lambda: 1,
            python_version="v",
        )
        out = provider.enrich({})
        self.assertIsInstance(out, dict)
        self.assertNotIsInstance(out, EnvironmentMetadata)

    def test_enrich_does_not_mutate_internal_state(self):
        provider = EnvironmentMetadataProvider(
            clock=lambda: 1.0,
            gethostname=lambda: "h",
            getpid=lambda: 1,
            python_version="v",
        )
        out = provider.enrich({"hostname": "evil"})
        out["hostname"] = "more-evil"
        self.assertEqual(provider.metadata()["hostname"], "h")


if __name__ == "__main__":
    unittest.main()
