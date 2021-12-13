from collections import OrderedDict

import requests
from github.Issue import Issue
from pytest_mock import MockerFixture

from src.models import BotPublishInfo


def test_bot_info() -> None:
    info = BotPublishInfo(
        name="name",
        desc="desc",
        author="author",
        homepage="https://www.baidu.com",
        tags=["tag"],
        is_official=False,
    )

    assert OrderedDict(info.dict()) == OrderedDict(
        name="name",
        desc="desc",
        author="author",
        homepage="https://www.baidu.com",
        tags=["tag"],
        is_official=False,
    )


def test_bot_from_issue(mocker: MockerFixture) -> None:
    body = """
        <!-- DO NOT EDIT ! -->
        <!--
        - name: name
        - desc: desc
        - homepage: https://www.baidu.com
        - tags: tag
        - is_official: false
        -->
        """
    mock_issue: Issue = mocker.MagicMock()  # type: ignore
    mock_issue.body = body  # type: ignore
    mock_issue.user.login = "author"  # type: ignore

    info = BotPublishInfo.from_issue(mock_issue)

    assert OrderedDict(info.dict()) == OrderedDict(
        name="name",
        desc="desc",
        author="author",
        homepage="https://www.baidu.com",
        tags=["tag"],
        is_official=False,
    )


def mocked_requests_get(url: str):
    class MockResponse:
        def __init__(self, status_code: int):
            self.status_code = status_code

    if url == "https://pypi.org/pypi/project_link/json":
        return MockResponse(200)
    if url == "https://v2.nonebot.dev":
        return MockResponse(200)

    return MockResponse(404)


def test_bot_info_validation_success(mocker: MockerFixture) -> None:
    """测试验证成功的情况"""
    mocker.patch("requests.get", side_effect=mocked_requests_get)

    info = BotPublishInfo(
        name="name",
        desc="desc",
        author="author",
        homepage="https://v2.nonebot.dev",
        tags=["tag"],
        is_official=False,
    )

    assert info.is_valid
    assert (
        info.validation_message
        == """> Bot: name\n\n**✅ All tests passed, you are ready to go!**\n\n<details><summary>Report Detail</summary><pre><code><li>✅ Project <a href="https://v2.nonebot.dev">homepage</a> returns 200.</li></code></pre></details>"""
    )

    calls = [  # type: ignore
        mocker.call("https://v2.nonebot.dev"),  # type: ignore
    ]
    requests.get.assert_has_calls(calls)  # type: ignore


def test_bot_info_validation_failed(mocker: MockerFixture) -> None:
    """测试验证失败的情况"""
    mocker.patch("requests.get", side_effect=mocked_requests_get)

    info = BotPublishInfo(
        name="name",
        desc="desc",
        author="author",
        homepage="https://www.baidu.com",
        tags=["tag"],
        is_official=False,
    )

    assert not info.is_valid
    assert (
        info.validation_message
        == """> Bot: name\n\n**⚠️ We have found following problem(s) in pre-publish progress:**\n<pre><code><li>⚠️ Project <a href="https://www.baidu.com">homepage</a> returns 404.<dt>Please make sure that your project has a publicly visible homepage.</dt></li></code></pre>"""
    )

    calls = [  # type: ignore
        mocker.call("https://www.baidu.com"),  # type: ignore
    ]
    requests.get.assert_has_calls(calls)  # type: ignore
