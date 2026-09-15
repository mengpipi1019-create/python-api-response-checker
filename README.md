# API 响应数据检查器

一个 Python 标准库实现的接口数据校验练习：读取**模拟商品列表 JSON 文件**，检查字段缺失、类型错误、非法数值及重复商品编号，并输出具体错误位置。

**项目性质：2026-09-15 新建的 AI 辅助个人实践 Demo。** 不访问任何公司的真实接口，不使用真实用户数据，不属于企业实习或生产系统。AI 用于需求拆解、代码和测试辅助，运行时不调用大模型。

快速浏览：[协作过程](docs/AI_COLLABORATION.md) · [验证记录](docs/TEST_REPORT.md) · [测试日志](evidence/unittest.txt)

## 为什么做这个

接口返回“成功”不代表数据一定正确。例如价格可能是负数、库存可能误写为布尔值。这个小工具把人工逐字段检查变成可重复执行的规则检查，作为测试开发方向的入门实践。

## 快速运行

使用 Python 3.10 或更高版本，无需安装第三方包。在项目目录执行：

```powershell
python checker.py samples/valid.json
python checker.py samples/invalid.json
python checker.py samples/invalid.json --report report.json
python -m unittest discover -s tests -v
```

正常样例输出 `PASS: 0 issue(s)`，退出码为 `0`。异常样例输出 `FAIL: 6 issue(s)`，退出码为 `1`，这是**检查成功发现问题**，不是程序崩溃。文件读取、JSON 解析或报告写入失败时退出码为 `2`。

`--report` 仅新建报告，不覆盖已有文件。再次执行请换一个尚不存在的报告名；输出目录需要事先存在。

## 输入约定

```json
{
  "code": 0,
  "data": {
    "items": [
      {"id": "SKU-001", "name": "模拟商品", "price": 29.9, "stock": 2}
    ]
  }
}
```

| 检查对象 | 规则 |
| --- | --- |
| 根节点、data、每个商品 | 必须是对象 |
| code | 整数 0，布尔值不能冒充整数 |
| data.items | 必须是数组；允许空数组 |
| id、name | 必填、字符串、不能全为空白 |
| id | 同一列表中不能完全相同；按原字符串区分大小写，不做清洗 |
| price | 必填、有限且非负的数字，不能是字符串或布尔值 |
| stock | 必填、非负整数，不能是浮点数或布尔值 |

缺失字段与 `null` 分开报告：前者为 `missing`，后者为类型错误。允许额外字段，不修改原始数据。JSON 解析拒绝重复对象键以及非标准的 `NaN`、`Infinity` 字面量。结构错误会在该层停止向下检查，但仍继续处理可检查的其他商品。

## 异常样例的真实输出

```text
FAIL: 6 issue(s)
$.data.items[0].name [empty] must not be blank
$.data.items[0].price [value] must be non-negative
$.data.items[0].stock [type] expected an integer, not a boolean
$.data.items[1].id [duplicate] product id must be unique
$.data.items[1].price [type] expected a number, not a boolean
$.data.items[1].stock [missing] required field is missing
```

`$.data.items[1].stock` 表示“第二个商品的库存字段”。输出既便于人定位，也能保存为 JSON 报告供后续脚本读取。

## 验证与结构

本次本地运行：**30 项测试通过，正常样例通过，异常样例定位 6 处预设问题**。这不是覆盖率、真实接口缺陷数或生产效果证明。

```text
checker.py                 校验函数与命令行入口
samples/                   正常、异常模拟数据
tests/test_checker.py      单元与命令行测试
scripts/record_validation.py  重跑测试并记录证据
docs/AI_COLLABORATION.md    AI 协作分工与表单描述
docs/TEST_REPORT.md        测试范围与局限
evidence/                  自动生成的执行日志和机器可读结果
```

证据可用 `python scripts/record_validation.py` 重新生成。脚本会更新本项目 `evidence` 下的验证结果，不访问网络。

## 边界

- 只校验本地文件，不发送 HTTP 请求，不是完整接口自动化平台。
- 规则针对这一种模拟商品列表，不是通用 JSON Schema 实现。
- 不包含鉴权、数据库断言、并发/性能测试、CI 集成或线上部署。
- 价格使用普通 JSON 数值做合法性检查，不负责精确金额计算。
- 一次性读入文件；未做大文件/恶意输入的资源限制，不应作为不可信上传服务直接上线。
- 没有真实业务中的效率提升或故障减少数据。

项目可用于展示一次真实的 AI 协作实践；独立复现、修改规则和解释代码需要另行练习，不能仅凭生成的代码宣称已独立掌握。
