# API 响应数据检查器

读取商品列表 JSON，检查缺失字段、类型错误、非法数值和重复商品编号。每个问题都包含字段路径、错误类型和原因，也可以导出 JSON 报告。

使用 Python 标准库，无第三方依赖。输入为本地模拟数据，不发送 HTTP 请求。

## 运行

需要 Python 3.10 或更高版本，在仓库根目录执行：

```powershell
python checker.py samples/valid.json
python checker.py samples/invalid.json
python checker.py samples/invalid.json --report report.json
python -m unittest discover -s tests -v
```

退出码 `0` 表示数据通过检查，`1` 表示发现规则问题，`2` 表示文件读取、JSON 解析或报告写入失败。`--report` 只创建新文件，已有报告不会被覆盖；重复执行需指定新的文件名。

## 输入与规则

```json
{"code":0,"data":{"items":[{"id":"SKU-001","name":"商品样例","price":29.9,"stock":2}]}}
```

| 字段 | 检查规则 |
| --- | --- |
| 根节点、data、每个商品 | 必须是对象 |
| code | 整数 0，不接受布尔值 |
| data.items | 数组，允许空数组 |
| id、name | 必填的非空白字符串 |
| id | 同一列表内唯一，按原字符串比较 |
| price | 有限、非负的数字，不接受布尔值 |
| stock | 非负整数，不接受浮点数或布尔值 |

缺失字段和 `null` 分开报告；允许额外字段，不修改输入。JSON 解析拒绝重复对象键以及非标准的 `NaN`、`Infinity`。结构错误会停止该分支的检查，但不影响其他可检查的商品。

## 输出示例

仓库中的异常样例包含六个预设问题：

```text
FAIL: 6 issue(s)
$.data.items[0].name [empty] must not be blank
$.data.items[0].price [value] must be non-negative
$.data.items[0].stock [type] expected an integer, not a boolean
$.data.items[1].id [duplicate] product id must be unique
$.data.items[1].price [type] expected a number, not a boolean
$.data.items[1].stock [missing] required field is missing
```

例如 `$.data.items[1].stock` 指第二个商品的库存字段。`true` 在 Python 中属于 `int` 的子类，库存规则因此使用精确类型检查，避免将布尔值误当整数。

## 文件与测试

```text
checker.py                    校验函数和命令行入口
samples/                      正常及异常 JSON
tests/test_checker.py         规则测试和命令行测试
scripts/record_validation.py  运行测试并记录结果与源码哈希
docs/TEST_REPORT.md           测试范围
evidence/                    测试日志和汇总
```

现有 30 项自动化测试通过，包含正常输入、边界值、异常 JSON、退出码和报告防覆盖检查。运行 `python scripts/record_validation.py` 可更新本地验证记录；该命令会覆盖 `evidence` 下的执行结果，不访问网络。

## 限制

只实现这一种商品列表结构的规则检查，不是通用 JSON Schema 工具，也不包含接口请求、鉴权、数据库或并发压测。输入一次性读入内存，未限制恶意大文件的资源消耗。价格只做数值合法性检查，不负责精确金额运算。测试结果仅适用于这些模拟样例和规则。
