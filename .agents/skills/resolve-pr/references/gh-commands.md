# GitHub commands for PR feedback

Use the verified PR number and repository for every call. Check each mutation's
response before reporting success. Save multi-line reply text to a temporary
file and pass it with `-F body=@<file>`.

```bash
gh pr view <pr> --json number,url,headRefName,headRepository,headRefOid,baseRefName,statusCheckRollup
gh pr diff <pr>
gh api 'repos/{owner}/{repo}/pulls/<pr>/reviews?per_page=100' --paginate --slurp
gh api 'repos/{owner}/{repo}/issues/<pr>/comments?per_page=100' --paginate --slurp
```

Fetch all review threads with GraphQL pagination. For unresolved threads with
more than 100 comments, fetch that thread's comments separately with the
second query.

```bash
gh api graphql --paginate --slurp -F owner='<owner>' -F name='<repo>' -F number=<pr> -f query='
query($owner: String!, $name: String!, $number: Int!, $endCursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100, after: $endCursor) {
        nodes {
          id isResolved isOutdated
          comments(first: 100) {
            totalCount
            nodes { databaseId body author { login } path line }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}'

gh api graphql --paginate --slurp -F threadId='<thread-id>' -f query='
query($threadId: ID!, $endCursor: String) {
  node(id: $threadId) {
    ... on PullRequestReviewThread {
      comments(first: 100, after: $endCursor) {
        nodes { databaseId body author { login } path line }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}'
```

Use the first comment's `databaseId` to reply within a thread. Reply to a
review body or top-level comment with a PR conversation comment. Resolve only
the verified thread ID after its outcome is complete.

```bash
gh api 'repos/{owner}/{repo}/pulls/<pr>/comments/<comment-id>/replies' -F body=@<reply-file>
gh api 'repos/{owner}/{repo}/issues/<pr>/comments' -F body=@<reply-file>
gh api graphql -F threadId='<thread-id>' -f query='mutation($threadId: ID!) { resolveReviewThread(input: {threadId: $threadId}) { thread { id isResolved } } }'
gh pr checks <pr> --watch
```
