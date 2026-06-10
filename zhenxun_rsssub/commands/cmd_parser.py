from arclet.alconna import Alconna, Args, MultiVar, Option, Subcommand

alconna = Alconna(
    "订阅姬",
    Subcommand(
        "添加",
        Args["name", str]["url?", str],
        Option("-g|--group", Args["group_id", str]),
    ),
    Subcommand(
        "删除",
        Args["names", MultiVar(str)],
        Option("-g|--group", Args["group_id", str]),
    ),
    Subcommand("彻底删除", Args["names", MultiVar(str)]),
    Subcommand("列表", Option("-g|--group", Args["group_id", str])),
    Subcommand(
        "详情",
        Args["name", str],
        Option("-g|--group", Args["group_id", str]),
    ),
    Subcommand(
        "设置",
        Args["name", str]["options", MultiVar(str)],
        Option("-g|--group", Args["group_id", str]),
    ),
    Subcommand(
        "测试",
        Args["name", str],
        Option("-g|--group", Args["group_id", str]),
    ),
    Subcommand(
        "拉取",
        Args["name", str],
        Option("-g|--group", Args["group_id", str]),
    ),
    Subcommand(
        "状态",
        Args["name?", str],
        Option("-g|--group", Args["group_id", str]),
    ),
    Subcommand(
        "导出",
        Args["name?", str]["options?", MultiVar(str)],
        Option("-g|--group", Args["group_id", str]),
    ),
    Subcommand("导入", Args["data", MultiVar(str)]),
)

config_alconna = Alconna(
    "订阅姬",
    Subcommand("配置", Args["options?", MultiVar(str)]),
)
