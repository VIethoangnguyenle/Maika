# Archive Rotation

> Tài liệu tham khảo cho `knowledge-curator`. Read when archive count exceeds the retention threshold or cross-repo snapshot references are needed.

## Mục lục

- Rotate archive
- Transparency log rotation
- Cross-repo snapshot references
- Gotchas

## Rotate archive

Keep the most recent `keep_n=20` ticket folders. For older folders, append metadata to `ARCHIVE_LOG.md`, then remove the old folder only after the log write succeeds.

## Transparency log rotation

When archive runs, compact repeated bootstrap entries in active AGENT_TRANSPARENCY while preserving the full log in archive.

## Cross-repo snapshot references

Use relative paths from project root. Do not copy cross-repo snapshot content.

## Gotchas

- Sanitize ticket IDs before folder creation.
- Regex for bootstrap entries must support old and new formats.
- Reset must not clear ideation drafts unless explicitly archived or requested.
