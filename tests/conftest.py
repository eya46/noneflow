import json
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import nonebot
import pytest
from nonebot.adapters.github import Adapter
from nonebug import NONEBOT_INIT_KWARGS
from nonebug.app import App
from pytest_mock import MockerFixture
from respx import MockRouter

if TYPE_CHECKING:
    from nonebot.plugin import Plugin


def pytest_configure(config: pytest.Config) -> None:
    config.stash[NONEBOT_INIT_KWARGS] = {
        "driver": "~none",
        "input_config": {
            "base": "master",
            "adapter_path": "adapter_path",
            "bot_path": "bot_path",
            "plugin_path": "plugin_path",
            "registry_repository": "owner/registry",
        },
        "github_repository": "owner/repo",
        "github_run_id": "123456",
        "github_event_path": "event_path",
        "plugin_test_output": "test_output",
        "plugin_test_result": False,
        "github_apps": [],
    }


@pytest.fixture(scope="session", autouse=True)
def load_plugin(nonebug_init: None) -> set["Plugin"]:
    nonebot.get_driver().register_adapter(Adapter)
    return nonebot.load_plugins(str(Path(__file__).parent.parent / "src" / "plugins"))


@pytest.fixture()
async def app(app: App, tmp_path: Path, mocker: MockerFixture):
    from src.plugins.publish.config import plugin_config

    adapter_path = tmp_path / "adapters.json"
    with adapter_path.open("w") as f:
        json.dump(
            [
                {
                    "module_name": "module_name1",
                    "project_link": "project_link1",
                    "name": "name",
                    "desc": "desc",
                    "author": "author",
                    "homepage": "https://v2.nonebot.dev",
                    "tags": [],
                    "is_official": False,
                },
            ],
            f,
        )
    bot_path = tmp_path / "bots.json"
    with bot_path.open("w") as f:
        json.dump(
            [
                {
                    "name": "name",
                    "desc": "desc",
                    "author": "author",
                    "homepage": "https://v2.nonebot.dev",
                    "tags": [],
                    "is_official": False,
                },
            ],
            f,
        )
    plugin_path = tmp_path / "plugins.json"
    with plugin_path.open("w") as f:
        json.dump(
            [
                {
                    "module_name": "module_name1",
                    "project_link": "project_link1",
                    "name": "name",
                    "desc": "desc",
                    "author": "author",
                    "homepage": "https://v2.nonebot.dev",
                    "tags": [],
                    "is_official": False,
                },
            ],
            f,
        )

    mocker.patch.object(plugin_config.input_config, "adapter_path", adapter_path)
    mocker.patch.object(plugin_config.input_config, "bot_path", bot_path)
    mocker.patch.object(plugin_config.input_config, "plugin_path", plugin_path)
    mocker.patch.object(plugin_config, "skip_plugin_test", False)

    yield app

    from src.utils.store_test.utils import get_pypi_data

    get_pypi_data.cache_clear()


@pytest.fixture(autouse=True, scope="function")
def clear_cache(app: App):
    """每次运行前都清除 cache"""
    from src.utils.validation.utils import check_url

    check_url.cache_clear()


@pytest.fixture
def mocked_api(respx_mock: MockRouter):
    respx_mock.get("exception", name="exception").mock(side_effect=httpx.ConnectError)
    respx_mock.get(
        "https://pypi.org/pypi/project_link/json", name="project_link"
    ).respond(
        json={
            "info": {
                "version": "0.0.1",
            },
            "urls": [
                {
                    "upload_time_iso_8601": "2023-09-01T00:00:00+00:00Z",
                }
            ],
        }
    )
    respx_mock.get(
        "https://pypi.org/pypi/nonebot-plugin-treehelp/json",
        name="project_link_treehelp",
    ).respond(
        json={
            "info": {
                "version": "0.3.1",
            },
            "urls": [
                {
                    "upload_time_iso_8601": "2021-08-01T00:00:00+00:00",
                }
            ],
        }
    )
    respx_mock.get(
        "https://pypi.org/pypi/nonebot-plugin-datastore/json",
        name="project_link_datastore",
    ).respond(
        json={
            "info": {
                "version": "1.0.0",
            }
        }
    )
    respx_mock.get(
        "https://pypi.org/pypi/nonebot-plugin-wordcloud/json",
        name="project_link_wordcloud",
    ).respond(
        json={
            "info": {
                "version": "0.5.0",
            }
        }
    )
    respx_mock.get(
        "https://pypi.org/pypi/project_link1/json", name="project_link1"
    ).respond()
    respx_mock.get(
        "https://pypi.org/pypi/project_link_failed/json", name="project_link_failed"
    ).respond(404)
    respx_mock.get("https://www.baidu.com", name="homepage_failed").respond(404)
    respx_mock.get("https://nonebot.dev/", name="homepage").respond()
    respx_mock.get(
        "https://raw.githubusercontent.com/nonebot/nonebot2/master/assets/adapters.json",
        name="store_adapters",
    ).respond(
        json=[
            {
                "module_name": "nonebot.adapters.onebot.v11",
                "project_link": "nonebot-adapter-onebot",
                "name": "OneBot V11",
                "desc": "OneBot V11 协议",
                "author": "yanyongyu",
                "homepage": "https://onebot.adapters.nonebot.dev/",
                "tags": [],
                "is_official": True,
            },
            {
                "module_name": "nonebot.adapters.onebot.v12",
                "project_link": "nonebot-adapter-onebot",
                "name": "OneBot V12",
                "desc": "OneBot V12 协议",
                "author": "yanyongyu",
                "homepage": "https://onebot.adapters.nonebot.dev/",
                "tags": [],
                "is_official": True,
            },
        ],
    )
    yield respx_mock
