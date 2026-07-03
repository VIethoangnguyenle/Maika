"""fresh-session tier (Cursor/Antigravity): executor chạy trong worker context MỚI.

dispatch() trả về worker prompt. Parent (orchestrator) đưa prompt này vào
`worker_command` của profiles/execution-mode.yaml qua orchestrator.dispatch_worker()
— mỗi node một worker context sạch, KHÔNG cần user mở session thủ công."""


def dispatch(handoff_path, result_path):
    return (
        f"Read {{ platform.framework_root }}/procedures/executor.md and execute the handoff at "
        f"{handoff_path}. Write the outcome to {result_path} per the TASK_RESULT schema."
    )
