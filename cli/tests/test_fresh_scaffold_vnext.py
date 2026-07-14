from cli.commands.init import run_init
from cli.commands.task import run_task
from cli.platforms import get_platform

import pytest


@pytest.mark.parametrize("platform_key", ["generic", "codex", "antigravity", "claude-code"])
def test_every_fresh_scaffold_can_start_vnext_task(tmp_path, maika_root, platform_key):
    target = tmp_path / platform_key
    run_init(
        target_dir=str(target), maika_root=str(maika_root), platform_key=platform_key,
        selected_mcps=[], language="python", assume_yes=True,
    )
    framework_root = get_platform(platform_key).framework_root
    assert (target / framework_root / "profiles" / "execution-mode.yaml").exists()
    assert run_task("start", target_dir=str(target), change_id="fresh", title="Fresh") == 0
    assert (target / framework_root / "changes" / "fresh" / "STATE.yaml").exists()
