#!/usr/bin/env python3
"""
Model Editor - Simple tool for editing models in endpoint configuration
Focuses specifically on model selection and management
"""

import json
import os
import sys
from typing import Dict, List, Any

class ModelEditor:
    def __init__(self, config_path: str = "endpoint_config.json"):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"endpoints": {}}
        except Exception as e:
            print(f"Error loading config: {e}")
            return {"endpoints": {}}
    
    def save_config(self) -> bool:
        """Save configuration to JSON file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            print("✅ Configuration saved successfully!")
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def list_endpoints(self):
        """List all available endpoints"""
        endpoints = self.config.get("endpoints", {})
        if not endpoints:
            print("📭 No endpoints found")
            return []
        
        print("\n📊 Available endpoints:")
        endpoint_names = list(endpoints.keys())
        for idx, name in enumerate(endpoint_names, 1):
            models = endpoints[name].get("models", [])
            print(f"  {idx}. {name} ({len(models)} models)")
            if models:
                for i, model in enumerate(models[:3], 1):
                    print(f"      {i}. {model}")
                if len(models) > 3:
                    print(f"      ... and {len(models) - 3} more")
        
        return endpoint_names
    
    def edit_models(self, endpoint_name: str):
        """Edit models for a specific endpoint"""
        if endpoint_name not in self.config.get("endpoints", {}):
            print(f"❌ Endpoint '{endpoint_name}' not found")
            return
        
        endpoint = self.config["endpoints"][endpoint_name]
        models = endpoint.setdefault("models", [])
        
        while True:
            print(f"\n🎯 Editing models for: {endpoint_name}")
            print("=" * 50)
            
            if models:
                print("Current models:")
                for idx, model in enumerate(models, 1):
                    print(f"  {idx:2d}. {model}")
            else:
                print("No models configured")
            
            print("\nOptions:")
            print("  1. Add single model")
            print("  2. Add multiple models")
            print("  3. Remove model")
            print("  4. Replace model")
            print("  5. Reorder models")
            print("  6. Clear all models")
            print("  7. Import from preset")
            print("  8. Save & Exit")
            
            choice = input("\nChoose action (1-8): ").strip()
            
            if choice == "1":
                model = input("Enter model name: ").strip()
                if model and model not in models:
                    models.append(model)
                    print(f"✅ Added: {model}")
                elif model in models:
                    print("⚠️  Model already exists")
            
            elif choice == "2":
                models_str = input("Enter comma-separated models: ").strip()
                new_models = [m.strip() for m in models_str.split(",") if m.strip()]
                added = 0
                for model in new_models:
                    if model and model not in models:
                        models.append(model)
                        added += 1
                print(f"✅ Added {added} new models")
            
            elif choice == "3" and models:
                try:
                    num = int(input("Enter model number to remove: ").strip())
                    if 1 <= num <= len(models):
                        removed = models.pop(num - 1)
                        print(f"✅ Removed: {removed}")
                    else:
                        print("❌ Invalid number")
                except ValueError:
                    print("❌ Please enter a valid number")
            
            elif choice == "4" and models:
                try:
                    num = int(input("Enter model number to replace: ").strip())
                    if 1 <= num <= len(models):
                        old_model = models[num - 1]
                        new_model = input(f"Replace '{old_model}' with: ").strip()
                        if new_model and new_model != old_model:
                            models[num - 1] = new_model
                            print(f"✅ Replaced: {old_model} → {new_model}")
                    else:
                        print("❌ Invalid number")
                except ValueError:
                    print("❌ Please enter a valid number")
            
            elif choice == "5" and len(models) > 1:
                try:
                    from_pos = int(input("Move from position: ").strip())
                    to_pos = int(input("To position: ").strip())
                    if 1 <= from_pos <= len(models) and 1 <= to_pos <= len(models):
                        model = models.pop(from_pos - 1)
                        models.insert(to_pos - 1, model)
                        print(f"✅ Moved from {from_pos} to {to_pos}")
                    else:
                        print("❌ Invalid positions")
                except ValueError:
                    print("❌ Please enter valid numbers")
            
            elif choice == "6":
                if input("Clear all models? (y/N): ").lower().startswith('y'):
                    models.clear()
                    print("✅ All models cleared")
            
            elif choice == "7":
                self.import_preset_models(models)
            
            elif choice == "8":
                self.save_config()
                break
            
            else:
                if choice in ["2", "3", "4", "5"] and not models:
                    print("❌ No models to operate on")
                else:
                    print("❌ Invalid choice")
            
            input("\nPress Enter to continue...")
    
    def import_preset_models(self, models: List[str]):
        """Import models from preset lists"""
        presets = {
            "1": {
                "name": "Popular OpenAI Models",
                "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
            },
            "2": {
                "name": "DeepSeek Models",
                "models": ["deepseek-chat", "deepseek-reasoner"]
            },
            "3": {
                "name": "SiliconFlow Models",
                "models": [
                    "Pro/deepseek-ai/DeepSeek-R1",
                    "Pro/deepseek-ai/DeepSeek-V3",
                    "Qwen/Qwen2.5-7B-Instruct",
                    "Qwen/QVQ-72B-Preview"
                ]
            },
            "4": {
                "name": "Anthropic Models",
                "models": [
                    "claude-sonnet-4-20250514",
                    "claude-opus-4-20250514",
                    "claude-3-5-haiku-20241022"
                ]
            },
            "5": {
                "name": "Alibaba Models",
                "models": ["qwq-32b", "qwen-max", "qwen-turbo", "qwen-plus"]
            }
        }
        
        print("\n📦 Available presets:")
        for key, preset in presets.items():
            print(f"  {key}. {preset['name']}")
            print(f"     Models: {', '.join(preset['models'][:3])}...")
        
        choice = input("\nChoose preset (1-5, or 0 to cancel): ").strip()
        
        if choice in presets:
            preset_models = presets[choice]["models"]
            print(f"\nImporting from: {presets[choice]['name']}")
            
            method = input("Import method (append/replace): ").strip().lower()
            
            if method == "replace":
                models.clear()
                models.extend(preset_models)
                print(f"✅ Replaced with {len(preset_models)} models")
            else:
                added = 0
                for model in preset_models:
                    if model not in models:
                        models.append(model)
                        added += 1
                print(f"✅ Added {added} new models")
        
        elif choice != "0":
            print("❌ Invalid choice")
    
    def quick_edit_models(self, endpoint_name: str, new_models: List[str]):
        """Quick edit models via command line arguments"""
        if endpoint_name not in self.config.get("endpoints", {}):
            print(f"❌ Endpoint '{endpoint_name}' not found")
            return False
        
        endpoint = self.config["endpoints"][endpoint_name]
        endpoint["models"] = new_models
        
        return self.save_config()
    
    def run_interactive(self):
        """Run interactive mode"""
        try:
            while True:
                print("\n" + "=" * 60)
                print("🎯 Model Editor")
                print("=" * 60)
                
                endpoint_names = self.list_endpoints()
                if not endpoint_names:
                    return
                
                print("\nOptions:")
                print("  1. Edit models for endpoint")
                print("  2. Add new endpoint")
                print("  3. Exit")
                
                choice = input("\nChoose action (1-3): ").strip()
                
                if choice == "1":
                    try:
                        num = int(input("Enter endpoint number: ").strip())
                        if 1 <= num <= len(endpoint_names):
                            name = endpoint_names[num - 1]
                            self.edit_models(name)
                        else:
                            print("❌ Invalid number")
                    except ValueError:
                        print("❌ Please enter a valid number")
                
                elif choice == "2":
                    from simple_cli_editor import SimpleCLIEditor
                    editor = SimpleCLIEditor()
                    editor.add_endpoint_simple()
                
                elif choice == "3":
                    break
                
                else:
                    print("❌ Invalid choice")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")

def main():
    """Main entry point"""
    if len(sys.argv) == 1:
        # Interactive mode
        editor = ModelEditor()
        editor.run_interactive()
    
    elif len(sys.argv) == 3 and sys.argv[1] == "list":
        # List models for endpoint
        endpoint_name = sys.argv[2]
        editor = ModelEditor()
        if endpoint_name in editor.config.get("endpoints", {}):
            models = editor.config["endpoints"][endpoint_name].get("models", [])
            print(f"Models for {endpoint_name}:")
            for model in models:
                print(f"  {model}")
        else:
            print(f"❌ Endpoint '{endpoint_name}' not found")
    
    elif len(sys.argv) >= 4 and sys.argv[1] == "edit":
        # Quick edit mode: edit endpoint_name model1 model2 ...
        endpoint_name = sys.argv[2]
        new_models = sys.argv[3:]
        editor = ModelEditor()
        if editor.quick_edit_models(endpoint_name, new_models):
            print(f"✅ Updated models for {endpoint_name}")
        else:
            print(f"❌ Failed to update models for {endpoint_name}")
    
    else:
        print("Usage:")
        print("  python model_editor.py                    # Interactive mode")
        print("  python model_editor.py list <endpoint>   # List models")
        print("  python model_editor.py edit <endpoint> model1 model2 ...  # Quick edit")

if __name__ == "__main__":
    main()