#!/usr/bin/env python3
"""
Enhanced Endpoint Configuration Editor
An improved CUI with better model management capabilities
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.text import Text
from rich.columns import Columns
from rich import print as rprint
from rich.layout import Layout
from rich.live import Live
from rich.spinner import Spinner

console = Console()

class EnhancedEndpointEditor:
    def __init__(self, config_path: str = "endpoint_config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.current_endpoint = None
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"endpoints": {}}
        except Exception as e:
            console.print(f"[red]Error loading config: {e}[/red]")
            return {"endpoints": {}}
    
    def save_config(self) -> bool:
        """Save configuration to JSON file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            console.print(f"[red]Error saving config: {e}[/red]")
            return False
    
    def display_banner(self):
        """Display beautiful banner"""
        banner = """
[bold cyan]╔══════════════════════════════════════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║[/bold cyan]                [bold white]🚀 Enhanced Endpoint Configuration Editor[/bold white]               [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]        [dim]Next-gen CUI with advanced model management[/dim]              [bold cyan]║[/bold cyan]
[bold cyan]╚══════════════════════════════════════════════════════════════════════════════╝[/bold cyan]
        """
        console.print(banner)
    
    def display_endpoints(self):
        """Display all endpoints in a beautiful table"""
        endpoints = self.config.get("endpoints", {})
        
        if not endpoints:
            console.print("\n[yellow]📭 No endpoints configured[/yellow]")
            return
        
        table = Table(title="[bold cyan]🌐 Configured Endpoints[/bold cyan]", show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Name", style="cyan", no_wrap=True, width=15)
        table.add_column("Base URL", style="green", width=35)
        table.add_column("Models", style="yellow", width=20)
        table.add_column("Features", style="blue", width=12)
        table.add_column("Auth Type", style="magenta", width=10)
        
        for idx, (name, config) in enumerate(endpoints.items(), 1):
            base_url = config.get("base_url", "N/A")
            models = config.get("models", [])
            models_display = f"{len(models)} models" if models else "No models"
            
            features = []
            if config.get("chat_completion_path"):
                features.append("💬")
            if config.get("embeddings_path"):
                features.append("📊")
            if config.get("rerank_path"):
                features.append("🔄")
            if config.get("anthropic_path"):
                features.append("🤖")
            
            features_display = " ".join(features) if features else "Basic"
            auth_type = config.get("auth_type", "unknown")
            
            table.add_row(str(idx), name, base_url, models_display, features_display, auth_type)
        
        console.print(table)
    
    def display_model_list(self, models: List[str], title: str = "Models"):
        """Display model list in a formatted way"""
        if not models:
            console.print(f"[dim]No {title.lower()} configured[/dim]")
            return
        
        table = Table(title=f"[bold cyan]{title}[/bold cyan]", show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Model Name", style="green", width=50)
        
        for idx, model in enumerate(models, 1):
            table.add_row(str(idx), model)
        
        console.print(table)
    
    def edit_models(self, endpoint_name: str):
        """Dedicated model editing interface"""
        if endpoint_name not in self.config.get("endpoints", {}):
            console.print(f"[red]Endpoint '{endpoint_name}' not found[/red]")
            return
        
        endpoint = self.config["endpoints"][endpoint_name]
        models = endpoint.get("models", [])
        
        while True:
            console.clear()
            self.display_banner()
            console.print(f"\n[bold yellow]🎯 Editing Models for: {endpoint_name}[/bold yellow]")
            
            self.display_model_list(models, "Chat Models")
            
            choices = [
                "1. Add model",
                "2. Remove model", 
                "3. Edit model",
                "4. Reorder models",
                "5. Bulk import",
                "6. Back to main menu"
            ]
            
            console.print("\n[bold cyan]Available Actions:[/bold cyan]")
            for choice in choices:
                console.print(f"  {choice}")
            
            action = Prompt.ask("\n[bold cyan]Choose action[/bold cyan]", choices=["1", "2", "3", "4", "5", "6"], default="6")
            
            if action == "1":
                self.add_model(models)
            elif action == "2":
                self.remove_model(models)
            elif action == "3":
                self.edit_single_model(models)
            elif action == "4":
                self.reorder_models(models)
            elif action == "5":
                self.bulk_import_models(models)
            elif action == "6":
                endpoint["models"] = models
                self.save_config()
                break
    
    def add_model(self, models: List[str]):
        """Add a new model"""
        console.print("\n[green]➕ Add New Model[/green]")
        model_name = Prompt.ask("[cyan]Enter model name[/cyan]").strip()
        
        if model_name and model_name not in models:
            position = IntPrompt.ask(
                "[cyan]Position (1-{})[/cyan]".format(len(models) + 1),
                default=len(models) + 1,
                show_default=True
            )
            position = max(1, min(position, len(models) + 1))
            models.insert(position - 1, model_name)
            console.print(f"[green]✅ Model '{model_name}' added at position {position}[/green]")
        elif model_name in models:
            console.print("[yellow]⚠️  Model already exists[/yellow]")
        
        input("\n[dim]Press Enter to continue...[/dim]")
    
    def remove_model(self, models: List[str]):
        """Remove a model"""
        if not models:
            console.print("[yellow]No models to remove[/yellow]")
            input("\n[dim]Press Enter to continue...[/dim]")
            return
        
        console.print("\n[red]🗑️  Remove Model[/red]")
        for idx, model in enumerate(models, 1):
            console.print(f"  {idx}. {model}")
        
        try:
            choice = IntPrompt.ask(
                "[cyan]Select model number to remove[/cyan]",
                choices=[str(i) for i in range(1, len(models) + 1)]
            )
            removed = models.pop(choice - 1)
            console.print(f"[green]✅ Model '{removed}' removed[/green]")
        except (ValueError, IndexError):
            console.print("[red]Invalid selection[/red]")
        
        input("\n[dim]Press Enter to continue...[/dim]")
    
    def edit_single_model(self, models: List[str]):
        """Edit a single model"""
        if not models:
            console.print("[yellow]No models to edit[/yellow]")
            input("\n[dim]Press Enter to continue...[/dim]")
            return
        
        console.print("\n[yellow]✏️  Edit Model[/yellow]")
        for idx, model in enumerate(models, 1):
            console.print(f"  {idx}. {model}")
        
        try:
            choice = IntPrompt.ask(
                "[cyan]Select model number to edit[/cyan]",
                choices=[str(i) for i in range(1, len(models) + 1)]
            )
            old_model = models[choice - 1]
            new_model = Prompt.ask(
                f"[cyan]Edit model[/cyan]",
                default=old_model
            ).strip()
            
            if new_model and new_model != old_model:
                models[choice - 1] = new_model
                console.print(f"[green]✅ Model updated: {old_model} → {new_model}[/green]")
        except (ValueError, IndexError):
            console.print("[red]Invalid selection[/red]")
        
        input("\n[dim]Press Enter to continue...[/dim]")
    
    def reorder_models(self, models: List[str]):
        """Reorder models"""
        if len(models) < 2:
            console.print("[yellow]Need at least 2 models to reorder[/yellow]")
            input("\n[dim]Press Enter to continue...[/dim]")
            return
        
        console.print("\n[blue]🔃 Reorder Models[/blue]")
        for idx, model in enumerate(models, 1):
            console.print(f"  {idx}. {model}")
        
        try:
            from_pos = IntPrompt.ask(
                "[cyan]Move model from position[/cyan]",
                choices=[str(i) for i in range(1, len(models) + 1)]
            )
            to_pos = IntPrompt.ask(
                "[cyan]To position[/cyan]",
                choices=[str(i) for i in range(1, len(models) + 1)]
            )
            
            model = models.pop(from_pos - 1)
            models.insert(to_pos - 1, model)
            console.print(f"[green]✅ Model moved from {from_pos} to {to_pos}[/green]")
        except (ValueError, IndexError):
            console.print("[red]Invalid selection[/red]")
        
        input("\n[dim]Press Enter to continue...[/dim]")
    
    def bulk_import_models(self, models: List[str]):
        """Bulk import models from comma-separated list"""
        console.print("\n[green]📥 Bulk Import Models[/green]")
        console.print("[dim]Enter comma-separated model names[/dim]")
        
        models_str = Prompt.ask("[cyan]Models[/cyan]")
        new_models = [m.strip() for m in models_str.split(",") if m.strip()]
        
        if new_models:
            # Remove duplicates while preserving order
            seen = set(models)
            for model in new_models:
                if model not in seen:
                    models.append(model)
                    seen.add(model)
            
            console.print(f"[green]✅ Added {len([m for m in new_models if m not in seen])} new models[/green]")
        
        input("\n[dim]Press Enter to continue...[/dim]")
    
    def add_endpoint(self):
        """Add a new endpoint with enhanced prompts"""
        console.print("\n[bold green]➕ Adding New Endpoint[/bold green]")
        console.print("[dim]Press Enter to use defaults, Ctrl+C to cancel[/dim]")
        
        try:
            name = Prompt.ask("[cyan]Endpoint name[/cyan]").strip()
            if not name:
                console.print("[red]❌ Name is required[/red]")
                return
            
            if name in self.config.get("endpoints", {}):
                console.print(f"[red]❌ Endpoint '{name}' already exists[/red]")
                return
            
            base_url = Prompt.ask("[cyan]Base URL[/cyan]", default="https://api.example.com")
            auth_type = Prompt.ask(
                "[cyan]Auth type[/cyan]", 
                choices=["bearer", "api_key", "none"], 
                default="bearer"
            )
            
            # Enhanced model input with bulk import option
            console.print("\n[bold cyan]🎯 Model Configuration[/bold cyan]")
            model_input_method = Prompt.ask(
                "[cyan]How to add models?[/cyan]",
                choices=["manual", "bulk", "skip"],
                default="manual"
            )
            
            models = []
            if model_input_method == "manual":
                while True:
                    model = Prompt.ask("[cyan]Add model (empty to finish)[/cyan]").strip()
                    if not model:
                        break
                    models.append(model)
            elif model_input_method == "bulk":
                models_str = Prompt.ask("[cyan]Models (comma-separated)[/cyan]")
                models = [m.strip() for m in models_str.split(",") if m.strip()]
            
            config = {
                "base_url": base_url,
                "auth_type": auth_type,
                "models": models
            }
            
            # Enhanced feature configuration
            console.print("\n[bold cyan]⚙️  Feature Configuration[/bold cyan]")
            
            features = [
                ("chat_completion_path", "/v1/chat/completions", "Chat Completion"),
                ("embeddings_path", "/v1/embeddings", "Embeddings"),
                ("rerank_path", "/v1/rerank", "Rerank"),
                ("anthropic_path", "/v1/messages", "Anthropic")
            ]
            
            for path_key, default_path, description in features:
                if Confirm.ask(f"[dim]Add {description}?[/dim]", default=path_key == "chat_completion_path"):
                    config[path_key] = Prompt.ask(
                        f"[cyan]{description} path[/cyan]",
                        default=default_path
                    )
                    
                    # Add specific models for embeddings/rerank
                    if path_key in ["embeddings_path", "rerank_path"]:
                        model_type = path_key.replace("_path", "_models")
                        default_model = "embedding-model" if path_key == "embeddings_path" else "rerank-model"
                        models_str = Prompt.ask(
                            f"[cyan]{description} models[/cyan]",
                            default=default_model
                        )
                        config[model_type] = [m.strip() for m in models_str.split(",") if m.strip()]
            
            if "endpoints" not in self.config:
                self.config["endpoints"] = {}
            
            self.config["endpoints"][name] = config
            
            if self.save_config():
                console.print(f"[green]✅ Endpoint '{name}' added successfully![/green]")
                if Confirm.ask("[dim]Edit models now?[/dim]", default=True):
                    self.edit_models(name)
            else:
                console.print("[red]❌ Failed to save endpoint[/red]")
                
        except KeyboardInterrupt:
            console.print("\n[yellow]⚡ Cancelled[/yellow]")
    
    def edit_endpoint(self):
        """Edit an existing endpoint with enhanced options"""
        endpoints = self.config.get("endpoints", {})
        if not endpoints:
            console.print("[yellow]📭 No endpoints to edit[/yellow]")
            return
        
        endpoint_names = list(endpoints.keys())
        name = Prompt.ask(
            "[cyan]Choose endpoint to edit[/cyan]",
            choices=endpoint_names
        )
        
        if not name:
            return
        
        while True:
            console.clear()
            self.display_banner()
            console.print(f"\n[bold yellow]✏️  Editing: {name}[/bold yellow]")
            
            endpoint = endpoints[name]
            self.display_model_list(endpoint.get("models", []), f"Models for {name}")
            
            choices = [
                "1. Basic settings",
                "2. Edit models", 
                "3. Edit feature paths",
                "4. Edit auth settings",
                "5. Clone endpoint",
                "6. Back to main menu"
            ]
            
            console.print("\n[bold cyan]Available Actions:[/bold cyan]")
            for choice in choices:
                console.print(f"  {choice}")
            
            action = Prompt.ask("\n[bold cyan]Choose action[/bold cyan]", choices=["1", "2", "3", "4", "5", "6"], default="6")
            
            if action == "1":
                self.edit_basic_settings(name)
            elif action == "2":
                self.edit_models(name)
            elif action == "3":
                self.edit_feature_paths(name)
            elif action == "4":
                self.edit_auth_settings(name)
            elif action == "5":
                self.clone_endpoint(name)
            elif action == "6":
                break
    
    def edit_basic_settings(self, name: str):
        """Edit basic endpoint settings"""
        endpoint = self.config["endpoints"][name]
        
        console.print("\n[blue]⚙️  Basic Settings[/blue]")
        
        base_url = Prompt.ask("[cyan]Base URL[/cyan]", default=endpoint.get("base_url", ""))
        auth_type = Prompt.ask(
            "[cyan]Auth type[/cyan]",
            choices=["bearer", "api_key", "none"],
            default=endpoint.get("auth_type", "bearer")
        )
        
        endpoint.update({
            "base_url": base_url,
            "auth_type": auth_type
        })
        
        if self.save_config():
            console.print("[green]✅ Basic settings updated[/green]")
        
        input("\n[dim]Press Enter to continue...[/dim]")
    
    def edit_feature_paths(self, name: str):
        """Edit feature paths"""
        endpoint = self.config["endpoints"][name]
        
        console.print("\n[green]🛠️  Feature Paths[/green]")
        
        features = [
            ("chat_completion_path", "/v1/chat/completions", "Chat Completion"),
            ("embeddings_path", "/v1/embeddings", "Embeddings"),
            ("rerank_path", "/v1/rerank", "Rerank"),
            ("anthropic_path", "/v1/messages", "Anthropic")
        ]
        
        for path_key, default_path, description in features:
            current_value = endpoint.get(path_key, "")
            enabled = Confirm.ask(
                f"[dim]Enable {description}?[/dim]",
                default=bool(current_value) or path_key == "chat_completion_path"
            )
            
            if enabled:
                new_value = Prompt.ask(
                    f"[cyan]{description} path[/cyan]",
                    default=current_value or default_path
                )
                if new_value.strip():
                    endpoint[path_key] = new_value.strip()
                    
                    # Handle specific model lists
                    if path_key == "embeddings_path":
                        models_str = Prompt.ask(
                            "[cyan]Embeddings models[/cyan]",
                            default=",".join(endpoint.get("embeddings_models", ["embedding-model"]))
                        )
                        endpoint["embeddings_models"] = [m.strip() for m in models_str.split(",") if m.strip()]
                    elif path_key == "rerank_path":
                        models_str = Prompt.ask(
                            "[cyan]Rerank models[/cyan]",
                            default=",".join(endpoint.get("rerank_models", ["rerank-model"]))
                        )
                        endpoint["rerank_models"] = [m.strip() for m in models_str.split(",") if m.strip()]
            elif path_key in endpoint:
                del endpoint[path_key]
                # Clean up associated model lists
                if path_key == "embeddings_path" and "embeddings_models" in endpoint:
                    del endpoint["embeddings_models"]
                if path_key == "rerank_path" and "rerank_models" in endpoint:
                    del endpoint["rerank_models"]
        
        if self.save_config():
            console.print("[green]✅ Feature paths updated[/green]")
        
        input("\n[dim]Press Enter to continue...[/dim]")
    
    def edit_auth_settings(self, name: str):
        """Edit authentication settings"""
        endpoint = self.config["endpoints"][name]
        
        console.print("\n[green]🔐 Auth Settings[/green]")
        
        auth_type = Prompt.ask(
            "[cyan]Auth type[/cyan]",
            choices=["bearer", "api_key", "none"],
            default=endpoint.get("auth_type", "bearer")
        )
        
        endpoint["auth_type"] = auth_type
        
        if self.save_config():
            console.print("[green]✅ Auth settings updated[/green]")
        
        input("\n[dim]Press Enter to continue...[/dim]")
    
    def clone_endpoint(self, name: str):
        """Clone an existing endpoint"""
        if name not in self.config.get("endpoints", {}):
            console.print("[red]Endpoint not found[/red]")
            return
        
        original = self.config["endpoints"][name]
        new_name = Prompt.ask("[cyan]New endpoint name[/cyan]").strip()
        
        if not new_name:
            console.print("[red]Name is required[/red]")
            return
        
        if new_name in self.config.get("endpoints", {}):
            console.print("[red]Endpoint already exists[/red]")
            return
        
        import copy
        self.config["endpoints"][new_name] = copy.deepcopy(original)
        
        if self.save_config():
            console.print(f"[green]✅ Endpoint cloned: {name} → {new_name}[/green]")
        
        input("\n[dim]Press Enter to continue...[/dim]")
    
    def delete_endpoint(self):
        """Delete an endpoint"""
        endpoints = self.config.get("endpoints", {})
        if not endpoints:
            console.print("[yellow]📭 No endpoints to delete[/yellow]")
            return
        
        endpoint_names = list(endpoints.keys())
        name = Prompt.ask(
            "[cyan]Choose endpoint to delete[/cyan]",
            choices=endpoint_names
        )
        
        if name and Confirm.ask(f"[red]⚠️  Are you sure you want to delete '{name}'?[/red]"):
            del self.config["endpoints"][name]
            if self.save_config():
                console.print(f"[green]✅ Endpoint '{name}' deleted successfully![/green]")
            else:
                console.print("[red]❌ Failed to delete endpoint[/red]")
        
        input("\n[dim]Press Enter to continue...[/dim]")
    
    def validate_config(self):
        """Validate the configuration"""
        issues = []
        endpoints = self.config.get("endpoints", {})
        
        for name, config in endpoints.items():
            if not config.get("base_url"):
                issues.append(f"{name}: Missing base_url")
            if not config.get("models"):
                issues.append(f"{name}: No models configured")
            if config.get("auth_type") not in ["bearer", "api_key", "none"]:
                issues.append(f"{name}: Invalid auth_type")
        
        if issues:
            console.print("\n[red]⚠️  Configuration Issues:[/red]")
            for issue in issues:
                console.print(f"  • {issue}")
        else:
            console.print("\n[green]✅ Configuration is valid[/green]")
        
        input("\n[dim]Press Enter to continue...[/dim]")
    
    def run(self):
        """Main application loop"""
        try:
            while True:
                console.clear()
                self.display_banner()
                self.display_endpoints()
                
                console.print("\n" + "─" * 80)
                choices = [
                    "1. [green]📥 Add endpoint[/green]",
                    "2. [yellow]✏️  Edit endpoint[/yellow]",
                    "3. [red]🗑️  Delete endpoint[/red]",
                    "4. [blue]🔍 Validate config[/blue]",
                    "5. [cyan]💾 Save config[/cyan]",
                    "6. [magenta]❌ Exit[/magenta]"
                ]
                
                console.print("\n[bold cyan]Available Actions:[/bold cyan]")
                for choice in choices:
                    console.print(f"  {choice}")
                
                action = Prompt.ask(
                    "\n[bold cyan]Choose action[/bold cyan]",
                    choices=["1", "2", "3", "4", "5", "6"],
                    default="6"
                )
                
                if action == "1":
                    self.add_endpoint()
                elif action == "2":
                    self.edit_endpoint()
                elif action == "3":
                    self.delete_endpoint()
                elif action == "4":
                    self.validate_config()
                elif action == "5":
                    if self.save_config():
                        console.print("[green]💾 Configuration saved successfully![/green]")
                    else:
                        console.print("[red]❌ Failed to save configuration[/red]")
                    input("\n[dim]Press Enter to continue...[/dim]")
                elif action == "6":
                    console.print("\n[bold green]👋 Thank you for using Enhanced Endpoint Configuration Editor![/bold green]")
                    break
                    
        except KeyboardInterrupt:
            console.print("\n\n[bold green]👋 Thank you for using Enhanced Endpoint Configuration Editor![/bold green]")

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        console.print("[bold cyan]Enhanced Endpoint Configuration Editor[/bold cyan]")
        console.print("Usage: python enhanced_editor.py")
        console.print("An advanced CUI for editing endpoint_config.json with model management")
        return
    
    editor = EnhancedEndpointEditor()
    editor.run()

if __name__ == "__main__":
    main()