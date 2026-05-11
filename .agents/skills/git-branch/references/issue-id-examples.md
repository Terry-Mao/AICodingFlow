# IssueID recognition examples

Recognize issue IDs from these common forms:

- plain number: `123`
- hash form: `#123`
- issue wording: `issue 123`, `issue #123`, `IssueID 123`, `IssueID: #123`
- GitHub issue URL: `https://github.com/<owner>/<repo>/issues/123`
- GitHub pull request URL only when the user clearly identifies it as the task issue: `https://github.com/<owner>/<repo>/pull/123`
- repository shorthand: `<owner>/<repo>#123`
- branch-like references: `issue-123`, `issue/123`, `<type>/<short-desc>-123`

If several numbers appear, prefer the one explicitly described as the issue or task ID. If that is ambiguous, ask the user to choose.
