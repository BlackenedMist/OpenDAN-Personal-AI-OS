# OpenDAN 多包项目结构

本项目采用多包架构，包含三个主要组件：

## 项目结构

```
OpenDAN/
├── pyproject.toml              # 主包配置 (opendan 框架)
├── src/
│   ├── opendan/               # 核心框架库
│   │   ├── pyproject.toml     # 框架包配置
│   │   └── opendan/           # 框架源码
│   ├── agents/
│   │   └── jarvis/            # Jarvis Agent 示例
│   │       ├── pyproject.toml # Agent 包配置
│   │       └── jarvis.py      # Agent 实现
│   └── services/              # 多 Agent 服务
│       ├── pyproject.toml     # 服务包配置
│       └── services/          # 服务源码
├── test/                      # 测试目录
├── build_all.py               # 构建脚本
└── Makefile                   # 开发工具
```

## 包说明

### 1. opendan (核心框架)
- **包名**: `opendan`
- **用途**: 被其他项目 import 的框架库
- **安装**: `pip install -e src/opendan`
- **构建**: `cd src/opendan && python -m hatch build`

### 2. opendan-jarvis (Agent 示例)
- **包名**: `opendan-jarvis`
- **用途**: 基于 opendan 编写的独立运行 Agent 示例
- **依赖**: `opendan>=0.1.0`
- **安装**: `pip install -e src/agents/jarvis`
- **运行**: `jarvis` (通过 entry point)

### 3. opendan-services (多 Agent 服务)
- **包名**: `opendan-services`
- **用途**: 基于 opendan 构建的多 Agent 服务
- **依赖**: `opendan>=0.1.0`, `redis`, `sqlalchemy`
- **安装**: `pip install -e src/services`
- **运行**: `opendan-services` (通过 entry point)

## 开发工作流

### 快速开始

```bash
# 安装所有包（开发模式）
make install-dev

# 运行测试
make test

# 代码格式化和检查
make format
make lint

# 构建所有包
make build-all
```

### 常用命令

```bash
# 查看所有可用命令
make help

# 开发环境完整设置
make dev-install

# 运行完整开发检查
make dev-test

# 清理构建产物
make clean
```

### 单独开发某个包

```bash
# 只安装框架
pip install -e src/opendan

# 只安装 jarvis
pip install -e src/agents/jarvis

# 只安装 services
pip install -e src/services
```

## 测试

测试文件位于 `test/` 目录，使用 pytest：

```bash
# 运行所有测试
pytest test/

# 运行特定包的测试
pytest test/ -k "jarvis"
pytest test/ -k "services"

# 带覆盖率报告
pytest test/ --cov=src --cov-report=html
```

## 发布

### 构建所有包
```bash
python build_all.py
```

### 发布（先测试）
```bash
# 干运行发布
python build_all.py --publish --dry-run

# 实际发布
python build_all.py --publish
```

### 单独发布某个包
```bash
cd src/opendan && python -m hatch publish
cd src/agents/jarvis && python -m hatch publish
cd src/services && python -m hatch publish
```

## 依赖管理

- 每个包都有自己的 `pyproject.toml`
- 主包包含所有运行时依赖
- 子包只包含自己特有的依赖
- 开发依赖在每个包中单独定义

## 注意事项

1. **版本同步**: 发布时注意同步所有包的版本号
2. **依赖关系**: jarvis 和 services 都依赖 opendan，发布顺序很重要
3. **测试覆盖**: 确保每个包都有对应的测试
4. **文档更新**: 更新各包的 README 和文档

## 故障排除

### mysqlclient 安装失败
在 macOS 上可能需要先安装系统依赖：
```bash
brew install mysql
# 或
brew install mariadb-connector-c
```

### 包找不到
确保在正确的虚拟环境中，并且包已正确安装：
```bash
pip list | grep opendan
```


