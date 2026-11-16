# GreenTokens：先完成 BERT-Tiny 单机 CPU 微调

这是 GreenTokens 的独立单机 CPU 训练示例，支持 Apple Silicon Mac（包括 M4）和常见
Intel/AMD Windows 电脑。后续训练实验目标是三台真实电脑，区别于平台原有的四机里程碑。

从仓库根目录先运行 `cd examples/bert_tiny_cpu`，然后按以下步骤操作。
该示例尚未接入客户页面、`POST /v1/jobs`、MySQL 或 S3；现有 API 仍只支持 `sum_numbers_v1`。

这是单机基线脚本，不是已经完成的三机分布式训练。脚本强制使用 CPU，
包括在 Apple Silicon Mac 上禁用对 MPS 的自动选择。仅进行了语法和 CLI 检查，
尚未在你的硬件上安装依赖、下载模型或运行训练。

## 1. 下载文件并安装

在本示例文件夹中打开终端；依赖安装在本目录的独立 `.venv`，不使用后端的虚拟环境。
建议使用 Python 3.11。以下 Mac 命令面向 Apple Silicon；如果是 Intel Mac，
先提供芯片与 macOS 版本，较新的 PyTorch 没有相同的 Intel Mac wheel 支持，
不要直接降级到不能安全加载旧模型权重的版本。

macOS（Apple Silicon；先安装 Python 3.11，以下命令明确使用该版本）：

```bash
python3.11 --version
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install 'torch>=2.6,<3'
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python train_bert_tiny.py
```

如果 `python3.11` 显示 command not found，请先从 https://www.python.org/downloads/macos/
安装 Python 3.11；无需删除或替换现有 Python。这里明确指定 `python3.11`，
避免意外使用系统中的另一个版本。

Windows PowerShell（常见 Intel/AMD 64 位 Windows；先安装 Python 3.11）：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install "torch>=2.6,<3" --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe train_bert_tiny.py
```

无需激活虚拟环境，所以 Windows 无需修改 PowerShell 的脚本执行策略。
模型和数据首次下载需要能访问 Hugging Face。若下载失败，保留完整报错以便定位。
出现 classifier 参数新初始化的提示是正常的：二分类层正是本次要训练的部分。

## 2. 训练设置和结果

- 模型：prajjwal1/bert-tiny；任务：英文情感二分类。
- 训练样本：固定种子抽取 999 条（约 1,000 条，可被未来的三个 worker 均分）。
- 3 个 epoch；全局 batch size 24；最大长度 128；CPU 线程 2。
- 验证集：SST-2 validation；不把验证数据用于训练。
- 完成后保存模型、分词器和 metrics.json；再从磁盘重新加载模型，预测一句话。
- 预测和验证准确率均为实际计算值；不保证某句话一定预测正确。
- 保存的是可用于推理的模型检查点，不含用于精确恢复训练的优化器状态。

脚本输出 `COMPLETE` 后，检查新生成的 `bert-tiny-sst2-cpu` 文件夹。
`metrics.json` 包含训练循环耗时、包含下载等操作的总耗时、CPU 时间、主机名、
验证准确率、实际依赖版本和预测结果。CPU 百分比以一个逻辑核满载为 100%，可能超过 100%。

已有输出不会被覆盖。重跑时指定新目录，例如：

```bash
.venv/bin/python train_bert_tiny.py --output bert-tiny-run2
```

Windows 使用对应的 `.\.venv\Scripts\python.exe`。
若要做更短的安装检查，可添加 `--examples 30 --epochs 1 --output smoke-test`；
这不能替代正式的 999 条样本基线。

## 3. Windows + macOS + 校园网如何做三机训练

Ray 官方只支持 Linux 多节点集群；原生 Windows/macOS 多节点属于实验性路径。
建议先成功完成上面的单机步骤，再确定每台真实电脑的 Linux 运行环境：
Windows 可考虑 WSL2/Linux 虚拟机，Mac 可考虑与芯片架构匹配的 Linux 虚拟机。
虚拟机/WSL2 并不自动解决网络问题，仍要确认三个 Linux 实例能双向访问需要的端口。
每台物理电脑运行一个训练节点，不能把三个虚拟机都放在一台电脑上当成三机证据。

连接同一个校园网不保证设备之间可以互相访问；可能存在设备隔离、防火墙或不同网段。
使用学校允许的私有网络连接方式，并限制 Ray 服务仅供这三台已授权电脑访问。
不需要为单机训练开放任何网络监听端口。

下一阶段需要确认：三台电脑分别是什么系统、芯片和内存；能否安装 Linux 环境；
网络是否允许三台训练节点互通。确认后再生成实际 IP、端口和存储配置对应的启动命令。
最终用 Ray Train 启动三个 worker、每台一个，以 Gloo 同步梯度。
单机与三机比较时固定数据、epoch、全局 batch、学习率和文本长度；
三机可用每 worker batch 8。若改为 Linux 环境，应该在同一环境重新测单机基线。

## 参考

- 模型：https://huggingface.co/prajjwal1/bert-tiny
- 数据：https://huggingface.co/datasets/stanfordnlp/sst2
- PyTorch 安装：https://pytorch.org/get-started/locally/
- Ray 平台支持：https://docs.ray.io/en/latest/cluster/getting-started.html
- Ray PyTorch 教程：https://docs.ray.io/en/latest/train/getting-started-pytorch.html
- 已查阅的 Ray 官方示例：https://github.com/ray-project/ray/blob/master/python/ray/train/examples/pytorch/torch_quick_start.py

本脚本的单机训练部分使用标准 PyTorch 循环和 Transformers 模型接口；
后续的分片与同步应复用 Ray/PyTorch 提供的能力，不自行实现分布式训练协议。

## 提交与结果共享

模型权重、虚拟环境和训练输出不要提交到 Git。请在本目录运行命令；本目录的 `.gitignore`
已排除默认输出、常见训练产物和虚拟环境。分享运行结果前检查 `metrics.json` 中的主机名、
绝对路径和示例句子，仅向需要这些信息的队友分享。依赖当前是版本范围，不是锁定文件；
首次成功后保存 `pip freeze` 输出，三机环境应统一版本并重新测试。
