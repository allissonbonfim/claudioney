from __future__ import annotations

import pytest

from flash.config import Settings


def test_production_refuses_dev_secrets():
    with pytest.raises(RuntimeError, match="FLASH_SECRET"):
        Settings(env="production").assert_safe()
    with pytest.raises(RuntimeError, match="FLASH_ADMIN_TOKEN"):
        Settings(env="production", secret="x" * 40).assert_safe()
    Settings(env="production", secret="x" * 40, admin_token="y" * 20).assert_safe()
    Settings(env="dev").assert_safe()
