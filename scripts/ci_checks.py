"""Fail the required CI job if any test was skipped or none ran."""

import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
suites = list(root.iter("testsuite"))
assert sum(int(s.get("tests", 0)) for s in suites) > 0, "No tests executed"
assert sum(int(s.get("skipped", 0)) for s in suites) == 0, "Required tests were skipped"
assert sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites) == 0
print("Required test report: no failures, errors or skips")
