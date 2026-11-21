# dirsum

[![CI](https://github.com/Ecishy/dirsum/actions/workflows/ci.yml/badge.svg)](https://github.com/Ecishy/dirsum/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**See what is eating your disk: size by extension, largest files, per-folder rollup.**
One command, no dependencies, nothing installed on your system. Pure standard library.

```
$ dirsum ~/Projects/webapp
Scanned C:\Users\you\Projects\webapp
1,842 files, 213 folders, 1.4 GiB total

By extension:
    812.3 MiB     456  .jpg
    214.9 MiB      12  .mp4
    101.2 MiB     389  .js
    ...

Largest 10 file(s):
    88.0 MiB  assets/promo.mp4
    61.2 MiB  assets/gallery.zip
    ...

$ dirsum ~/Projects/webapp --dirs
First-level folders:
    990.5 MiB  1,102  assets
    310.1 MiB    505  src
      ...
```

## Features

- **By extension** — which file types dominate, with counts and bytes
- **Largest N files** — find the one video you forgot about (`--top N`, `0` disables)
- **First-level rollup** — `--dirs` shows which subfolder is the heavy one
- **`--json`** for scripts and dashboards
- `--exclude` fnmatch patterns (`build/*`, `node_modules`)
- Symlinks and Windows junctions are ignored so nothing is double-counted
- Everything stays read-only — dirsum never writes or deletes anything

## Install

```bash
pip install .
# or run straight from the source tree:
python -m dirsum ~/Projects
```

## Usage

```
dirsum [PATH] [options]

  -e, --exclude PAT    skip fnmatch pattern like '*.tmp' or 'build/*' (repeatable)
  -t, --top N          largest N files to list (default: 10, 0 disables)
  --dirs               add a first-level folder breakdown
  -j, --json           machine-readable output
  --follow-symlinks    descend into symlinked directories
  -V, --version        print version
```

**Exit codes:** `0` — finished; `2` — usage or I/O error.

## Use as a library

```python
from dirsum import collect, by_extension, top_files

files, dirs = collect("Downloads", exclude=("*.tmp",))
for ext, (count, size) in by_extension(files).items():
    print(f"{ext:>10}: {count} files, {size:,} bytes")
```

## 中文说明

`dirsum` 是一个零依赖的目录体积统计命令行工具（Python 3.9+ 标准库实现），回答三个问题：

1. **什么文件类型占了空间**——按扩展名聚合文件数与字节数，从大到小排序
2. **哪几个文件最大**——`--top N` 列出最大的 N 个文件
3. **哪个子文件夹最重**——`--dirs` 给出第一层子目录的体积汇总

- 只读不写，绝不修改任何文件；符号链接与 Windows 目录联接自动跳过，不会重复统计
- 支持 `--exclude` 过滤（如 `node_modules`）、`--json` 供脚本使用

```bash
dirsum ~/Projects                # 总览
dirsum ~/Downloads --top 20      # 找出最大的 20 个文件
dirsum D:/ --dirs --exclude 'Windows/*'   # 看哪个目录最占空间
```

## Development

```bash
pip install .
python -m unittest discover -s tests -v   # stdlib only
```

CI runs the same suite on Linux / macOS / Windows across Python 3.9–3.13.

## License

[MIT](LICENSE) © Ecishy
