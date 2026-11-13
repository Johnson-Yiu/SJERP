# SEC1 既有候选来源矩阵

范围沿用原扫描的 13 个数据库路径、10 个数据库对象和 117 处连接串候选。相同连接串对象按行归类，若存在多条路径则分别列出，路径重复不增加去重计数。数据库检查使用仓库外只读副本。

按 blob 和行去重统计：隔离测试动态模板 48 处、待资料责任方确认 31 处、合成单测输入 36 处、明确占位 2 处。

| 路径 | Git blob | 行 | 分类 | 依据 | 处置 |
| --- | --- | --- | --- | --- | --- |
| docs/uat-evidence/party-version-closeout-02/logs/quote-inheritance-e2e-pg/run_owned.py | 061aa5eaaadaba503a7c9593ad3068c49171bf96 | 51 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| .github/workflows/ci.yml | 066b94a4045e928481fa364c1a62854d31f5c270 | 47 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| backend/crm/tests/test_database_settings.py | 0972bfbde4a8e0dba9df8b86bb0b6b99f3d63c58 | 76,79,82,99,133,142,151,160,169,178,187,195 | 合成单测输入 | 数据库配置解析测试中的字面输入，作用域为单测。 | 保留单测。 |
| backend/environment.example | 0c9fd9c38bfe6faaab35b3659d132ce3bc36cf8d | 20 | 明确占位 | 部署环境示例对象，匹配包含示例替换标记。 | 保留示例。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/pg17-final-source-retry/run_owned.py | 10996643bb0fa69235a6891822a6570f5bdc2853 | 61 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/pg17-final-source-validation/run_owned.py | 10996643bb0fa69235a6891822a6570f5bdc2853 | 61 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/pg17-final-after-so-country/run_owned.py | 10d4f1105384f1ad20c147bb645a33963fdbdaf4 | 61 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/pg17-final-frozen-source/run_owned.py | 10d4f1105384f1ad20c147bb645a33963fdbdaf4 | 61 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/pg17-final-stable-source/run_owned.py | 10d4f1105384f1ad20c147bb645a33963fdbdaf4 | 61 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-02/logs/quote-inheritance-pg/run_owned.py | 11faefd5df1bad6b3302c060746aba041171e731 | 51 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-02/logs/party-details-draft-pg-final/run_owned.py | 2134d1ebdb2929e040cd698454c2e6a257c2a524 | 51 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-02/logs/party-details-draft-pg-identity/run_owned.py | 2134d1ebdb2929e040cd698454c2e6a257c2a524 | 51 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-02/logs/party-details-draft-pg-retest/run_owned.py | 2134d1ebdb2929e040cd698454c2e6a257c2a524 | 51 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-02/logs/party-details-draft-pg/run_owned.py | 2134d1ebdb2929e040cd698454c2e6a257c2a524 | 51 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/quote-approval-guard-pg17/run_owned.py | 29b0856357c863ae24b4118837566f6da6da2d4b | 51 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-03/logs/pg17-final/run_owned.py | 2c6d51a0968a42eeee798d5f0abce0c29d0b985b | 62 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-03/logs/pg17/run_owned.py | 2c6d51a0968a42eeee798d5f0abce0c29d0b985b | 62 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| .github/workflows/ci.yml | 31cd23a4cf7e3d2bd735690fef2609c7d32028ed | 47 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/party-version-closeout-02/logs/pg17-final-prepared/run_owned.py | 36e57c916dea95fa4c3c7b007c4b4c9ca9443cf6 | 62 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-02/logs/pg17-final-retry/run_owned.py | 36e57c916dea95fa4c3c7b007c4b4c9ca9443cf6 | 62 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-02/logs/pg17-final-retry2/run_owned.py | 36e57c916dea95fa4c3c7b007c4b4c9ca9443cf6 | 62 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-02/logs/pg17-final-retry3/run_owned.py | 36e57c916dea95fa4c3c7b007c4b4c9ca9443cf6 | 62 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/run_owned.py | 3c74a8d6f154cfe02c565a3289fe80702884eaec | 47 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| README.md | 46460aa17fb0514bbc56194782704ba42ea9f569 | 68 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/sales-order-import-20261106/run-postgres.py | 49b46ddaafb59e3b6a133d35dae7849835376670 | 102 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-02/logs/pg17-lifecycle-exploratory-02/run_owned.py | 4ad56bcc246aae2bccea78e3bcfceddf93838452 | 61 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/ISS-051-环境隔离与部署配置.md | 4e6a5f8c61dfe3b6ce864e13a11bdf02e62d3c94 | 19 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/party-version-closeout-02/logs/quote-details-approval-pg/run_owned.py | 60ae82cd9614cebdabbea62cb760deccbb25e1f5 | 51 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| .github/workflows/ci.yml | 618f421d03fc138492bea2295376c67f78dd8503 | 47 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| README.md | 620f6bdb973df59e28943cbd35b304b82882f88d | 71 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/pg312-final/run_owned.py | 63bd554c9d556e8681c352655bf39566fa7c99cb | 51,54,58,67 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| .github/workflows/ci.yml | 6aea1e960c314fb3605df82b1e674b6871f0fbc3 | 47 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/party-int01/upgrade-run_upgrade.py | 6d09588c1c93d3333902f3b654d686800b6ccc9f | 62 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| README.md | 740bab6d560a64ae4225c2fe08aa00e528fb0ce4 | 86 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/final-tax-corrected/run_owned.py | 7d410f095a3b7c79aab420f6313697fffbeeeb42 | 49,52,64 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/access-readiness-20261105/run_postgres.py | 80ff51acccf04f7b1279d17ae26f9e6b73df5bfa | 39 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| backend/environment.example | 8384ee75a7643b011e2cccadc8999e5c7e113d0e | 18 | 明确占位 | 部署环境示例对象，匹配包含示例替换标记。 | 保留示例。 |
| backend/crm/tests/test_database_settings.py | 88d1490eee38bd866556379dd41821bbdc2ffc8b | 53,56,59 | 合成单测输入 | 数据库配置解析测试中的字面输入，作用域为单测。 | 保留单测。 |
| README.md | 8a05708b4d8e3f52177f3f1ad8944148efefb0e8 | 69 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| backend/crm/tests/test_database_settings.py | 8a96553ade62cfd7ca147d4d90022386bdad53ec | 75,78,81,98,132,141,150,159,168,177,186,194 | 合成单测输入 | 数据库配置解析测试中的字面输入，作用域为单测。 | 保留单测。 |
| README.md | 8ac013495fc2e017e95dcba5cd9e3267c943d076 | 68 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/r1-candidate-regression-20261029/backend-full-test-first.log | 8cd84d6d10e2a18bce75d30ede6b5afba904a6c2 | 874,943 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/party-version-closeout-02/logs/party-details-0116-pg-final/run_owned.py | 9b7d2cf8bcae5b655d49d2f39aaaedbc6f924bd2 | 51 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-02/logs/party-details-0116-pg/run_owned.py | 9b7d2cf8bcae5b655d49d2f39aaaedbc6f924bd2 | 51 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/pg312-legacy-tax-final/run_owned.py | 9dbfd725d94b0582dff9abb187e0300f6bccd660 | 51 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/pg312-legacy-tax/run_owned.py | 9dbfd725d94b0582dff9abb187e0300f6bccd660 | 51 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| .github/workflows/ci.yml | a1a66d2dc282bdcb401946c8429b367d98578388 | 47 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/final/run_owned.py | a368e78efbd8d4500a83a9e7ceeed8009fea8df3 | 49,52,64 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/access-readiness-20261105/run_postgres-access-source.py.txt | a9c76661d4c16a57f6ae47d4160b4707b8aefdf5 | 42 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/history-product-sku-linking-01/run-postgres.py | af3c494a29f4cd43d84664142dabbf8547bf75b9 | 28 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| README.md | b1dc5baf64d964f76d34b16c8257172a00632288 | 88 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/party-version-closeout-02/logs/pg17-lifecycle-01/run_owned.py | b3a371a646fc59a1acacbfecd60e69a5932892aa | 61 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/access-readiness-20261105/run_postgres.py | b8fde7d9b195a36d40e940ca8f6996a131872e0e | 38 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| README.md | b9f6f45c2ae4555c1a6af08dd4406b733dd8b837 | 53 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| backend/crm/tests/test_database_settings.py | bcc0a98fe1a07ad77f5eeafa808fc3713b2648de | 71,74,77,94,128,137,146,155,163 | 合成单测输入 | 数据库配置解析测试中的字面输入，作用域为单测。 | 保留单测。 |
| .github/workflows/ci.yml | be2d5465688803ab2a111922587f0fd3f6a5fa55 | 47 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/party-int01/run_postgres.py | bf35002204383d748dc0a7ec4b3287ea92e76892 | 62 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/concurrency/run_owned.py | c476ce677d62e1ec1e300f7c9c6fd8e56d3c450f | 49,52,64 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| README.md | c6bca0c515ff6d023779bb3a4cf69b7ef0bfd9ed | 61 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/pg17-final-all-source-stable/run_owned.py | c8a57193f2b2cd7e2bb7220ae239decae93514e9 | 61 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/pg17-final-draft-tax-stable/run_owned.py | c8a57193f2b2cd7e2bb7220ae239decae93514e9 | 61 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/r1-iss018-postgres-boundary-20261102/README.md | c8caf7a995979ebbb5216b4581bde1c3a5f169e5 | 41 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| README.md | c9f08ab9f484cff9f6753b963e9c493c4bd6b672 | 88 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| .github/workflows/ci.yml | ccff93db07d0d37dfb7dc3ccf6f0d68178407cc4 | 47 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/final-tax/run_owned.py | d2ebcb7b9519518799023478cec3c6230732ddd6 | 49,52,64 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/access-readiness-20261105/run_postgres.py | d51a99e37f0299a6af38e11dc1abf89cc9c13811 | 39 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-int01/snapshot-upgrade-run_upgrade.py | d95c456ae9b3748565bb9955931345b7f8a2fe6c | 62 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-02/logs/party-details-approval-pg/run_owned.py | e55e65cf1d916113de224d51e28d6ffb4ec33964 | 51 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| README.md | e5b9a8c89625557cd6e24e4de0cff7bf502f445c | 86 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| .github/workflows/ci.yml | e6bf78804165482ba42b1109d17fc10659e470cb | 47 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| README.md | e72931075532f6716d5699765d618747bfbbdac6 | 71 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| .github/workflows/ci.yml | e9bee72414c92ec78a685f981e0eb1b59322b1ae | 47 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| README.md | eadab3f68c64c7630849af86a358b3a07cbdcce1 | 68 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| .github/workflows/ci.yml | ebbe64391d6a49279678948025296561c1681953 | 47 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/pg312-followup/run_owned.py | f18b68e2548f7b5a6271b0e67f40bf999a0c4167 | 51,54,58,68 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-20261105/logs/draft-tax-revision/pg/run_owned.py | f2703e5b9af2e87a17f9e9b0478f4ac8584b38f8 | 51 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| README.md | f5e0e8dee82db8026c2877205cf3d89000933a65 | 70 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/history-product-sku-linking-01/run-postgres.py | fac01b4eb3671049f367378193c808d1b8c17414 | 26 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| docs/uat-evidence/party-version-closeout-02/logs/pg17-final-01/run_owned.py | fdb00b27cd57177364a3d0bf3f9e98b891d7b6c3 | 61 | 隔离测试动态模板 | 连接串为运行期插值；同一对象含本地 initdb、pg_ctl 与随机凭据生成逻辑。公开匹配为源码模板。 | 保留模板。 |
| .github/workflows/ci.yml | fdfe1c1ac0c220cc1143d661fad753443cf90c08 | 47 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| .github/workflows/ci.yml | ff04aa8d109d1d0b7018cc946aa2b63ad6dbb45d | 47 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/r1-integration-iss006-052-ux-pw-auth/logs/backend-full-first-attempt.log | ff749dd2cfd7b73f2366939bbddcb5f1c3932376 | 879,948 | 待资料责任方确认 | 当前证据不足以证明该行的口令来源及适用环境。 | 确认生成或配置来源、服务是否仍可达及是否复用。若真实或复用，授权撤销和历史处置。 |
| docs/uat-evidence/export-stability-closeout-20261105/quote-save-export-interrupt-diagnostic/run-1/synthetic.sqlite3 | 4084d0583509df3f2f77bd777bc093c2ad0dd42b | 数据库文件 | 待资料责任方确认 | SQLite 只读核对有业务表记录。 未找到同目录生成清单。 | 提供本次运行输入来源及对象对应，确认无真实业务导入。保留原证据，暂不例外。 |
| docs/uat-evidence/export-stability-closeout-20261105/quote-save-export-interrupt-diagnostic/run-2/synthetic.sqlite3 | 5cb48c42ae8e5be5f037d8ca247493eb8f26be8e | 数据库文件 | 待资料责任方确认 | SQLite 只读核对有业务表记录。 未找到同目录生成清单。 | 提供本次运行输入来源及对象对应，确认无真实业务导入。保留原证据，暂不例外。 |
| docs/uat-evidence/export-stability-closeout-20261105/finance/django609-rerun/ledger/isolated.sqlite3 | 640d250f6e180d8a25d6aee3cfebb4c59cdd3d7d | 数据库文件 | 待资料责任方确认 | SQLite 只读核对有业务表记录。 同目录来源线索：docs/uat-evidence/export-stability-closeout-20261105/finance/django609-rerun/ledger/seed.py。 | 提供本次运行输入来源及对象对应，确认无真实业务导入。保留原证据，暂不例外。 |
| docs/uat-evidence/export-stability-closeout-20261105/packing/isolated.sqlite3 | 698a8948f156ef3d585feff2bdd8e1927b5b6960 | 数据库文件 | 待资料责任方确认 | SQLite 只读核对有业务表记录。 同目录来源线索：docs/uat-evidence/export-stability-closeout-20261105/packing/README.md, docs/uat-evidence/export-stability-closeout-20261105/packing/seed.py, docs/uat-evidence/export-stability-closeout-20261105/packing/test-logs-manifest.json。 | 提供本次运行输入来源及对象对应，确认无真实业务导入。保留原证据，暂不例外。 |
| docs/uat-evidence/export-stability-closeout-20261105/python312-http-recheck-20261105/packing-390/synthetic.sqlite3 | 698a8948f156ef3d585feff2bdd8e1927b5b6960 | 数据库文件 | 待资料责任方确认 | SQLite 只读核对有业务表记录。 同目录来源线索：docs/uat-evidence/export-stability-closeout-20261105/python312-http-recheck-20261105/packing-390/README.md。 | 提供本次运行输入来源及对象对应，确认无真实业务导入。保留原证据，暂不例外。 |
| docs/uat-evidence/export-stability-closeout-20261105/python312-http-recheck-20261105/packing/synthetic.sqlite3 | 698a8948f156ef3d585feff2bdd8e1927b5b6960 | 数据库文件 | 待资料责任方确认 | SQLite 只读核对有业务表记录。 未找到同目录生成清单。 | 提供本次运行输入来源及对象对应，确认无真实业务导入。保留原证据，暂不例外。 |
| docs/uat-evidence/export-stability-closeout-20261105/finance/real-django-chrome/legal-api.sqlite3 | c206aea6df942f7d797de14e309e13f2572a479f | 数据库文件 | 待资料责任方确认 | SQLite 只读核对有业务表记录。 同目录来源线索：docs/uat-evidence/export-stability-closeout-20261105/finance/real-django-chrome/README.md, docs/uat-evidence/export-stability-closeout-20261105/finance/real-django-chrome/seed-api.py, docs/uat-evidence/export-stability-closeout-20261105/finance/real-django-chrome/seed.py。 | 提供本次运行输入来源及对象对应，确认无真实业务导入。保留原证据，暂不例外。 |
| docs/uat-evidence/export-stability-closeout-20261105/python312-http-recheck-20261105/quote/synthetic.sqlite3 | dacb3b15990f926cc1ee6a706e6293d42874ebb0 | 数据库文件 | 待资料责任方确认 | SQLite 只读核对有业务表记录。 未找到同目录生成清单。 | 提供本次运行输入来源及对象对应，确认无真实业务导入。保留原证据，暂不例外。 |
| docs/uat-evidence/export-stability-closeout-20261105/quote-http-byte-control/synthetic.sqlite3 | dacb3b15990f926cc1ee6a706e6293d42874ebb0 | 数据库文件 | 待资料责任方确认 | SQLite 只读核对有业务表记录。 同目录来源线索：docs/uat-evidence/export-stability-closeout-20261105/quote-http-byte-control/README.md, docs/uat-evidence/export-stability-closeout-20261105/quote-http-byte-control/seed.py。 | 提供本次运行输入来源及对象对应，确认无真实业务导入。保留原证据，暂不例外。 |
| docs/uat-evidence/export-stability-closeout-20261105/finance/ledger-chrome/isolated.sqlite3 | e71f6c5b63e5c1ffa3015ad11a68ce32d9526862 | 数据库文件 | 待资料责任方确认 | SQLite 只读核对有业务表记录。 同目录来源线索：docs/uat-evidence/export-stability-closeout-20261105/finance/ledger-chrome/README.md, docs/uat-evidence/export-stability-closeout-20261105/finance/ledger-chrome/seed.py。 | 提供本次运行输入来源及对象对应，确认无真实业务导入。保留原证据，暂不例外。 |
| docs/uat-evidence/integration-closeout-02/final-02140bf-history-chrome/artifacts/isolated-sanitized.sqlite3 | ea7d1fca280905ed3de2bc6e12e626a625f3d4c2 | 数据库文件 | 待资料责任方确认 | SQLite 只读核对有业务表记录。 未找到同目录生成清单。 | 提供本次运行输入来源及对象对应，确认无真实业务导入。保留原证据，暂不例外。 |
| docs/uat-evidence/export-stability-closeout-20261105/quote-save-export-interrupt-diagnostic/run-3/synthetic.sqlite3 | f5455104c0efc6686d33f4d5a3a93db480cb58d6 | 数据库文件 | 待资料责任方确认 | SQLite 只读核对有业务表记录。 未找到同目录生成清单。 | 提供本次运行输入来源及对象对应，确认无真实业务导入。保留原证据，暂不例外。 |
| docs/uat-evidence/export-stability-closeout-20261105/finance/django609-rerun/dashboard/isolated.sqlite3 | fabccce5424e3100851ab54907275869029e5267 | 数据库文件 | 待资料责任方确认 | SQLite 只读核对有业务表记录。 同目录来源线索：docs/uat-evidence/export-stability-closeout-20261105/finance/django609-rerun/dashboard/seed-api.py。 | 提供本次运行输入来源及对象对应，确认无真实业务导入。保留原证据，暂不例外。 |

## 集成方接线

在取得 BASE 和 HEAD 及完整范围历史后，从仓库运行 `python -m unittest discover -s scripts -p test_check_public_delivery.py`，再运行 `python scripts/check_public_delivery.py --range BASE_SHA..HEAD_SHA`。两步均保留非零退出码。范围通过只说明该增量通过检查。待决行独立追踪，无数据库例外。无须上传原始命中。
