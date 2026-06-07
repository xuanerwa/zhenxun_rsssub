from arclet.alconna import Alconna, Args, MultiVar, Subcommand

alconna = Alconna(
    "订阅姬",
    Subcommand("添加", Args["name", str]["url", str]),
    Subcommand("删除", Args["names", MultiVar(str)]),
    Subcommand("列表"),
    Subcommand("详情", Args["name", str]),
    Subcommand("设置", Args["name", str]["options", MultiVar(str)]),
    Subcommand("测试", Args["name", str]),
    Subcommand("拉取", Args["name", str]),
    Subcommand("状态", Args["name?", str]),
    Subcommand("导出", Args["name?", str]["options?", MultiVar(str)]),
    Subcommand("导入", Args["data", MultiVar(str)]),
)
