# 🧵 SewSource

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## 📖 Overview

SewSource is a powerful command-line interface (CLI) tool that helps you aggregate documentation files from GitHub repositories. It clones repositories, combines specified documentation files, and creates a unified source perfect for interactive Learning Language Model (LLM) discussions using tools like NotebookLM.
<!-- mtoc-start -->

* [🚀 Installation](#-installation)
* [🛠️ Usage](#-usage)
  * [Basic Command](#basic-command)
  * [Advanced Usage with Options](#advanced-usage-with-options)
* [📋 Command Options](#-command-options)
* [💡 Examples](#-examples)
  * [1. Basic Repository Aggregation](#1-basic-repository-aggregation)
  * [2. Specific Documentation Directories](#2-specific-documentation-directories)
  * [3. Excluding Certain Content](#3-excluding-certain-content)
* [⚠️ Common Issues and Solutions](#-common-issues-and-solutions)
* [Next TODOs](#next-todos)
* [🤝 Contributing](#-contributing)
* [📄 License](#-license)

<!-- mtoc-end -->
## 🚀 Installation

```bash
pip install sewsource
```

## 🛠️ Usage

### Basic Command

```bash
sewsource https://github.com/username/repository
```

### Advanced Usage with Options

```bash
sewsource https://github.com/username/repository \
    --output-dir "./docs_combined" \
    --include-dirs "docs,wiki" \
    --exclude-dirs "tests" \
    --blacklist "README.md,CHANGELOG.md" \
    --extensions ".md,.rst,.txt"
```

## 📋 Command Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--output-dir` | `-o` | Output directory for combined files | `~/.sewsource` |
| `--include-dirs` | `-i` | Directories to include | All directories |
| `--exclude-dirs` | `-x` | Directories to exclude | None |
| `--blacklist` | `-b` | Files to exclude | None |
| `--extensions` | `-e` | File extensions to include | `.md, .mdx` |
| `--version` | - | Show version information | - |
| `--help` | - | Show help message | - |

## 💡 Examples

### 1. Basic Repository Aggregation

```bash
sewsource https://github.com/tensorflow/tensorflow
```

### 2. Specific Documentation Directories

```bash
sewsource https://github.com/pytorch/pytorch \
    --include-dirs "docs" -i "tutorials" \
    --extensions ".md" -e ".rst"
```

### 3. Excluding Certain Content

```bash
sewsource https://github.com/kubernetes/kubernetes \
    --exclude-dirs "vendor" -x "test" \
    --blacklist "CONTRIBUTING.md"
```

## ⚠️ Common Issues and Solutions

* **Large Repositories**

   ```bash
   # For large repos, use specific directories
   sewsource https://github.com/large/repo --include-dirs "docs"
   ```

## Next TODOs

* [ ] Add support for comma separated values as arguments for multiple folders/files

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
