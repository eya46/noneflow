import click

from .constants import (
    ADAPTERS_PATH,
    BOTS_PATH,
    DRIVERS_PATH,
    PLUGIN_KEY_TEMPLATE,
    PLUGINS_PATH,
    PREVIOUS_PLUGINS_PATH,
    PREVIOUS_RESULTS_PATH,
    RESULTS_PATH,
    STORE_ADAPTERS_PATH,
    STORE_BOTS_PATH,
    STORE_DRIVERS_PATH,
    STORE_PLUGINS_PATH,
)
from .models import Plugin, StorePlugin, TestResult
from .utils import dump_json, get_latest_version, load_json
from .validation import validate_plugin


class StoreTest:
    """商店测试"""

    def __init__(
        self,
        offset: int = 0,
        limit: int = 1,
        force: bool = False,
    ) -> None:
        self._offset = offset
        self._limit = limit
        self._force = force

        # NoneBot 仓库中的数据
        self._store_adapters = load_json(STORE_ADAPTERS_PATH)
        self._store_bots = load_json(STORE_BOTS_PATH)
        self._store_drivers = load_json(STORE_DRIVERS_PATH)
        self._store_plugins: dict[str, StorePlugin] = {
            PLUGIN_KEY_TEMPLATE.format(
                project_link=plugin["project_link"],
                module_name=plugin["module_name"],
            ): plugin
            for plugin in load_json(STORE_PLUGINS_PATH)
        }
        # 上次测试的结果
        self._previous_results: dict[str, TestResult] = load_json(PREVIOUS_RESULTS_PATH)
        self._previous_plugins: dict[str, Plugin] = {
            PLUGIN_KEY_TEMPLATE.format(
                project_link=plugin["project_link"],
                module_name=plugin["module_name"],
            ): plugin
            for plugin in load_json(PREVIOUS_PLUGINS_PATH)
        }

    def should_skip(self, key: str) -> bool:
        """是否跳过测试"""
        if key.startswith("git+http"):
            click.echo(f"插件 {key} 为 Git 插件，无法测试，已跳过")
            return True

        # 如果强制测试，则不跳过
        if self._force:
            return False

        # 如果插件不在上次测试的结果中，则不跳过
        previous_result = self._previous_results.get(key)
        previous_plugin = self._previous_plugins.get(key)
        if not previous_result or not previous_plugin:
            return False

        # 如果插件为最新版本，则跳过测试
        latest_version = get_latest_version(previous_plugin["project_link"])
        if latest_version == previous_result["version"]:
            click.echo(f"插件 {key} 为最新版本（{latest_version}），跳过测试")
            return True
        return False

    def skip_plugin_test(self, key: str) -> bool:
        """是否跳过插件测试"""
        if key in self._previous_plugins:
            return self._previous_plugins[key].get("skip_test", False)
        return False

    async def test_plugins(
        self,
        key: str | None = None,
        config: str | None = None,
        data: str | None = None,
    ):
        """测试并更新插件商店中的插件信息"""
        new_results: dict[str, TestResult] = {}
        new_plugins: dict[str, Plugin] = {}

        if key:
            test_plugins = [(key, self._store_plugins[key])]
            plugin_configs = {key: config or ""}
            plugin_datas = {key: data}
        else:
            test_plugins = list(self._store_plugins.items())[self._offset :]
            plugin_configs = {
                key: self._previous_results.get(key, {})
                .get("inputs", {})
                .get("config", "")
                for key, _ in test_plugins
            }
            plugin_datas = {}

        # 测试上限不可能超过插件总数
        limit = min(self._limit, len(test_plugins))

        i = 1
        for key, plugin in test_plugins:
            if i > limit:
                click.echo(f"已达到测试上限 {limit}，测试停止")
                break

            try:
                if self.should_skip(key):
                    continue

                click.echo(f"{i}/{limit} 正在测试插件 {key} ...")

                new_results[key], new_plugin = await validate_plugin(
                    plugin=plugin,
                    config=plugin_configs.get(key, ""),
                    skip_test=self.skip_plugin_test(key),
                    data=plugin_datas.get(key),
                    previous_plugin=self._previous_plugins.get(key),
                )
                if new_plugin:
                    new_plugins[key] = new_plugin
            except Exception as e:
                # 如果测试中遇到意外错误，则跳过该插件
                click.echo(e)
                continue

            i += 1

        results: dict[str, TestResult] = {}
        plugins: dict[str, Plugin] = {}
        # 按照插件列表顺序输出
        for key in self._store_plugins:
            # 更新测试结果
            # 如果新的测试结果中有，则使用新的测试结果
            # 否则使用上次测试结果
            if key in new_results:
                results[key] = new_results[key]
            elif key in self._previous_results:
                results[key] = self._previous_results[key]

            # 更新插件列表
            if key in new_plugins:
                plugins[key] = new_plugins[key]
            elif key in self._previous_plugins:
                plugins[key] = self._previous_plugins[key]

        return results, plugins

    async def run(
        self, key: str | None = None, config: str | None = None, data: str | None = None
    ):
        """测试商店内插件情况"""

        results, plugins = await self.test_plugins(key, config, data)

        # 保存测试结果与生成的列表
        dump_json(ADAPTERS_PATH, self._store_adapters)
        dump_json(BOTS_PATH, self._store_bots)
        dump_json(DRIVERS_PATH, self._store_drivers)
        dump_json(PLUGINS_PATH, list(plugins.values()))
        dump_json(RESULTS_PATH, results)
