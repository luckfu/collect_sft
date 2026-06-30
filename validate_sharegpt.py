import json
import os
import shutil

def validate_sharegpt_jsonl(file_path="conversations.jsonl"):
    if not os.path.exists(file_path):
        print("❌ 文件不存在")
        return
    
    valid_lines = []
    invalid_lines = []
    valid_count = 0
    invalid_count = 0
    errors = []
    
    # 创建备份
    backup_path = file_path + ".bak"
    if not os.path.exists(backup_path):
        shutil.copy(file_path, backup_path)
        print(f"✅ 创建备份: {backup_path}")
    else:
        print(f"⚠️ 备份已存在: {backup_path}，跳过创建")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                # 检查 ShareGPT 基本结构
                if not isinstance(data, dict):
                    raise ValueError("不是字典对象")
                if "conversations" not in data:
                    raise ValueError("缺少 'conversations' 字段")
                if not isinstance(data["conversations"], list):
                    raise ValueError("'conversations' 不是列表")
                for conv in data["conversations"]:
                    if not all(key in conv for key in ["from", "value"]):
                        raise ValueError("对话回合缺少 'from' 或 'value'")
                if "system" not in data or not isinstance(data["system"], str):
                    raise ValueError("缺少 'system' 字段或不是字符串")
                
                if "tools" not in data or not isinstance(data["tools"], str):
                    raise ValueError("缺少 'tools' 字段或不是字符串")
                
                # 验证 tools 字符串是否能解析为 JSON
                try:
                    json.loads(data["tools"])
                except json.JSONDecodeError:
                    raise ValueError("'tools' 字符串不是有效的 JSON")
                
                valid_count += 1
                valid_lines.append(line)
            except (json.JSONDecodeError, ValueError) as e:
                invalid_count += 1
                invalid_lines.append(line)
                errors.append(f"行 {line_num}: {str(e)}")
    
    # 写入无效行到新文件
    invalid_path = "invalid_conversations.jsonl"
    with open(invalid_path, 'w', encoding='utf-8') as f:
        f.writelines(invalid_lines)
    print(f"✅ 无效行已保存到: {invalid_path} (共 {invalid_count} 行)")
    
    # 重写源文件只包含有效行
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(valid_lines)
    print(f"✅ 源文件已更新: {file_path} (仅保留 {valid_count} 有效行)")
    
    print(f"✅ 有效行数: {valid_count}")
    print(f"❌ 无效行数: {invalid_count}")
    if errors:
        print("\n错误详情:")
        for error in errors[:10]:  # 显示前10个错误
            print(error)
    
if __name__ == "__main__":
    validate_sharegpt_jsonl()