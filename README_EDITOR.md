# 🚀 Endpoint Configuration Editor

一个美观的字符界面(CUI)终端编辑器，用于管理 `endpoint_config.json` 配置文件。

## 🎯 特性

- **美观界面**: 使用 Rich 和 Textual 库打造现代化终端界面
- **双模式**: 支持 CLI 交互模式和 TUI 图形模式
- **易用性**: 直观的键盘导航和菜单操作
- **功能完整**: 添加、编辑、删除、保存配置
- **实时预览**: 查看端点详细信息和模型列表
- **中文支持**: 完全支持中文显示和输入

## 📦 安装

### 快速安装
```bash
python3 setup_editor.py
```

### 手动安装
```bash
pip3 install rich textual click
chmod +x endpoint_editor.py simple_editor.py
```

## 🎮 使用方法

### 1. 简单版本 (推荐)
```bash
# 启动简单美观的CLI界面
python3 simple_editor.py
```

### 2. 高级版本 (TUI界面)
```bash
# 启动高级TUI界面
python3 endpoint_editor.py

# 或者启动CLI模式
python3 endpoint_editor.py --cli
```

## 🖥️ 界面展示

### 简单CLI界面
```
╔══════════════════════════════════════════════════════════════════════════════╗
║                     🚀 Endpoint Configuration Editor                    ║
║              Beautiful CUI for managing endpoint configs               ║
╚══════════════════════════════════════════════════════════════════════════════╝

┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name               ┃ Base URL                                                   ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ siliconflow        │ https://api.siliconflow.cn                                 │
│ 910b               │ http://36.141.21.137:9081                                  │
│ deepseek           │ https://api.deepseek.com                                   │
└────────────────────┴────────────────────────────────────────────────────────────┘

Choose action [add/edit/delete/save/exit] (exit): 
```

### TUI界面
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Endpoint Configuration Editor                          Ctrl+Q: Quit          │
├─────────────────────────────────────────────────────────────────────────────┤
│                            🌐 Configured Endpoints                          │
│ ┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┓ │
│ ┃ Name        ┃ Base URL            ┃ Models Count ┃ Features┃ Auth    ┃ │
│ ┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━┩ │
│ │ siliconflow │ https://api.silicon…│ 5            │ 💬📊🔄  │ bearer  │ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## ⌨️ 快捷键

### 简单CLI版本
- **add**: 添加新端点
- **edit**: 编辑现有端点
- **delete**: 删除端点
- **save**: 保存配置
- **exit**: 退出程序

### TUI版本
- **a**: 添加端点
- **e**: 编辑选中端点
- **d**: 删除选中端点
- **Ctrl+S**: 保存配置
- **q**: 退出程序
- **方向键**: 导航
- **Esc**: 取消操作

## 🏗️ 支持的配置项

每个端点支持以下配置：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `base_url` | 基础URL | `https://api.siliconflow.cn` |
| `chat_completion_path` | 对话完成路径 | `/v1/chat/completions` |
| `embeddings_path` | 嵌入路径 | `/v1/embeddings` |
| `rerank_path` | 重排路径 | `/v1/rerank` |
| `anthropic_path` | Anthropic路径 | `/v1/messages` |
| `models` | 模型列表 | `["gpt-4", "claude-3"]` |
| `embeddings_models` | 嵌入模型列表 | `["bge-m3"]` |
| `rerank_models` | 重排模型列表 | `["reranker-v2"]` |
| `auth_type` | 认证类型 | `bearer`, `api_key`, `none` |

## 📁 文件结构

```
├── endpoint_editor.py     # 高级TUI版本
├── simple_editor.py       # 简单CLI版本
├── setup_editor.py        # 安装脚本
├── endpoint_config.json   # 配置文件
└── README_EDITOR.md       # 使用说明
```

## 🔧 示例操作

### 添加端点
1. 运行 `python3 simple_editor.py`
2. 选择 "add"
3. 输入端点名称 (如: "openai")
4. 输入基础URL (如: "https://api.openai.com")
5. 输入模型列表 (如: "gpt-4,gpt-3.5-turbo")
6. 选择认证类型
7. 按需添加可选路径

### 编辑端点
1. 运行 `python3 simple_editor.py`
2. 选择 "edit"
3. 选择要编辑的端点
4. 修改相应字段
5. 保存更改

## 🐛 故障排除

### 依赖问题
```bash
# 如果遇到依赖错误
pip3 install --upgrade rich textual click
```

### 权限问题
```bash
# 给脚本执行权限
chmod +x *.py
```

### 编码问题
```bash
# 确保使用UTF-8编码
export PYTHONIOENCODING=utf-8
```

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个工具！

## 📄 许可证

MIT License - 自由使用和修改