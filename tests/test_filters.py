import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".github", "workflow-scripts"))

from job_filters import regions, sponsorship_blocked, term_hints, wanted_title  # noqa: E402
from pipelines import classify, is_big_name  # noqa: E402


def job(title, company="Acme", location="", terms=None, flags=""):
    return {"title": title, "company": company, "location": location, "terms": terms, "flags": flags}


class Titles(unittest.TestCase):
    def test_wanted(self):
        for t in ["Software Engineer Intern", "Software Developer Co-op", "Data Analyst Intern",
                  "Machine Learning Engineer Intern", "Associate Product Manager Intern",
                  "Mechanical Design Intern", "Solutions Engineer Intern", "Quantitative Developer Intern",
                  "Technical Support Engineer Intern", "Business Analyst Co-op", "Full-Stack Developer Intern"]:
            self.assertTrue(wanted_title(t), t)

    def test_rejected(self):
        for t in ["Software Engineer", "Senior Software Engineer Intern", "Marketing Intern",
                  "PhD Software Engineer Intern", "Full Stack Developer", "Legal Intern",
                  "Contract Student Worker - Data Analyst (Part-time)"]:
            self.assertFalse(wanted_title(t), t)


class Regions(unittest.TestCase):
    def test_regions(self):
        self.assertEqual(regions("San Francisco, CA"), {"US"})
        self.assertEqual(regions("Toronto, ON"), {"CA"})
        self.assertEqual(regions("Toronto, ON · New York, NY"), {"US", "CA"})
        self.assertEqual(regions("Remote"), set())
        self.assertEqual(regions("Remote - Canada"), {"CA"})
        self.assertEqual(regions("Remote, Australia"), {"OTHER"})
        self.assertEqual(regions("Bangalore, IN"), {"OTHER"})
        self.assertEqual(regions("London, UK"), {"OTHER"})
        self.assertEqual(regions("Waterloo, ON"), {"CA"})


class Terms(unittest.TestCase):
    def test_hints(self):
        self.assertIn(("winter", 2027), term_hints("Winter 2027, Spring 2027"))
        self.assertIn(("summer", 2027), term_hints("Summer 2027 Software Intern"))
        self.assertIn(("winter", 2027), term_hints("Software Engineering Intern - Winter '27"))
        self.assertIn(("summer", 2027), term_hints("2027 Summer Intern"))
        self.assertIn(("winter", 2027), term_hints("Co-op (January 2027 - April 2027)"))
        self.assertEqual(term_hints("You may apply. May be remote"), set())


class Freshness(unittest.TestCase):
    def test_deadline_hint(self):
        from job_filters import deadline_hint
        self.assertEqual(deadline_hint("Applications close on October 15"), "closes October 15")
        self.assertEqual(deadline_hint("We review on a rolling basis"), "rolling")
        self.assertEqual(deadline_hint("Nothing here"), "")

    def test_tier(self):
        from pipelines import company_tier
        self.assertEqual(company_tier("Amazon"), 2)
        self.assertEqual(company_tier("Tiny Startup"), 0)


class Sponsorship(unittest.TestCase):
    def test_blocked(self):
        for s in ["U.S. citizenship is required", "Must be a US citizen", "US citizens only",
                  "Active security clearance", "ITAR restricted", "🇺🇸 something"]:
            self.assertTrue(sponsorship_blocked(s), s)

    def test_ok(self):
        for s in ["", "We sponsor visas for eligible candidates", "We are unable to sponsor visas.",
                  "will not pursue visa sponsorship", "authorized to work without sponsorship", "🛂 something"]:
            self.assertFalse(sponsorship_blocked(s), s)


class Pipelines(unittest.TestCase):
    def test_summer_needs_big_name_and_us(self):
        self.assertEqual(classify(job("Software Engineer Intern, Summer 2027", "Google", "Mountain View, CA")), ["summer"])
        self.assertEqual(classify(job("Software Engineer Intern, Summer 2027", "Tiny Startup", "New York, NY")), [])
        self.assertEqual(classify(job("Software Engineer Intern, Summer 2027", "Google", "Toronto, ON")), [])

    def test_winter_any_company_us_ca(self):
        self.assertEqual(classify(job("Software Engineer Intern", "Tiny Startup", "Toronto, ON", terms="Winter 2027")), ["winter"])
        self.assertEqual(classify(job("Software Engineer Intern", "Tiny Startup", "New York, NY", terms="Spring 2027")), ["winter"])
        self.assertEqual(classify(job("Software Engineer Intern", "Tiny Startup", "London, UK", terms="Winter 2027")), [])

    def test_wrong_term_rejected(self):
        self.assertEqual(classify(job("Software Engineer Intern", "Google", "Seattle, WA", terms="Fall 2026")), [])
        self.assertEqual(classify(job("Software Engineer Intern", "Google", "Seattle, WA", terms="Winter 2026")), [])
        self.assertEqual(classify(job("2026 Software Engineer Intern", "Google", "Seattle, WA")), [])

    def test_unstated_term_goes_to_both_when_big_us(self):
        self.assertEqual(sorted(classify(job("Software Engineer Intern", "Google", "Seattle, WA"))), ["summer", "winter"])
        self.assertEqual(classify(job("Software Engineer Intern", "Tiny Startup", "Seattle, WA")), ["winter"])

    def test_sponsorship_flag(self):
        self.assertEqual(classify(job("Software Engineer Intern", "Google", "Seattle, WA", flags="🇺🇸")), [])

    def test_big_names(self):
        self.assertTrue(is_big_name("Amazon Web Services"))
        self.assertTrue(is_big_name("Google DeepMind"))
        self.assertTrue(is_big_name("Apple"))
        self.assertFalse(is_big_name("Apple Federal Credit Union"))
        self.assertFalse(is_big_name("Metadata Inc"))


if __name__ == "__main__":
    unittest.main()
