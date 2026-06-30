import sqlite3
import json
import os

def export_conversations_to_jsonl(db_path="interactions.db", output_file="conversations.jsonl"):
    """
    从 confirmed_interactions 表中提取 conversation 字段的 JSON 内容，导出为 JSONL 文件
    """
    def convert_tools_to_string(obj):
        """递归转换 'tools' 字段：如果它是列表，转换为 JSON 字符串"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == 'tools' and isinstance(value, list):
                    obj[key] = json.dumps(value, ensure_ascii=False)
                else:
                    convert_tools_to_string(value)
        elif isinstance(obj, list):
            for item in obj:
                convert_tools_to_string(item)
        return obj
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 只查询 conversation 字段
        query = "SELECT conversation FROM confirmed_interactions ORDER BY confirmed_timestamp"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if not rows:
            print("❌ 数据库中没有找到任何数据")
            return
        
        # 导出到 JSONL 文件
        exported_count = 0
        with open(output_file, 'w', encoding='utf-8') as f:
            for (conversation_str,) in rows:
                try:
                    # 解析 conversation JSON 字符串
                    conversation_json = json.loads(conversation_str)
                    
                    # 转换 tools 字段
                    conversation_json = convert_tools_to_string(conversation_json)
                    
                    # 直接写入 conversation 的 JSON 内容
                    f.write(json.dumps(conversation_json, ensure_ascii=False) + '\n')
                    exported_count += 1
                    
                except json.JSONDecodeError as e:
                    print(f"⚠️ 跳过无效的 JSON 数据: {e}")
                    continue
        
        print(f"✅ 成功导出 {exported_count} 条对话记录到 {output_file}")
        print(f"📁 文件大小: {os.path.getsize(output_file) / 1024:.2f} KB")
        
    except sqlite3.Error as e:
        print(f"❌ 数据库错误: {e}")
    except Exception as e:
        print(f"❌ 导出过程中发生错误: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 开始导出对话数据...")
    
    # 检查数据库文件是否存在
    if not os.path.exists("interactions.db"):
        print("❌ 找不到 interactions.db 文件")
        exit(1)
    
    # 导出对话内容
    export_conversations_to_jsonl()
    
    print("🎉 导出完成！")