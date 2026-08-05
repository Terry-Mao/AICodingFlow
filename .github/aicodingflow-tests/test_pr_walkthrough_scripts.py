from __future__ import annotations

import unittest

from script_imports import import_script


d3_runtime = import_script(
    ".agents/skills/pr-walkthrough/scripts/d3_canvas_runtime.py",
    "pr_walkthrough_d3_canvas_runtime",
)
validator = import_script(
    ".agents/skills/pr-walkthrough/scripts/validate_d3_canvas.py",
    "pr_walkthrough_validate_d3_canvas",
)


class PrWalkthroughScriptsTest(unittest.TestCase):
    def test_safe_href_allows_only_explicit_safe_schemes_or_relative_paths(self) -> None:
        self.assertEqual(d3_runtime.safe_href("https://example.test/path"), "https://example.test/path")
        self.assertEqual(d3_runtime.safe_href("http://example.test/path"), "http://example.test/path")
        self.assertEqual(d3_runtime.safe_href("file:///tmp/pr-walkthrough/index.html"), "file:///tmp/pr-walkthrough/index.html")
        self.assertEqual(d3_runtime.safe_href("../relative/path.html"), "../relative/path.html")
        self.assertEqual(d3_runtime.safe_href("#section"), "#section")
        self.assertEqual(d3_runtime.safe_href("javascript:alert(1)"), "#")
        self.assertEqual(d3_runtime.safe_href("java\nscript:alert(1)"), "#")
        self.assertEqual(d3_runtime.safe_href("data:text/html,alert(1)"), "#")
        self.assertEqual(d3_runtime.safe_href("//example.test/path"), "#")

    def test_runtime_sanitizes_graph_data_urls_before_rendering_hrefs(self) -> None:
        runtime_script = d3_runtime.d3_canvas_runtime_script()

        self.assertIn("function safeHref(value)", runtime_script)
        self.assertIn("escapeHtml(safeHref(file.url))", runtime_script)
        self.assertIn("escapeHtml(safeHref(comment.url))", runtime_script)
        self.assertIn("escapeHtml(safeHref(link.url))", runtime_script)

    def test_static_validate_rejects_pr_specific_system_overview_attachments(self) -> None:
        data = d3_runtime.sample_data()
        overview = next(graph for graph in data["graphs"] if graph["id"] == "system-overview")
        overview["nodes"][0]["files"] = [{"path": "changed.py", "url": "https://example.test/files"}]

        errors = validator.static_validate(d3_runtime.html_template(data), data)

        self.assertIn("Graph system-overview node surface must not include PR attachment field `files`", errors)

    def test_static_validate_rejects_pr_specific_system_overview_text(self) -> None:
        data = d3_runtime.sample_data()
        overview = next(graph for graph in data["graphs"] if graph["id"] == "system-overview")
        overview["nodes"][0]["summary"] = "This overview explains the PR diff for reviewers."

        errors = validator.static_validate(d3_runtime.html_template(data), data)

        self.assertIn("Graph system-overview node surface contains PR-specific wording", errors)

    def test_static_validate_accepts_sample_overview_without_pr_attachments(self) -> None:
        data = d3_runtime.sample_data()

        errors = validator.static_validate(d3_runtime.html_template(data), data)

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
