# PyHFT

一个面向 `hft-common` 共享内存行情读取的 pybind 小项目。

当前功能：

- 通过 pybind 暴露 `ShmRingBufferReader`
- 读取 `CtpShmTickRecord` 行情
- 将 `poll()` 到的行情写入 parquet
- 读取 parquet 做回看验证
- 用 Python 标准库起一个最小实时展示网页

## 目录

- `src/bindings/shmringbuffer.cpp`: pybind 绑定
- `include/pyhft/ctp_shm_tick_record.h`: `CtpShmTickRecord` 本地镜像定义
- `third_party/hft-common`: `hft-common` 子模块
- `examples/read_shmringbuffer.py`: 终端持续读取示例
- `tools/poll_to_parquet.py`: 持续写 parquet
- `tools/read_parquet.py`: 读取 parquet 验证
- `tools/shm_web.py`: 最小网页展示

## 依赖

- Python 3
- CMake
- pybind11
- pyarrow

## 构建

```bash
cmake -S . -B build
cmake --build build -j
```

构建完成后，扩展模块输出到：

```text
bin/_shmringbuffer*.so
```

`compile_commands.json` 会生成在：

```text
build/compile_commands.json
```

## 读取 shm

终端持续读取：

```bash
python3 examples/read_shmringbuffer.py CTP_MD
```

当前输出关键字段：

- `symbol`
- `update_time`
- `last_price`
- `volume`
- `bid1 price/volume`
- `ask1 price/volume`

## 写 parquet

持续将 shm 行情写入 parquet：

```bash
python3 tools/poll_to_parquet.py CTP_MD tools/pq/test.parquet
```

停止时直接 `Ctrl+C`。

## 读 parquet

读取 parquet 并打印最后几条：

```bash
python3 tools/read_parquet.py tools/pq/test.parquet
```

## 网页展示

启动最小网页服务：

```bash
python3 tools/shm_web.py CTP_MD --port 8001
```

打开：

```text
http://127.0.0.1:8001
```

当前页面行为：

- 每个 `symbol` 只保留最新一条
- 同一个 `symbol` 的新 tick 会覆盖旧值
- 页面顺序固定按 `symbol` 排序

## 说明

- 当前 `ShmRingBufferReader.poll()` 返回的是 `list[dict]`
- 绑定的数据类型是 `CtpShmTickRecord`
- 如果 shm 名称不是 `CTP_MD`，把命令里的名字替换成实际值即可
