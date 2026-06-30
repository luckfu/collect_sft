#!/usr/bin/env python3
"""
Simple CLI Editor for Endpoint Configuration
Basic command-line interface without rich library dependencies
"""

import json
import os
import sys
from typing import Dict, List, Any

class SimpleCLIEditor:
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
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def display_banner(self):
        """Display simple banner"""
        print("=" * 80)
        print("🚀 Endpoint Configuration Editor")
        print("Simple CLI for managing endpoint configs")
        print("=" * 80)
    
    def display_endpoints(self):
        """Display all endpoints in a simple format"""
        endpoints = self.config.get("endpoints", {})
        
        if not endpoints:
            print("\n📭 No endpoints configured")
            return
        
        print(f"\n📊 Found {len(endpoints)} endpoints:")
        print("-" * 80)
        
        for idx, (name, config) in enumerate(endpoints.items(), 1):
            print(f"{idx}. {name}")
            print(f"   URL: {config.get('base_url', 'N/A')}")
            print(f"   Models: {len(config.get('models', []))} models")
            
            features = []
            if config.get("chat_completion_path"):
                features.append("Chat")
            if config.get("embeddings_path"):
                features.append("Embeddings")
            if config.get("rerank_path"):
                features.append("Rerank")
            if config.get("anthropic_path"):
                features.append("Anthropic")
            
            print(f"   Features: {', '.join(features) if features else 'Basic'}")
            print(f"   Auth: {config.get('auth_type', 'unknown')}")
            print()
    
    def edit_models_simple(self, endpoint_name: str):
        """Simple model editing interface"""
        if endpoint_name not in self.config.get("endpoints", {}):
            print(f"Error: Endpoint '{endpoint_name}' not found")
            return
        
        endpoint = self.config["endpoints"][endpoint_name]
        models = endpoint.setdefault("models", [])
        
        while True:
            print(f"\n🎯 Editing models for: {endpoint_name}")
            print("=" * 50)
            
            if models:
                print("Current models:")
                for idx, model in enumerate(models, 1):
                    print(f"  {idx}. {model}")
            else:
                print("No models configured")
            
            print("\nOptions:")
            print("1. Add model")
            print("2. Remove model")
            print("3. Edit model")
            print("4. Reorder models")
            print("5. Bulk import")
            print("6. Back to main menu")
            
            choice = input("\nChoose action (1-6): ").strip()
            
            if choice == "1":
                model = input("Enter model name: ").strip()
                if model and model not in models:
                    models.append(model)
                    print(f"✅ Added: {model}")
                elif model in models:
                    print("⚠️  Model already exists")
            
            elif choice == "2" and models:
                try:
                    num = int(input("Enter model number to remove: ").strip())
                    if 1 <= num <= len(models):
                        removed = models.pop(num - 1)
                        print(f"✅ Removed: {removed}")
                    else:
                        print("❌ Invalid number")
                except ValueError:
                    print("❌ Please enter a valid number")
            
            elif choice == "3" and models:
                try:
                    num = int(input("Enter model number to edit: ").strip())
                    if 1 <= num <= len(models):
                        old_model = models[num - 1]
                        new_model = input(f"Edit '{old_model}': ").strip()
                        if new_model and new_model != old_model:
                            models[num - 1] = new_model
                            print(f"✅ Updated: {old_model} → {new_model}")
                    else:
                        print("❌ Invalid number")
                except ValueError:
                    print("❌ Please enter a valid number")
            
            elif choice == "4" and len(models) > 1:
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
            
            elif choice == "5":
                models_str = input("Enter comma-separated models: ").strip()
                new_models = [m.strip() for m in models_str.split(",") if m.strip()]
                added = 0
                for model in new_models:
                    if model not in models:
                        models.append(model)
                        added += 1
                print(f"✅ Added {added} new models")
            
            elif choice == "6":
                self.save_config()
                break
            
            else:
                print("❌ Invalid choice or no models to operate on")
            
            input("\nPress Enter to continue...")
    
    def add_endpoint_simple(self):
        """Add new endpoint with simple interface"""
        print("\n➕ Adding New Endpoint")
        print("=" * 30)
        
        name = input("Endpoint name: ").strip()
        if not name:
            print("❌ Name is required")
            return
        
        if name in self.config.get("endpoints", {}):
            print(f"❌ Endpoint '{name}' already exists")
            return
        
        base_url = input("Base URL: ").strip()
        if not base_url:
            base_url = "https://api.example.com"
        
        auth_type = input("Auth type (bearer/api_key/none) [bearer]: ").strip()
        if not auth_type:
            auth_type = "bearer"
        if auth_type not in ["bearer", "api_key", "none"]:
            auth_type = "bearer"
        
        models = []
        print("\nModels (empty line to finish):")
        while True:
            model = input("Model: ").strip()
            if not model:
                break
            models.append(model)
        
        config = {
            "base_url": base_url,
            "auth_type": auth_type,
            "models": models
        }
        
        # Optional features
        if input("Add chat completion path? (y/N): ").lower().startswith('y'):
            config["chat_completion_path"] = input("Chat completion path [/v1/chat/completions]: ").strip() or "/v1/chat/completions"
        
        if input("Add embeddings path? (y/N): ").lower().startswith('y'):
            config["embeddings_path"] = input("Embeddings path [/v1/embeddings]: ").strip() or "/v1/embeddings"
            embeddings_models = input("Embeddings models (comma-separated): ").strip()
            if embeddings_models:
                config["embeddings_models"] = [m.strip() for m in embeddings_models.split(",")]
        
        if input("Add rerank path? (y/N): ").lower().startswith('y'):
            config["rerank_path"] = input("Rerank path [/v1/rerank]: ").strip() or "/v1/rerank"
            rerank_models = input("Rerank models (comma-separated): ").strip()
            if rerank_models:
                config["rerank_models"] = [m.strip() for m in rerank_models.split(",")]
        
        if "endpoints" not in self.config:
            self.config["endpoints"] = {}
        
        self.config["endpoints"][name] = config
        
        if self.save_config():
            print(f"✅ Endpoint '{name}' added successfully!")
            if input("Edit models now? (y/N): ").lower().startswith('y'):
                self.edit_models_simple(name)
        else:
            print("❌ Failed to save endpoint")
    
    def edit_endpoint_simple(self):
        """Edit endpoint with simple interface"""
        endpoints = self.config.get("endpoints", {})
        if not endpoints:
            print("📭 No endpoints to edit")
            return
        
        print("\nAvailable endpoints:")
        endpoint_names = list(endpoints.keys())
        for idx, name in enumerate(endpoint_names, 1):
            print(f"  {idx}. {name}")
        
        try:
            choice = int(input("\nSelect endpoint number: ").strip())
            if 1 <= choice <= len(endpoint_names):
                name = endpoint_names[choice - 1]
                self.edit_single_endpoint_simple(name)
            else:
                print("❌ Invalid choice")
        except ValueError:
            print("❌ Please enter a number")
    
    def edit_single_endpoint_simple(self, name: str):
        """Edit single endpoint"""
        endpoint = self.config["endpoints"][name]
        
        while True:
            print(f"\n✏️  Editing: {name}")
            print("=" * 40)
            print(f"1. Name: {name}")
            print(f"2. Base URL: {endpoint.get('base_url', '')}")
            print(f"3. Auth Type: {endpoint.get('auth_type', 'bearer')}")
            print(f"4. Models: {len(endpoint.get('models', []))} models")
            print(f"5. Feature paths")
            print(f"6. Edit models")
            print(f"7. Delete endpoint")
            print(f"8. Back to main menu")
            
            choice = input("\nChoose action (1-8): ").strip()
            
            if choice == "1":
                new_name = input("New name: ").strip()
                if new_name and new_name != name and new_name not in self.config.get("endpoints", {}):
                    self.config["endpoints"][new_name] = self.config["endpoints"].pop(name)
                    name = new_name
                    self.save_config()
                    print("✅ Name updated")
            
            elif choice == "2":
                base_url = input("Base URL: ").strip()
                if base_url:
                    endpoint["base_url"] = base_url
                    self.save_config()
                    print("✅ Base URL updated")
            
            elif choice == "3":
                auth_type = input("Auth type (bearer/api_key/none): ").strip()
                if auth_type in ["bearer", "api_key", "none"]:
                    endpoint["auth_type"] = auth_type
                    self.save_config()
                    print("✅ Auth type updated")
            
            elif choice == "4":
                models = endpoint.get("models", [])
                print(f"Current models: {', '.join(models)}")
            
            elif choice == "5":
                print("\nFeature paths:")
                paths = ["chat_completion_path", "embeddings_path", "rerank_path", "anthropic_path"]
                defaults = ["/v1/chat/completions", "/v1/embeddings", "/v1/rerank", "/v1/messages"]
                
                for path, default in zip(paths, defaults):
                    current = endpoint.get(path, "")
                    new_value = input(f"{path} [{current or default}]: ").strip()
                    if new_value:
                        endpoint[path] = new_value
                    elif current and not new_value:
                        endpoint.pop(path, None)
                
                self.save_config()
                print("✅ Feature paths updated")
            
            elif choice == "6":
                self.edit_models_simple(name)
            
            elif choice == "7":
                if input(f"Delete '{name}'? (y/N): ").lower().startswith('y'):
                    self.config["endpoints"].pop(name, None)
                    self.save_config()
                    print(f"✅ '{name}' deleted")
                    break
            
            elif choice == "8":
                break
            
            else:
                print("❌ Invalid choice")
            
            input("\nPress Enter to continue...")
    
    def delete_endpoint_simple(self):
        """Delete endpoint with simple interface"""
        endpoints = self.config.get("endpoints", {})
        if not endpoints:
            print("📭 No endpoints to delete")
            return
        
        print("\nAvailable endpoints:")
        endpoint_names = list(endpoints.keys())
        for idx, name in enumerate(endpoint_names, 1):
            print(f"  {idx}. {name}")
        
        try:
            choice = int(input("\nSelect endpoint to delete: ").strip())
            if 1 <= choice <= len(endpoint_names):
                name = endpoint_names[choice - 1]
                if input(f"Delete '{name}'? (y/N): ").lower().startswith('y'):
                    del self.config["endpoints"][name]
                    self.save_config()
                    print(f"✅ '{name}' deleted")
            else:
                print("❌ Invalid choice")
        except ValueError:
            print("❌ Please enter a number")
        
        input("\nPress Enter to continue...")
    
    def run(self):
        """Main application loop"""
        try:
            while True:
                print()
                self.display_banner()
                self.display_endpoints()
                
                print("\nOptions:")
                print("1. Add endpoint")
                print("2. Edit endpoint")
                print("3. Delete endpoint")
                print("4. Save config")
                print("5. Exit")
                
                choice = input("\nChoose action (1-5): ").strip()
                
                if choice == "1":
                    self.add_endpoint_simple()
                elif choice == "2":
                    self.edit_endpoint_simple()
                elif choice == "3":
                    self.delete_endpoint_simple()
                elif choice == "4":
                    if self.save_config():
                        print("💾 Configuration saved!")
                    else:
                        print("❌ Failed to save")
                    input("\nPress Enter to continue...")
                elif choice == "5":
                    print("👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid choice")
                    input("\nPress Enter to continue...")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print("Simple CLI Editor for Endpoint Configuration")
        print("Usage: python simple_cli_editor.py")
        print("Basic command-line interface for editing endpoint_config.json")
        return
    
    editor = SimpleCLIEditor()
    editor.run()

if __name__ == "__main__":
    main()